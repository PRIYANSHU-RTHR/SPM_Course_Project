"""Builds engine inputs from the DB and runs the estimation engine."""

from sqlalchemy.orm import Session

from app.engines.estimation import (
    DEFAULT_LOC_PER_HOUR,
    HOURS_PER_PM,
    cocomo2,
    ksloc_from_hours,
    path_pert,
    pert,
)
from app.schemas.estimate import Cocomo, ProjectEstimate, TaskPert
from app.services.inputs import get_project, load_tasks


def project_estimate(session: Session, project_id: int) -> ProjectEstimate:
    get_project(session, project_id)
    tasks = load_tasks(session, project_id)
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
