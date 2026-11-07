"""Schedules the project with its current assignments."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.scheduler import ScheduleError, schedule
from app.engines.types import ScheduleResult
from app.errors import ValidationFailedError
from app.models import Assignment, Project, Task
from app.schemas.schedule import ProjectSchedule, ScheduledTaskOut, WeekLoadOut
from app.services.inputs import get_project, load_members, load_tasks, run_cpm


def build_schedule(session: Session, project: Project, as_of: date | None = None) -> ScheduleResult:
    """Baseline plan; with `as_of`, the remaining work re-planned from that day."""
    tasks = load_tasks(session, project.id)
    progress = None
    if as_of is not None:
        progress = dict(
            session.execute(
                select(Task.id, Task.percent_complete).where(Task.project_id == project.id)
            ).all()
        )
    rows = session.execute(
        select(Assignment.task_id, Assignment.member_id)
        .join(Task, Task.id == Assignment.task_id)
        .where(Task.project_id == project.id, Assignment.is_current)
    )
    try:
        return schedule(
            tasks,
            dict(rows.tuples().all()),
            load_members(session),
            project.start_date,
            cpm_result=run_cpm(tasks),
            progress=progress,
            as_of=as_of,
        )
    except ScheduleError as exc:
        raise ValidationFailedError(str(exc)) from exc


def project_schedule(session: Session, project_id: int, as_of: date) -> ProjectSchedule:
    project = get_project(session, project_id)
    result = build_schedule(session, project, as_of)
    return ProjectSchedule(
        project_id=project_id,
        start=project.start_date,
        finish=result.finish,
        deadline=project.deadline,
        tasks=[ScheduledTaskOut.model_validate(t) for t in result.tasks],
        loads=[WeekLoadOut.model_validate(w) for w in result.loads],
        delayed=list(result.delayed),
    )
