"""Planning workflow: brief -> WBS -> estimates -> schedule -> owners -> PM review -> commit.

    decompose -> validate -> estimate -> schedule -> recommend -> pm_review -> commit
                                ^                                    |  edit
                                +------------------------------------+
                                                         reject -> END

The planning agent only drafts structure and three-point hours. Every number in the review
payload comes from an engine. `pm_review` is the only interrupt. Its resume value is a
`PlanDecision`: approve -> commit, edit -> apply changes and go back to estimate,
reject -> end. State holds plain JSON values only, so any checkpointer can serialise it.
"""

import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import pairwise
from typing import Any, Literal, TypedDict

from langgraph.errors import GraphInterrupt
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.agents.llm import LLMClient
from app.agents.planning import (
    MAX_HOURS,
    MIN_HOURS,
    PROMPT_NAME,
    PlannedTask,
    SkillReq,
    WBSPlan,
    build_prompt,
    match_skill,
    validate_plan,
)
from app.engines.assignment import is_eligible, recommend_optimal
from app.engines.calendar import hours_to_window
from app.engines.cpm import CycleError, cpm, topo_sort
from app.engines.estimation import (
    DEFAULT_LOC_PER_HOUR,
    HOURS_PER_PM,
    cocomo2,
    ksloc_from_hours,
    path_pert,
    pert,
)
from app.engines.evm import hours_cost
from app.engines.scheduler import ScheduleError, schedule
from app.engines.types import MemberInput, RequiredSkill, TaskInput
from app.models import AssignmentSource, AuditLog, Dependency, Epic, Member, Project, Skill, Task
from app.schemas.assignment import ApplyItem, ApplyRequest, ScoreOut
from app.schemas.estimate import Cocomo
from app.schemas.workflow import (
    ApproveDecision,
    CandidateBrief,
    EditDecision,
    PlanDecision,
    PlanEstimates,
    PlanRecommendation,
    PlanRecommendations,
    PlanReview,
    PlanSchedule,
    RejectDecision,
    ScheduledWbsTask,
    TaskChange,
    TaskEstimate,
)
from app.services.assignment import apply as apply_assignments
from app.services.inputs import load_members

NODES = ("decompose", "validate", "estimate", "schedule", "recommend", "pm_review", "commit")
APPROVED_ACTION = "workflow.plan_approved"
DECISION: TypeAdapter[ApproveDecision | EditDecision | RejectDecision] = TypeAdapter(PlanDecision)


class PlanState(TypedDict, total=False):
    thread_id: str
    request: dict[str, Any]  # PlanStart as JSON, start_date resolved
    vocabulary: list[str]  # skill names from the DB when the run started
    draft: dict[str, Any]  # WBSPlan exactly as the model returned it
    wbs: dict[str, Any]  # validated (and PM-edited) WBSPlan
    warnings: list[str]  # fixes made by validation
    gaps: list[str]  # tasks no team member is eligible for
    estimates: dict[str, Any]  # PlanEstimates
    schedule: dict[str, Any]  # PlanSchedule
    recommendations: dict[str, Any]  # PlanRecommendations
    revision: int
    decisions: list[dict[str, Any]]  # every PM decision, in order
    status: Literal["planning", "committed", "rejected"]
    project_id: int
    reason: str


class EditError(ValueError):
    """A PM edit that would leave the plan invalid."""


@dataclass(frozen=True)
class PlanDeps:
    session_factory: sessionmaker[Session]
    llm: LLMClient
    publish: Callable[[dict[str, Any]], Any]


# -- pure helpers -----------------------------------------------------------------------------


def wbs_tasks(wbs: WBSPlan) -> list[PlannedTask]:
    return [t for e in wbs.epics for t in e.tasks]


