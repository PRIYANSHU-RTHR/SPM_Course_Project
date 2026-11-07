"""Reallocation workflow: a disruption -> engine-computed proposal -> PM approval -> apply.

    apply_event -> recompute -> propose -> pm_approval -> apply -> recompute_final
                                                |
                                                +-- reject -> END

`apply_event` writes the disruption as a fact (leave row, slipped hours, new task). The
reassignment is only a proposal: optimal assignment re-run for the affected tasks alone
(owner unavailable during the leave, critical and finishing later than before the event,
new scope), with everyone's other work as starting load. "If approved" numbers come from
the same engines run on a copy with the proposed owners (services.scenario), never from
the LLM. `pm_approval` is the only interrupt; its resume value is approve or reject.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.engines.assignment import Load, is_eligible, recommend_optimal, score
from app.engines.calendar import HOURS_PER_DAY, add_working_days, next_working_day
from app.models import (
    AssignmentSource,
    AuditLog,
    Reallocation,
    ReallocationStatus,
    Risk,
    RiskStatus,
)
from app.schemas.assignment import ApplyItem, ApplyRequest
from app.schemas.reallocation import (
    Disruption,
    LeaveDisruption,
    OwnerRef,
    ProposalItem,
    ProposalPayload,
    RiskRef,
    ScenarioMetrics,
    SlipDisruption,
)
from app.schemas.workflow import (
    ApproveDecision,
    EditDecision,
    PlanDecision,
    RejectDecision,
)
from app.services.assignment import apply as apply_assignments
from app.services.disruptions import apply_disruption
from app.services.inputs import get_project
from app.services.risk_service import refresh_risks
from app.services.scenario import Outcome, load_scenario
from app.workflows.events import NodeResult, Publish, timed

NODES = ("apply_event", "recompute", "propose", "pm_approval", "apply", "recompute_final")
ACTOR_SYSTEM = "system:reallocation"

DISRUPTION: TypeAdapter[Any] = TypeAdapter(Disruption)
DECISION: TypeAdapter[ApproveDecision | EditDecision | RejectDecision] = TypeAdapter(PlanDecision)


class ReallocState(TypedDict, total=False):
    thread_id: str
    project_id: int
    disruption: dict[str, Any]  # the posted Disruption as JSON
    as_of: str  # project clock when the run started
    seed: int
    runs: int
    before_disruption: dict[str, Any]  # ScenarioMetrics before the fact was written
    pre_finish: dict[str, str]  # task id -> planned finish before the event
    leave_tasks: list[int]  # the absent member's open tasks overlapping the leave
    new_task_id: int | None
    now: dict[str, Any]  # ScenarioMetrics with the disruption, current owners
    affected: dict[str, list[str]]  # task id -> AffectReason values
    reallocation_id: int
    proposal: dict[str, Any]  # ProposalPayload
    decision: dict[str, Any]
    applied: list[int]  # assignment ids written on approval
    outcome: dict[str, Any]  # ScenarioMetrics after approval
    status: Literal["proposing", "committed", "rejected"]
    reason: str


@dataclass(frozen=True)
class ReallocDeps:
    session_factory: sessionmaker[Session]
    publish: Publish


def _pct(p: float | None) -> str:
    return "n/a" if p is None else f"{p:.0%}"


def _window(today: date, earliest: date, hours: float) -> tuple[date, date]:
    """Working days a task would take if its owner were free, from its earliest start."""
    start = next_working_day(max(today, earliest))
    return start, add_working_days(start, max(math.ceil(hours / HOURS_PER_DAY - 1e-9) - 1, 0))


def _risk_refs(
    keys: list[tuple[str, str]],
    findings: dict[tuple[str, str], Any],
    register: dict[tuple[str, str], int],
) -> list[RiskRef]:
    return [
        RiskRef(
            risk_id=register.get(k),
            rule_key=k[0],
            subject_ref=k[1],
            title=findings[k].title,
            score=findings[k].score,
        )
        for k in keys
    ]


def build_reallocate_graph(deps: ReallocDeps) -> StateGraph:
    def scenario_outcome(s: Session, state: ReallocState) -> Outcome:
        project = get_project(s, state["project_id"])
        as_of = date.fromisoformat(state["as_of"])
        return load_scenario(s, project, as_of, state["seed"], state["runs"]).evaluate()

    def apply_event(state: ReallocState) -> NodeResult:
        d = DISRUPTION.validate_python(state["disruption"])
        with deps.session_factory() as s:
            before = scenario_outcome(s, state)
            leave_tasks: list[int] = []
            if isinstance(d, LeaveDisruption):
                leave_tasks = [
                    t.task_id
                    for t in before.plan.tasks
                    if before.scenario.owners.get(t.task_id) == d.member_id
                    and before.scenario.is_open(t.task_id)
                    and t.start <= d.end_date
                    and t.end >= d.start_date
                ]
            info = apply_disruption(s, get_project(s, state["project_id"]), d)
        update = {
            "before_disruption": before.metrics().model_dump(mode="json"),
            "pre_finish": {str(t.task_id): t.end.isoformat() for t in before.plan.tasks},
            "leave_tasks": leave_tasks,
            "new_task_id": info["new_task_id"],
            "status": "proposing",
        }
        if isinstance(d, LeaveDisruption):
            summary = f"leave written; {len(leave_tasks)} open tasks of the member overlap it"
        elif isinstance(d, SlipDisruption):
            summary = f"task {d.task_id} grew by {d.extra_hours:g} h"
        else:
            summary = f"task {info['new_task_id']} added"
        return update, summary

    def recompute(state: ReallocState) -> NodeResult:
        as_of = date.fromisoformat(state["as_of"])
        with deps.session_factory() as s:
            risks = refresh_risks(s, state["project_id"], as_of, state["seed"], runs=state["runs"])
            now = scenario_outcome(s, state)
        scen = now.scenario
        affected: dict[int, list[str]] = {}
        for task_id in state["leave_tasks"]:
            if task_id in scen.states and scen.is_open(task_id):
                affected.setdefault(task_id, []).append("owner_unavailable")
        critical = {t.task_id for t in now.cpm.tasks if t.critical}
        for t in now.plan.tasks:
            before = state["pre_finish"].get(str(t.task_id))
            if (
                t.task_id in critical
                and scen.is_open(t.task_id)
                and before is not None
                and t.end > date.fromisoformat(before)
            ):
                affected.setdefault(t.task_id, []).append("critical_slip")
        if state.get("new_task_id") is not None:
            affected.setdefault(state["new_task_id"], []).append("new_scope")
        metrics = now.metrics()
        update = {
            "now": metrics.model_dump(mode="json"),
            "affected": {str(k): v for k, v in sorted(affected.items())},
        }
        summary = (
            f"P(on time) {_pct(metrics.p_on_time)}, finish {metrics.finish.isoformat()}, "
            f"{len(affected)} tasks affected, risks +{len(risks.opened) + len(risks.reopened)}"
            f" -{len(risks.closed)}"
        )
        return update, summary

    def propose(state: ReallocState) -> NodeResult:
        affected = {int(k): v for k, v in state["affected"].items()}
        with deps.session_factory() as s:
            now = scenario_outcome(s, state)
            open_risks = s.execute(
                select(Risk.rule_key, Risk.subject_ref, Risk.id).where(
                    Risk.project_id == state["project_id"], Risk.status != RiskStatus.CLOSED
                )
            )
            register = {(rule, subject): risk_id for rule, subject, risk_id in open_risks}
        scen = now.scenario
        by_id = {t.id: t for t in scen.tasks}
        team = {m.id: m for m in scen.members}
        today = next_working_day(scen.as_of)

        hours = {i: now.placed[i].hours for i in affected}
        windows = {i: _window(today, now.placed[i].early_start, hours[i]) for i in affected}
        load = Load((today, max(now.plan.finish, scen.deadline, today)))
        for t in now.plan.tasks:
            if (
                t.task_id not in affected
                and t.member_id is not None
                and scen.is_open(t.task_id)
                and t.hours > 0
                and t.end >= today
            ):
                load.add(t.member_id, (max(t.start, today), t.end), t.hours)

        subset = [
            replace(by_id[i], predecessors=tuple(p for p in by_id[i].predecessors if p in affected))
            for i in sorted(affected)
        ]
        plan = recommend_optimal(subset, scen.members, windows, hours=hours, base_load=load)
        recs = {r.task_id: r for r in plan.recommendations}

        changes: dict[int, int | None] = {}
        rows: list[dict[str, Any]] = []
        for i in sorted(affected):
            before = scen.owners.get(i)
            rec = recs[i]
            after = rec.member_id if rec.member_id is not None else before
            if after != before:
                changes[i] = after
            eligible, why, score_before = False, None, None
            if before is not None and before in team:
                eligible, why = is_eligible(by_id[i], team[before], windows[i])
                score_before = score(
                    by_id[i], team[before], windows[i], hours[i], load, scen.members
                ).total
            if rec.member_id is not None and rec.score is not None:
                score_after = rec.score.total
            else:
                score_after = score_before
            rows.append(
                {
                    "task_id": i,
                    "before": before,
                    "after": after,
                    "eligible": eligible,
                    "why": why,
                    "score_before": score_before,
                    "score_after": score_after,
                }
            )

        if_approved = scen.with_owners(changes).evaluate()
        now_f = {(f.rule_key, f.subject_ref): f for f in now.findings()}
        after_f = {(f.rule_key, f.subject_ref): f for f in if_approved.findings()}
        now_m, after_m = now.metrics(), if_approved.metrics()

        def owner(member_id: int | None) -> OwnerRef:
            name = scen.names.get(member_id) if member_id is not None else None
            return OwnerRef(member_id=member_id, name=name)

        items = [
            ProposalItem(
                task_id=r["task_id"],
                title=scen.states[r["task_id"]].title,
                reasons=affected[r["task_id"]],  # type: ignore[arg-type]
                before=owner(r["before"]),
                after=owner(r["after"]),
                changed=r["after"] != r["before"],
                before_eligible=r["eligible"],
                before_ineligible_reason=r["why"],
                score_before=r["score_before"],
                score_after=r["score_after"],
                finish_before=now.placed[r["task_id"]].end,
                finish_after=if_approved.placed[r["task_id"]].end,
            )
            for r in rows
        ]
        d = DISRUPTION.validate_python(state["disruption"])
        if isinstance(d, LeaveDisruption):
            who = scen.names.get(d.member_id, f"Member {d.member_id}")
            event = f"{who} is on leave {d.start_date.isoformat()} to {d.end_date.isoformat()}."
        elif isinstance(d, SlipDisruption):
            event = f"Task {d.task_id} needs {d.extra_hours:g} more hours."
        else:
            event = f"New task {state['new_task_id']} was added."
        summary = (
            f"{event} {len(items)} tasks affected, {len(changes)} reassignments proposed. "
            f"P(on time) {_pct(now_m.p_on_time)} now, {_pct(after_m.p_on_time)} if approved."
        )

        with deps.session_factory() as s:
            row = s.scalar(select(Reallocation).where(Reallocation.thread_id == state["thread_id"]))
            if row is None:
                row = Reallocation(
                    project_id=state["project_id"],
                    thread_id=state["thread_id"],
                    disruption=state["disruption"],
                    status=ReallocationStatus.PENDING,
                )
                s.add(row)
                s.flush()
            payload = ProposalPayload(
                reallocation_id=row.id,
                thread_id=state["thread_id"],
                project_id=state["project_id"],
                as_of=scen.as_of,
                disruption=state["disruption"],
                summary=summary,
                before_disruption=ScenarioMetrics.model_validate(state["before_disruption"]),
                now=now_m,
                if_approved=after_m,
                items=items,
                risks_that_would_close=_risk_refs(
                    sorted(k for k in now_f if k not in after_f), now_f, register
                ),
                risks_that_would_open=_risk_refs(
                    sorted(k for k in after_f if k not in now_f), after_f, register
                ),
            )
            row.payload = payload.model_dump(mode="json")
            s.commit()
            reallocation_id = row.id
        update = {"reallocation_id": reallocation_id, "proposal": row.payload}
        return update, f"{len(changes)} of {len(items)} affected tasks get a new owner"

    def _decide(
        s: Session, state: ReallocState, status: ReallocationStatus, actor: str, reason: str | None
    ) -> Reallocation:
        row = s.get_one(Reallocation, state["reallocation_id"])
        if row.status == ReallocationStatus.PENDING:
            row.status = status
            row.decided_by = actor
            row.reason = reason
            row.decided_at = datetime.now(UTC)
            s.add(
                AuditLog(
                    actor=actor,
                    action=f"reallocation.{status.value}",
                    entity="reallocation",
                    entity_id=row.id,
                    before={"status": "pending"},
                    after={"status": status.value},
                    reason=reason,
                )
            )
        return row

    def pm_approval(state: ReallocState) -> NodeResult:
        decision = DECISION.validate_python(interrupt(state["proposal"]))
        if isinstance(decision, EditDecision):  # the resume endpoint already refuses this
            raise ValueError("a reallocation proposal can only be approved or rejected")
        dumped = decision.model_dump(mode="json")
        if isinstance(decision, ApproveDecision):
            return Command(goto="apply", update={"decision": dumped}), "approved"
        with deps.session_factory() as s:
            _decide(s, state, ReallocationStatus.REJECTED, decision.actor, decision.reason)
            s.commit()
        update = {"decision": dumped, "status": "rejected", "reason": decision.reason}
        return Command(goto=END, update=update), "rejected; owners unchanged"

    def apply(state: ReallocState) -> NodeResult:
        decision = state["decision"]
        actor, reason = decision["actor"], decision.get("reason")
        changed = [i for i in state["proposal"]["items"] if i["changed"]]
        why = reason or f"reallocation approved ({state['disruption']['type']})"
        with deps.session_factory() as s:
            row = s.get_one(Reallocation, state["reallocation_id"])
            if row.status != ReallocationStatus.PENDING:  # re-run after a crash: done already
                return {"applied": state.get("applied", [])}, "already applied"
            _decide(s, state, ReallocationStatus.APPROVED, actor, reason)
            applied: list[int] = []
            if changed:  # apply() commits the decision too, in the same transaction
                result = apply_assignments(
                    s,
                    state["project_id"],
                    ApplyRequest(
                        actor=actor,
                        items=[
                            ApplyItem(
                                task_id=i["task_id"],
                                member_id=i["after"]["member_id"],
                                source=AssignmentSource.AI,
                                reason=why,
                                score_breakdown={
                                    "total": i["score_after"],
                                    "reallocation_id": state["reallocation_id"],
                                },
                            )
                            for i in changed
                        ],
                    ),
                )
                applied = [a.assignment_id for a in result]
            else:
                s.commit()
        return {"applied": applied}, f"{len(applied)} assignments changed"

    def recompute_final(state: ReallocState) -> NodeResult:
        as_of = date.fromisoformat(state["as_of"])
        with deps.session_factory() as s:
            risks = refresh_risks(s, state["project_id"], as_of, state["seed"], runs=state["runs"])
            metrics = scenario_outcome(s, state).metrics()
        update = {"outcome": metrics.model_dump(mode="json"), "status": "committed"}
        summary = f"P(on time) {_pct(metrics.p_on_time)}; {len(risks.closed)} risks closed"
        return update, summary

    graph = StateGraph(ReallocState)
    fns: dict[str, Callable[[ReallocState], NodeResult]] = {
        "apply_event": apply_event,
        "recompute": recompute,
        "propose": propose,
        "pm_approval": pm_approval,
        "apply": apply,
        "recompute_final": recompute_final,
    }
    for name, fn in fns.items():
        destinations = ("apply", END) if name == "pm_approval" else None
        graph.add_node(name, timed(name, fn, deps.publish), destinations=destinations)
    graph.add_edge(START, "apply_event")
    graph.add_edge("apply_event", "recompute")
    graph.add_edge("recompute", "propose")
    graph.add_edge("propose", "pm_approval")
    graph.add_edge("apply", "recompute_final")
    graph.add_edge("recompute_final", END)
    return graph
