from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.schedule import ProjectSchedule
from app.services.schedule import project_schedule

router = APIRouter(prefix="/projects", tags=["schedule"])


@router.get("/{project_id}/schedule", response_model=ProjectSchedule)
def get_schedule(
    project_id: int, session: Annotated[Session, Depends(get_session)]
) -> ProjectSchedule:
    return project_schedule(session, project_id)
