from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.agents.explanation import Explanation
from app.agents.llm import LLMClient
from app.db import get_session
from app.schemas.assignment import AppliedAssignment, ApplyRequest, Mode, RecommendResponse
from app.services import agents, assignment

router = APIRouter(prefix="/projects", tags=["assignment"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/{project_id}/assignments/recommend", name="recommend", response_model=RecommendResponse
)
def recommend(
    project_id: int, session: SessionDep, mode: Annotated[Mode, Query()] = "optimal"
) -> RecommendResponse:
    return assignment.recommend(session, project_id, mode)


@router.post(
    "/{project_id}/assignments/apply", name="apply", response_model=list[AppliedAssignment]
)
def apply(project_id: int, body: ApplyRequest, session: SessionDep) -> list[AppliedAssignment]:
    return assignment.apply(session, project_id, body)


@router.get(
    "/{project_id}/assignments/{task_id}/explain", name="explain", response_model=Explanation
)
def explain(
    project_id: int,
    task_id: int,
    request: Request,
    session: SessionDep,
    mode: Annotated[Mode, Query()] = "optimal",
) -> Explanation:
    """Why the engine recommends this member; model text only if every number is grounded."""
    client = LLMClient(request.app.state.settings)
    return agents.explain_assignment(session, client, project_id, task_id, mode)
