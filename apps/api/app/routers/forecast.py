from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.db import get_session
from app.engines.montecarlo import DEFAULT_RUNS
from app.schemas.forecast import ProjectForecast
from app.services.forecast import project_forecast

router = APIRouter(prefix="/projects", tags=["forecast"])


@router.get("/{project_id}/forecast", name="get", response_model=ProjectForecast)
def get_forecast(
    project_id: int,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    n: Annotated[int, Query(ge=100, le=50_000)] = DEFAULT_RUNS,
) -> ProjectForecast:
    return project_forecast(session, project_id, n, request.app.state.settings.sim_seed)
