"""Builds the dependency network from the DB and runs the CPM engine."""

from sqlalchemy.orm import Session

from app.schemas.cpm import CpmTask, ProjectCpm
from app.services.inputs import get_project, load_tasks, run_cpm


def project_cpm(session: Session, project_id: int) -> ProjectCpm:
    get_project(session, project_id)
    result = run_cpm(load_tasks(session, project_id))

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
