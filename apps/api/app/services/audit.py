"""A project's audit trail. `audit_log` has no project column, so rows are matched through
the entity they describe (project, task, assignment, risk, reallocation).

Each row also gets a one-line, human-readable `summary` built from its own before/after
values plus the names of the tasks, members and risks it mentions (a template, no LLM)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import Assignment, AuditLog, Member, Reallocation, Risk, Task
from app.schemas.reallocation import AuditRead
from app.services.common import PageParams, paginate
from app.services.inputs import get_project

# -- summaries (pure) ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Names:
    tasks: Mapping[int, str] = field(default_factory=dict)
    members: Mapping[int, str] = field(default_factory=dict)
    risks: Mapping[int, str] = field(default_factory=dict)

    def task(self, task_id: Any) -> str:
        if not isinstance(task_id, int):
            return "a task"
        title = self.tasks.get(task_id)
        return f"T-{task_id:03d} “{title}”" if title else f"T-{task_id:03d}"

    def member(self, member_id: Any) -> str:
        if not isinstance(member_id, int):
            return "nobody"
        return self.members.get(member_id, f"member #{member_id}")

    def risk(self, risk_id: int) -> str:
        title = self.risks.get(risk_id)
        return f"risk “{title}”" if title else f"risk #{risk_id}"


def actor_label(actor: str) -> str:
    """`system:risk-engine` -> `Risk engine`; people are shown as given."""
    if actor.startswith("system:"):
        return actor.removeprefix("system:").replace("-", " ").capitalize()
    return actor


def _hours(value: Any) -> str:
    return f"{value:g} h" if isinstance(value, int | float) else "?"


def _leave(a: AuditLog, n: Names, who: str) -> str:
    after = a.after or {}
    return (
        f"{who} recorded leave for {n.member(after.get('member_id'))} "
        f"from {after.get('start_date')} to {after.get('end_date')}"
    )


def _slip(a: AuditLog, n: Names, who: str) -> str:
    before, after = a.before or {}, a.after or {}
    old, new = before.get("most_likely_hours"), after.get("most_likely_hours")
    numeric = isinstance(old, int | float) and isinstance(new, int | float)
    extra = f" (+{new - old:g} h)" if numeric else ""
    return (
        f"{who} recorded a slip on {n.task(a.entity_id)}: "
        f"most likely {_hours(old)} → {_hours(new)}{extra}"
    )


def _scope_add(a: AuditLog, n: Names, who: str) -> str:
    after = a.after or {}
    return (
        f"{who} added new scope {n.task(a.entity_id)}, "
        f"most likely {_hours(after.get('most_likely_hours'))}"
    )


def _assignment(a: AuditLog, n: Names, who: str) -> str:
    after = a.after or {}
    how = "PM override" if after.get("source") == "pm_override" else "AI recommendation"
    task, to = n.task(after.get("task_id")), n.member(after.get("member_id"))
    if a.before is None:
        return f"{who} assigned {task} to {to} ({how})"
    return f"{who} reassigned {task} from {n.member(a.before.get('member_id'))} to {to} ({how})"


def _reallocation(verb: str) -> Callable[[AuditLog, Names, str], str]:
    def describe(a: AuditLog, n: Names, who: str) -> str:
        return f"{who} {verb} reallocation proposal #{a.entity_id}"

    return describe


def _risk_score(a: AuditLog) -> str:
    after = a.after or {}
    p, i = after.get("probability"), after.get("impact")
    return f" (P{p} x I{i} = {p * i})" if isinstance(p, int) and isinstance(i, int) else ""


def _risk(verb: str) -> Callable[[AuditLog, Names, str], str]:
    def describe(a: AuditLog, n: Names, who: str) -> str:
        score = "" if verb == "closed" else _risk_score(a)
        return f"{who} {verb} {n.risk(a.entity_id)}{score}"

    return describe


def _risk_plan(a: AuditLog, n: Names, who: str) -> str:
    return f"{who} generated the RMMM plan for {n.risk(a.entity_id)}"


def _advance(a: AuditLog, n: Names, who: str) -> str:
    before, after = a.before or {}, a.after or {}
    return (
        f"{who} advanced the simulated clock from {before.get('sim_date')} to "
        f"{after.get('sim_date')} ({after.get('working_days', '?')} working days)"
    )


def _plan_approved(a: AuditLog, n: Names, who: str) -> str:
    after = a.after or {}
    edits = after.get("edits") or 0
    rounds = f" after {edits} edit round{'s' if edits != 1 else ''}" if edits else ""
    return (
        f"{who} approved the generated plan: {after.get('epics', '?')} epics, "
        f"{after.get('tasks', '?')} tasks{rounds}"
    )


_DESCRIBE: dict[str, Callable[[AuditLog, Names, str], str]] = {
    "disruption.leave": _leave,
    "disruption.slip": _slip,
    "disruption.scope_add": _scope_add,
    "assignment.ai": _assignment,
    "assignment.pm_override": _assignment,
    "reallocation.approved": _reallocation("approved"),
    "reallocation.rejected": _reallocation("rejected"),
    "risk_opened": _risk("opened"),
    "risk_reopened": _risk("reopened"),
    "risk_closed": _risk("closed"),
    "risk.plan": _risk_plan,
    "simulation.advance": _advance,
    "workflow.plan_approved": _plan_approved,
}


def summarize(row: AuditLog, names: Names) -> str:
    who = actor_label(row.actor)
    describe = _DESCRIBE.get(row.action)
    if describe is None:
        return f"{who}: {row.action} on {row.entity} #{row.entity_id}"
    return describe(row, names, who)


# -- queries ------------------------------------------------------------------------------------


def _ids(rows: list[AuditLog]) -> tuple[set[int], set[int], set[int]]:
    tasks: set[int] = set()
    members: set[int] = set()
    risks: set[int] = set()
    for a in rows:
        if a.entity == "task":
            tasks.add(a.entity_id)
        elif a.entity == "risk":
            risks.add(a.entity_id)
        for values in (a.before or {}, a.after or {}):
            if isinstance(t := values.get("task_id"), int):
                tasks.add(t)
            if isinstance(m := values.get("member_id"), int):
                members.add(m)
    return tasks, members, risks


def load_names(session: Session, rows: list[AuditLog]) -> Names:
    tasks, members, risks = _ids(rows)
    return Names(
        tasks=dict(session.execute(select(Task.id, Task.title).where(Task.id.in_(tasks))).all()),
        members=dict(
            session.execute(select(Member.id, Member.name).where(Member.id.in_(members))).all()
        ),
        risks=dict(session.execute(select(Risk.id, Risk.title).where(Risk.id.in_(risks))).all()),
    )


def list_audit(session: Session, project_id: int, page: PageParams) -> tuple[list[AuditRead], int]:
    get_project(session, project_id)
    task_ids = select(Task.id).where(Task.project_id == project_id)
    by_entity = {
        "task": task_ids,
        "assignment": select(Assignment.id).where(Assignment.task_id.in_(task_ids)),
        "risk": select(Risk.id).where(Risk.project_id == project_id),
        "reallocation": select(Reallocation.id).where(Reallocation.project_id == project_id),
    }
    belongs = or_(
        and_(AuditLog.entity == "project", AuditLog.entity_id == project_id),
        *(
            and_(AuditLog.entity == entity, AuditLog.entity_id.in_(ids))
            for entity, ids in by_entity.items()
        ),
    )
    stmt = select(AuditLog).where(belongs).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    rows, total = paginate(session, stmt, page)
    names = load_names(session, rows)
    columns = [f for f in AuditRead.model_fields if f != "summary"]
    items = [
        AuditRead(summary=summarize(a, names), **{f: getattr(a, f) for f in columns}) for a in rows
    ]
    return items, total
