from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.schedule import ProjectSchedule
from app.services.inputs import get_project, project_today
from app.services.schedule import project_schedule

router = APIRouter(prefix="/projects", tags=["schedule"])


@router.get("/{project_id}/schedule", name="get", response_model=ProjectSchedule)
def get_schedule(
    project_id: int,
    session: Annotated[Session, Depends(get_session)],
    as_of: Annotated[
        date | None,
        Query(description="Plan remaining work from this date (default: the project's clock)"),
    ] = None,
) -> ProjectSchedule:
    return project_schedule(
        session, project_id, as_of or project_today(get_project(session, project_id))
    )
