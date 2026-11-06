"""Builds engine inputs from the DB and runs the estimation engine."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.estimation import (
    DEFAULT_LOC_PER_HOUR,
    HOURS_PER_PM,
    cocomo2,
    ksloc_from_hours,
    path_pert,
    pert,
)
from app.engines.types import TaskInput
from app.errors import NotFoundError
from app.models import Project, Task
from app.schemas.estimate import Cocomo, ProjectEstimate, TaskPert


def project_estimate(session: Session, project_id: int) -> ProjectEstimate:
    if session.get(Project, project_id) is None:
        raise NotFoundError(f"Project {project_id} not found", details={"project_id": project_id})

    rows = session.scalars(
        select(Task).where(Task.project_id == project_id).order_by(Task.id)
    ).all()
    tasks = [
        TaskInput(id=t.id, o=t.optimistic_hours, m=t.most_likely_hours, p=t.pessimistic_hours)
        for t in rows
    ]
    total = path_pert(tasks)  # all tasks: total effort, not a schedule path

    cocomo = None
    if total.te > 0:
        ksloc = ksloc_from_hours(total.te)
        c = cocomo2(ksloc)
        cocomo = Cocomo(
            loc_per_hour=DEFAULT_LOC_PER_HOUR,
            ksloc=c.ksloc,
            exponent=c.exponent,
            effort_pm=c.effort_pm,
            tdev_months=c.tdev_months,
            avg_staff=c.avg_staff,
        )

    return ProjectEstimate(
        project_id=project_id,
        task_count=len(tasks),
        total_te_hours=total.te,
        total_std_hours=total.std,
        total_effort_pm=total.te / HOURS_PER_PM,
        tasks=[
            TaskPert(task_id=e.task_id, te_hours=e.te, variance=e.variance, std_hours=e.std)
            for e in map(pert, tasks)
        ],
        cocomo=cocomo,
    )
