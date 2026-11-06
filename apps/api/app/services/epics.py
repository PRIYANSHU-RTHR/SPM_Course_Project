from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Epic
from app.schemas.epic import EpicCreate, EpicUpdate
from app.services.common import PageParams, apply_changes, commit, get_or_404, paginate
from app.services.projects import get_project


def get_epic(session: Session, epic_id: int) -> Epic:
    return get_or_404(session, Epic, epic_id, "Epic")


def list_epics(session: Session, project_id: int, page: PageParams) -> tuple[list[Epic], int]:
    get_project(session, project_id)
    stmt = select(Epic).where(Epic.project_id == project_id).order_by(Epic.position, Epic.id)
    return paginate(session, stmt, page)


def create_epic(session: Session, project_id: int, data: EpicCreate) -> Epic:
    get_project(session, project_id)
    epic = Epic(project_id=project_id, **data.model_dump())
    session.add(epic)
    commit(session)
    return epic


def update_epic(session: Session, epic_id: int, data: EpicUpdate) -> Epic:
    epic = get_epic(session, epic_id)
    apply_changes(epic, data.changes())
    commit(session)
    return epic


def delete_epic(session: Session, epic_id: int) -> None:
    """Deletes the epic and (by FK cascade) its tasks."""
    session.delete(get_epic(session, epic_id))
    commit(session)