def task_inputs(wbs: WBSPlan) -> tuple[list[TaskInput], dict[int, str]]:
    """Engine inputs with ids 1..n in WBS order, plus engine id -> WBS id."""
    tasks = wbs_tasks(wbs)
    num = {t.local_id: k for k, t in enumerate(tasks, start=1)}
    inputs = [
        TaskInput(
            id=num[t.local_id],
            o=t.o,
            m=t.m,
            p=t.p,
            required_skills=tuple(
                RequiredSkill(skill=r.skill, level=r.level, must=r.must) for r in t.required_skills
            ),
            predecessors=tuple(num[p] for p in t.predecessors),
        )
        for t in tasks
    ]
    return inputs, {k: lid for lid, k in num.items()}


def skill_gaps(
    wbs: WBSPlan, members: Sequence[MemberInput], window: tuple[date, date]
) -> list[str]:
    """One warning per task that no member is eligible for (assignment engine rules)."""
    if not members:
        return ["the team has no members, so no task can be assigned"]
    tasks, label = task_inputs(wbs)
    return [
        f"{label[t.id]}: no team member has the must-have skills"
        for t in tasks
        if not any(is_eligible(t, m, window)[0] for m in members)
    ]


def apply_changes(
    wbs: WBSPlan, changes: Sequence[TaskChange], vocabulary: Iterable[str]
) -> WBSPlan:
    """PM edits on a copy of the plan. Raises EditError instead of repairing anything."""
    plan = wbs.model_copy(deep=True)
    vocab = list(vocabulary)

    def find(task_id: str) -> tuple[list[PlannedTask], PlannedTask]:
        for epic in plan.epics:
            for task in epic.tasks:
                if task.local_id == task_id:
                    return epic.tasks, task
        raise EditError(f"unknown task {task_id}")

    for change in changes:
        siblings, task = find(change.task_id)
        if change.op == "remove":
            siblings.remove(task)
            for other in wbs_tasks(plan):
                if task.local_id in other.predecessors:
                    other.predecessors.remove(task.local_id)
            continue

        if change.title is not None:
            task.title = change.title
        if change.description is not None:
            task.description = change.description
        o = task.o if change.o is None else change.o
        m = task.m if change.m is None else change.m
        p = task.p if change.p is None else change.p
        if not MIN_HOURS <= o <= m <= p <= MAX_HOURS:
            raise EditError(
                f"{task.local_id}: need {MIN_HOURS:g} <= o <= m <= p <= {MAX_HOURS:g} hours, "
                f"got {o:g}/{m:g}/{p:g}"
            )
        task.o, task.m, task.p = o, m, p

        if change.required_skills is not None:
            skills: dict[str, SkillReq] = {}
            for req in change.required_skills:
                name = match_skill(req.skill, vocab)
                if name is None:
                    raise EditError(f"{task.local_id}: unknown skill {req.skill!r}")
                if not 1 <= req.level <= 5:
                    raise EditError(f"{task.local_id}: skill {name} level must be 1-5")
                if name in skills:
                    raise EditError(f"{task.local_id}: skill {name} listed twice")
                skills[name] = SkillReq(skill=name, level=req.level, must=req.must)
            task.required_skills = list(skills.values())

        if change.predecessors is not None:
            ids = {t.local_id for t in wbs_tasks(plan)}
            for pred in change.predecessors:
                if pred == task.local_id:
                    raise EditError(f"{task.local_id}: a task cannot depend on itself")
                if pred not in ids:
                    raise EditError(f"{task.local_id}: unknown predecessor {pred}")
            task.predecessors = list(dict.fromkeys(change.predecessors))

    plan.epics = [e for e in plan.epics if e.tasks]
    if not plan.epics:
        raise EditError("the plan must keep at least one task")
    tasks, label = task_inputs(plan)
    try:
        topo_sort(tasks)
    except CycleError as exc:
        loop = " -> ".join(label[i] for i in exc.cycle)
        raise EditError(f"the edit creates a dependency cycle: {loop}") from exc
    return plan


# -- graph --------------------------------------------------------------------------------------

