"""Reading reallocation proposals (the rows the reallocation workflow writes)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Reallocation
from app.services.inputs import get_project


def get_reallocation(session: Session, project_id: int, thread_id: str) -> Reallocation:
    get_project(session, project_id)
    row = session.scalar(
        select(Reallocation).where(
            Reallocation.project_id == project_id, Reallocation.thread_id == thread_id
        )
    )
    if row is None:
        raise NotFoundError(
            f"Proposal {thread_id} not found in project {project_id}",
            details={"thread_id": thread_id},
        )
    return row
