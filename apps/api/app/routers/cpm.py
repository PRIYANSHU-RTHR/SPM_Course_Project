from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.cpm import ProjectCpm
from app.services.cpm import project_cpm

router = APIRouter(prefix="/projects", tags=["schedule"])


@router.get("/{project_id}/cpm", name="get_cpm", response_model=ProjectCpm)
def get_cpm(project_id: int, session: Annotated[Session, Depends(get_session)]) -> ProjectCpm:
    return project_cpm(session, project_id)