NodeResult = tuple[Any, str]  # (state update or Command, one-line summary for the timeline)


def _timed(name: str, fn: Callable[[PlanState], NodeResult], deps: PlanDeps) -> Callable:
    """Publish start/end events around a node. An interrupt ends the node as 'waiting'."""

    def node(state: PlanState) -> Any:
        base = {"thread_id": state["thread_id"], "type": "node", "node": name}
        deps.publish({**base, "phase": "start"})
        started = time.perf_counter()

        def end(summary: str) -> None:
            ms = round((time.perf_counter() - started) * 1000, 1)
            deps.publish({**base, "phase": "end", "duration_ms": ms, "summary": summary})

        try:
            update, summary = fn(state)
        except GraphInterrupt:
            end("waiting for PM review")
            raise
        end(summary)
        return update

    return node


def build_plan_graph(deps: PlanDeps) -> StateGraph:
    """Uncompiled graph; compile it with the checkpointer of your choice."""

    def window(state: PlanState) -> tuple[date, date]:
        req = state["request"]
        return date.fromisoformat(req["start_date"]), date.fromisoformat(req["deadline"])

    def members() -> list[MemberInput]:
        with deps.session_factory() as s:
            return load_members(s)

    def decompose(state: PlanState) -> NodeResult:
        with deps.session_factory() as s:
            vocab = list(s.scalars(select(Skill.name).order_by(Skill.name)))
        prompt = build_prompt(state["request"]["brief"], vocab)
        draft = deps.llm.generate_structured(PROMPT_NAME, prompt, WBSPlan)
        n = len(wbs_tasks(draft))
        update = {
            "vocabulary": vocab,
            "draft": draft.model_dump(mode="json"),
            "revision": 0,
            "decisions": [],
            "status": "planning",
        }
        return update, f"{n} tasks in {len(draft.epics)} epics drafted"

    def validate(state: PlanState) -> NodeResult:
        wbs, warnings = validate_plan(WBSPlan.model_validate(state["draft"]), state["vocabulary"])
        if not wbs.epics:
            raise ValueError("the planning agent returned no usable tasks")
        gaps = skill_gaps(wbs, members(), window(state))
        update = {"wbs": wbs.model_dump(mode="json"), "warnings": warnings, "gaps": gaps}
        return update, f"{len(warnings)} fixes, {len(gaps)} skill gaps"

    def estimate(state: PlanState) -> NodeResult:
        tasks, label = task_inputs(WBSPlan.model_validate(state["wbs"]))
        total = path_pert(tasks)  # every task: total effort, not a schedule path
        cocomo = None
        if total.te > 0:
            c = cocomo2(ksloc_from_hours(total.te))
            cocomo = Cocomo(
                loc_per_hour=DEFAULT_LOC_PER_HOUR,
                ksloc=c.ksloc,
                exponent=c.exponent,
                effort_pm=c.effort_pm,
                tdev_months=c.tdev_months,
                avg_staff=c.avg_staff,
            )
        req = state["request"]
        est = PlanEstimates(
            total_te_hours=total.te,
            total_std_hours=total.std,
            total_effort_pm=total.te / HOURS_PER_PM,
            estimated_cost=hours_cost(total.te, Decimal(req["hourly_rate"])),
            budget=Decimal(req["budget"]),
            cocomo=cocomo,
            tasks=[
                TaskEstimate(task_id=label[e.task_id], te_hours=e.te, std_hours=e.std)
                for e in map(pert, tasks)
            ],
        )
        summary = f"{total.te:.0f} h expected effort"
        if cocomo:
            summary += f", COCOMO II {cocomo.effort_pm:.1f} PM"
        return {"estimates": est.model_dump(mode="json")}, summary

    def schedule_node(state: PlanState) -> NodeResult:
        tasks, label = task_inputs(WBSPlan.model_validate(state["wbs"]))
        start, deadline = window(state)
        plan = cpm(tasks)
        # No owners yet: every task runs on the plain project calendar.
        result = schedule(tasks, {}, [], start, cpm_result=plan)
        placed = {t.task_id: t for t in result.tasks}
        out = PlanSchedule(
            start=start,
            finish=result.finish,
            deadline=deadline,
            duration_hours=plan.project_duration,
            meets_deadline=result.finish <= deadline,
            critical_path=[label[i] for i in plan.critical_paths[0]] if plan.critical_paths else [],
            tasks=[
                ScheduledWbsTask(
                    task_id=label[r.task_id],
                    start=placed[r.task_id].start,
                    end=placed[r.task_id].end,
                    total_slack_hours=r.total_slack,
                    critical=r.critical,
                )
                for r in plan.tasks
            ],
        )
        summary = f"finish {out.finish.isoformat()}, {len(out.critical_path)} critical tasks"
        return {"schedule": out.model_dump(mode="json")}, summary

    def recommend(state: PlanState) -> NodeResult:
        tasks, label = task_inputs(WBSPlan.model_validate(state["wbs"]))
        start = window(state)[0]
        team = members()
        with deps.session_factory() as s:
            names: dict[int, str] = dict(s.execute(select(Member.id, Member.name)).all())
        windows = {r.task_id: hours_to_window(start, r.es, r.ef) for r in cpm(tasks).tasks}
        plan = recommend_optimal(tasks, team, windows)
        owners = {r.task_id: r.member_id for r in plan.recommendations}
        try:
            finish: date | None = schedule(tasks, owners, team, start).finish
        except ScheduleError:
            finish = None
        by_task = {r.task_id: r for r in plan.recommendations}
        out = PlanRecommendations(
            total_score=plan.total_score,
            utilisation_std=plan.utilisation_std,
            unassigned=plan.unassigned,
            finish_with_owners=finish,
            items=[
                PlanRecommendation(
                    task_id=label[t.id],
                    member_id=by_task[t.id].member_id,
                    member_name=names.get(by_task[t.id].member_id or -1),
                    score=ScoreOut.model_validate(by_task[t.id].score)
                    if by_task[t.id].score
                    else None,
                    candidates=[
                        CandidateBrief(
                            member_id=c.member_id,
                            name=names.get(c.member_id, f"Member {c.member_id}"),
                            total=c.score.total,
                        )
                        for c in by_task[t.id].candidates
                    ],
                    ineligible_count=len(by_task[t.id].ineligible),
                )
                for t in tasks
            ],
        )
        assigned = len(tasks) - plan.unassigned
        summary = f"{assigned}/{len(tasks)} tasks matched, total score {plan.total_score:.0f}"
        return {"recommendations": out.model_dump(mode="json")}, summary

    def pm_review(state: PlanState) -> NodeResult:
        review = PlanReview(
            thread_id=state["thread_id"],
            revision=state["revision"],
            project_name=state["request"]["project_name"],
            wbs=WBSPlan.model_validate(state["wbs"]),
            warnings=state["warnings"] + state["gaps"],
            estimates=PlanEstimates.model_validate(state["estimates"]),
            schedule=PlanSchedule.model_validate(state["schedule"]),
            recommendations=PlanRecommendations.model_validate(state["recommendations"]),
        )
        decision = DECISION.validate_python(interrupt(review.model_dump(mode="json")))
        decisions = [*state["decisions"], decision.model_dump(mode="json")]

        if decision.action == "approve":
            return Command(goto="commit", update={"decisions": decisions}), "approved"
        if decision.action == "reject":
            update = {"decisions": decisions, "status": "rejected", "reason": decision.reason}
            return Command(goto=END, update=update), "rejected"
        wbs = apply_changes(
            WBSPlan.model_validate(state["wbs"]), decision.changes, state["vocabulary"]
        )
        update = {
            "wbs": wbs.model_dump(mode="json"),
            "gaps": skill_gaps(wbs, members(), window(state)),
            "revision": state["revision"] + 1,
            "decisions": decisions,
        }
        return Command(goto="estimate", update=update), f"{len(decision.changes)} edits applied"

    def commit(state: PlanState) -> NodeResult:
        thread_id, req = state["thread_id"], state["request"]
        wbs = WBSPlan.model_validate(state["wbs"])
        actor = state["decisions"][-1].get("actor", "pm")
        with deps.session_factory() as s:
            # Re-running after a crash between DB commit and checkpoint must not duplicate.
            done = s.scalar(
                select(AuditLog.entity_id).where(
                    AuditLog.action == APPROVED_ACTION,
                    AuditLog.after["thread_id"].astext == thread_id,
                )
            )
            if done is not None:
                return {"status": "committed", "project_id": done}, f"project {done} exists"

            project = Project(
                name=req["project_name"],
                brief=req["brief"],
                start_date=date.fromisoformat(req["start_date"]),
                deadline=date.fromisoformat(req["deadline"]),
                budget=Decimal(req["budget"]),
                hourly_rate=Decimal(req["hourly_rate"]),
            )
            rows: dict[str, Task] = {}
            epics = []
            for position, e in enumerate(wbs.epics):
                epic = Epic(project=project, title=e.title[:200], position=position)
                epics.append(epic)
                for t in e.tasks:
                    rows[t.local_id] = Task(
                        project=project,
                        epic=epic,
                        title=t.title[:200],
                        description=t.description or None,
                        optimistic_hours=t.o,
                        most_likely_hours=t.m,
                        pessimistic_hours=t.p,
                        required_skills=[r.model_dump() for r in t.required_skills],
                    )
            s.add(project)
            s.add_all(epics)
            s.add_all(rows.values())
            s.flush()
            s.add_all(
                Dependency(pred_task_id=rows[p].id, succ_task_id=rows[t.local_id].id)
                for t in wbs_tasks(wbs)
                for p in t.predecessors
            )
            s.add(
                AuditLog(
                    actor=actor,
                    action=APPROVED_ACTION,
                    entity="project",
                    entity_id=project.id,
                    before=None,
                    after={
                        "thread_id": thread_id,
                        "revision": state["revision"],
                        "epics": len(epics),
                        "tasks": len(rows),
                        "edits": sum(d["action"] == "edit" for d in state["decisions"]),
                    },
                    reason="plan approved in the planning workflow",
                )
            )
            items = [
                ApplyItem(
                    task_id=rows[i["task_id"]].id,
                    member_id=i["member_id"],
                    source=AssignmentSource.AI,
                    reason=f"planning workflow, optimal mode, score {i['score']['total']:.1f}",
                    score_breakdown=i["score"],
                )
                for i in state["recommendations"]["items"]
                if i["member_id"] is not None
            ]
            if items:  # commits the whole transaction, with one audit row per assignment
                apply_assignments(s, project.id, ApplyRequest(actor=actor, items=items))
            else:
                s.commit()
            project_id = project.id
        update = {"status": "committed", "project_id": project_id}
        return update, f"project {project_id} created with {len(rows)} tasks"

    graph = StateGraph(PlanState)
    fns: dict[str, Callable[[PlanState], NodeResult]] = {
        "decompose": decompose,
        "validate": validate,
        "estimate": estimate,
        "schedule": schedule_node,
        "recommend": recommend,
        "pm_review": pm_review,
        "commit": commit,
    }
    for name, fn in fns.items():
        destinations = ("estimate", "commit", END) if name == "pm_review" else None
        graph.add_node(name, _timed(name, fn, deps), destinations=destinations)
    graph.add_edge(START, "decompose")
    for a, b in pairwise(NODES[:6]):  # decompose ... pm_review; pm_review routes by Command
        graph.add_edge(a, b)
    graph.add_edge("commit", END)
    return graph
