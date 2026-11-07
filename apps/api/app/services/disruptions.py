"""Disruptions are facts: they are checked up front and written to the DB (audited) at once.
The PM only approves or rejects the *reassignment* that follows (workflows/reallocate.py)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NotFoundError, ValidationFailedError
from app.models import (
    AuditLog,
    Availability,
    AvailabilityKind,
    Dependency,
    Member,
    Project,
    Reallocation,
    ReallocationStatus,
    Task,
    TaskStatus,
)
from app.schemas.reallocation import (
    Disruption,
    LeaveDisruption,
    ScopeAddDisruption,
    SlipDisruption,
)
from app.services.inputs import get_project
from app.services.tasks import _check_epic_in_project, _check_skills_exist


def _project_task(session: Session, project_id: int, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if task is None or task.project_id != project_id:
        raise NotFoundError(
            f"Task {task_id} not found in project {project_id}", details={"task_id": task_id}
        )
    return task


def check_disruption(session: Session, project_id: int, d: Disruption) -> Project:
    """Raise 404/422 before anything is written or a workflow is started."""
    project = get_project(session, project_id)
    if isinstance(d, LeaveDisruption):
        if session.get(Member, d.member_id) is None:
            raise NotFoundError(
                f"Member {d.member_id} not found", details={"member_id": d.member_id}
            )
    elif isinstance(d, SlipDisruption):
        task = _project_task(session, project_id, d.task_id)
        if task.status == TaskStatus.DONE:
            raise ValidationFailedError(
                f"Task {d.task_id} is already done", details={"task_id": d.task_id}
            )
    else:
        _check_epic_in_project(session, d.task.epic_id, project_id)
        _check_skills_exist(session, d.task.required_skills)
        for pred in d.predecessors:
            _project_task(session, project_id, pred)
    return project


def apply_disruption(session: Session, project: Project, d: Disruption) -> dict[str, Any]:
    """Write the fact and one audit row; commit. Returns ids the workflow needs."""
    reason = d.reason or f"disruption: {d.type}"
    if isinstance(d, LeaveDisruption):
        session.add(
            Availability(
                member_id=d.member_id,
                kind=AvailabilityKind.LEAVE,
                start_date=d.start_date,
                end_date=d.end_date,
                hours_per_week=0,
                note=reason,
            )
        )
        # Leave is about a person, not a task; logged on the project so the project's
        # audit trail shows it.
        audit = AuditLog(
            actor=d.actor,
            action="disruption.leave",
            entity="project",
            entity_id=project.id,
            before=None,
            after={
                "member_id": d.member_id,
                "start_date": d.start_date.isoformat(),
                "end_date": d.end_date.isoformat(),
            },
            reason=reason,
        )
        session.add(audit)
        session.commit()
        return {"new_task_id": None}

    if isinstance(d, SlipDisruption):
        task = _project_task(session, project.id, d.task_id)
        before = {
            "optimistic_hours": task.optimistic_hours,
            "most_likely_hours": task.most_likely_hours,
            "pessimistic_hours": task.pessimistic_hours,
        }
        task.optimistic_hours += d.extra_hours
        task.most_likely_hours += d.extra_hours
        task.pessimistic_hours += d.extra_hours
        session.add(
            AuditLog(
                actor=d.actor,
                action="disruption.slip",
                entity="task",
                entity_id=task.id,
                before=before,
                after={
                    "optimistic_hours": task.optimistic_hours,
                    "most_likely_hours": task.most_likely_hours,
                    "pessimistic_hours": task.pessimistic_hours,
                },
                reason=reason,
            )
        )
        session.commit()
        return {"new_task_id": None}

    assert isinstance(d, ScopeAddDisruption)
    task = Task(project_id=project.id, **d.task.model_dump())
    session.add(task)
    session.flush()
    session.add_all(Dependency(pred_task_id=p, succ_task_id=task.id) for p in d.predecessors)
    session.add(
        AuditLog(
            actor=d.actor,
            action="disruption.scope_add",
            entity="task",
            entity_id=task.id,
            before=None,
            after={**d.task.model_dump(mode="json"), "predecessors": d.predecessors},
            reason=reason,
        )
    )
    session.commit()
    return {"new_task_id": task.id}


def pending_for_project(session: Session, project_id: int) -> list[str]:
    """Thread ids of proposals still waiting for the PM."""
    return list(
        session.scalars(
            select(Reallocation.thread_id).where(
                Reallocation.project_id == project_id,
                Reallocation.status == ReallocationStatus.PENDING,
            )
        )
    )
