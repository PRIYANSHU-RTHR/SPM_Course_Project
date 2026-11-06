"""Builds the dependency network from the DB and runs the CPM engine."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.cpm import CycleError, cpm
from app.engines.types import TaskInput
from app.errors import ConflictError, NotFoundError
from app.models import Dependency, Project, Task
from app.schemas.cpm import CpmTask, ProjectCpm


def project_cpm(session: Session, project_id: int) -> ProjectCpm:
    if session.get(Project, project_id) is None:
        raise NotFoundError(f"Project {project_id} not found", details={"project_id": project_id})

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

    tasks = [
        TaskInput(
            id=t.id,
            o=t.optimistic_hours,
            m=t.most_likely_hours,
            p=t.pessimistic_hours,
            predecessors=tuple(preds[t.id]),
        )
        for t in rows
    ]
    try:
        result = cpm(tasks)
    except CycleError as exc:
        raise ConflictError(str(exc), details={"cycle": exc.cycle}) from exc

    return ProjectCpm(
        project_id=project_id,
        project_duration_hours=result.project_duration,
        critical_paths=[list(p) for p in result.critical_paths],
        tasks=[
            CpmTask(
                task_id=r.task_id,
                duration_hours=r.duration,
                es=r.es,
                ef=r.ef,
                ls=r.ls,
                lf=r.lf,
                total_slack=r.total_slack,
                free_slack=r.free_slack,
                critical=r.critical,
            )
            for r in result.tasks
        ],
    )
