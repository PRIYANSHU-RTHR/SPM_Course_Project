from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.assignment import AppliedAssignment, ApplyRequest, Mode, RecommendResponse
from app.services import assignment

router = APIRouter(prefix="/projects", tags=["assignment"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/{project_id}/assignments/recommend", response_model=RecommendResponse)
def recommend(
    project_id: int, session: SessionDep, mode: Annotated[Mode, Query()] = "optimal"
) -> RecommendResponse:
    return assignment.recommend(session, project_id, mode)


@router.post("/{project_id}/assignments/apply", response_model=list[AppliedAssignment])
def apply(project_id: int, body: ApplyRequest, session: SessionDep) -> list[AppliedAssignment]:
    return assignment.apply(session, project_id, body)
