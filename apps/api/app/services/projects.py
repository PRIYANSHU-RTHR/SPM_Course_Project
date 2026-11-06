from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ValidationFailedError
from app.models import Assignment, Dependency, Epic, Project, Task
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.common import PageParams, apply_changes, commit, get_or_404, paginate


@dataclass(frozen=True)
class ProjectGraph:
    project: Project
    epics: list[Epic]
    tasks: list[Task]
    dependencies: list[Dependency]
    assignments: list[Assignment]


def get_project(session: Session, project_id: int) -> Project:
    return get_or_404(session, Project, project_id, "Project")


def list_projects(session: Session, page: PageParams) -> tuple[list[Project], int]:
    return paginate(session, select(Project).order_by(Project.id), page)


def create_project(session: Session, data: ProjectCreate) -> Project:
    project = Project(**data.model_dump())
    session.add(project)
    commit(session)
    return project


def update_project(session: Session, project_id: int, data: ProjectUpdate) -> Project:
    project = get_project(session, project_id)
    apply_changes(project, data.changes())
    if project.deadline < project.start_date:
        session.rollback()
        raise ValidationFailedError(
            "deadline must be on or after start_date",
            details={"start_date": str(project.start_date), "deadline": str(project.deadline)},
        )
    commit(session)
    return project


def delete_project(session: Session, project_id: int) -> None:
    session.delete(get_project(session, project_id))
    commit(session)


def get_project_graph(session: Session, project_id: int) -> ProjectGraph:
    project = get_project(session, project_id)
    task_ids = select(Task.id).where(Task.project_id == project_id)
    return ProjectGraph(
        project=project,
        epics=list(
            session.scalars(
                select(Epic).where(Epic.project_id == project_id).order_by(Epic.position, Epic.id)
            )
        ),
        tasks=list(
            session.scalars(select(Task).where(Task.project_id == project_id).order_by(Task.id))
        ),
        dependencies=list(
            session.scalars(
                select(Dependency)
                .where(Dependency.pred_task_id.in_(task_ids))
                .order_by(Dependency.id)
            )
        ),
        assignments=list(
            session.scalars(
                select(Assignment)
                .where(Assignment.task_id.in_(task_ids), Assignment.is_current)
                .order_by(Assignment.task_id)
            )
        ),
    )
