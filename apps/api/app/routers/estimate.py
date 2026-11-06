from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.estimate import ProjectEstimate
from app.services.estimation import project_estimate

router = APIRouter(prefix="/projects", tags=["estimation"])


@router.get("/{project_id}/estimate", name="get", response_model=ProjectEstimate)
def get_estimate(
    project_id: int, session: Annotated[Session, Depends(get_session)]
) -> ProjectEstimate:
    return project_estimate(session, project_id)
