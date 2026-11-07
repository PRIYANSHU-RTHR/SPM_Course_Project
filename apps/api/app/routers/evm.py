from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.evm import ProjectEvm
from app.services.evm import project_evm
from app.services.inputs import get_project, project_today

router = APIRouter(prefix="/projects", tags=["evm"])


@router.get("/{project_id}/evm", name="get", response_model=ProjectEvm)
def get_evm(
    project_id: int,
    session: Annotated[Session, Depends(get_session)],
    as_of: Annotated[
        date | None, Query(description="Status date (default: the project's clock)")
    ] = None,
) -> ProjectEvm:
    return project_evm(
        session, project_id, as_of or project_today(get_project(session, project_id))
    )
