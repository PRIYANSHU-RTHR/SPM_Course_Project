"""Turns DB rows into engine inputs. Shared by every engine service."""

from collections import defaultdict
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.engines.cpm import CycleError, cpm
from app.engines.types import CPMResult, LeaveRange, MemberInput, RequiredSkill, TaskInput
from app.errors import ConflictError, NotFoundError
from app.models import AvailabilityKind, Dependency, Member, MemberSkill, Project, Task


def get_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found", details={"project_id": project_id})
    return project


def project_today(project: Project) -> date:
    """The project's simulated clock (`sim_date`), else today's date in UTC."""
    return project.sim_date or datetime.now(UTC).date()


def load_tasks(session: Session, project_id: int) -> list[TaskInput]:
    rows = session.scalars(
        select(Task).where(Task.project_id == project_id).order_by(Task.id)
    ).all()
    preds: dict[int, list[int]] = defaultdict(list)
    deps = session.execute(
        select(Dependency.pred_task_id, Dependency.succ_task_id)
        .join(Task, Task.id == Dependency.succ_task_id)
        .where(Task.project_id == project_id)
    )
    for pred, succ in deps:
        preds[succ].append(pred)
    return [
        TaskInput(
            id=t.id,
            o=t.optimistic_hours,
            m=t.most_likely_hours,
            p=t.pessimistic_hours,
            priority=t.priority,
            required_skills=tuple(
                RequiredSkill(
                    skill=s["skill"],
                    level=int(s["level"]),
                    must=bool(s.get("must", True)),
                    weight=float(s.get("weight", 1.0)),
                )
                for s in t.required_skills
            ),
            predecessors=tuple(preds[t.id]),
        )
        for t in rows
    ]


def load_members(session: Session) -> list[MemberInput]:
    members = session.scalars(
        select(Member)
        .options(
            selectinload(Member.skills).selectinload(MemberSkill.skill),
            selectinload(Member.availability),
        )
        .order_by(Member.id)
    ).all()
    out = []
    for m in members:
        work = [a.hours_per_week for a in m.availability if a.kind == AvailabilityKind.WORK]
        out.append(
            MemberInput(
                id=m.id,
                skills={s.skill.name: s.level for s in m.skills},
                # shortcut: one weekly capacity per member (largest `work` row); per-range
                # capacity needs MemberInput to carry ranges, add if the seed data uses them.
                hours_per_week=max(work, default=0.0),
                leave=tuple(
                    LeaveRange(a.start_date, a.end_date)
                    for a in m.availability
                    if a.kind == AvailabilityKind.LEAVE
                ),
            )
        )
    return out


def run_cpm(tasks: list[TaskInput]) -> CPMResult:
    try:
        return cpm(tasks)
    except CycleError as exc:
        raise ConflictError(str(exc), details={"cycle": exc.cycle}) from exc
