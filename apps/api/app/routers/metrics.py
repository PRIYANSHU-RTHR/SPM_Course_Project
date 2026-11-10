"""Headline project numbers in one call (KPI chips that animate before -> after)."""

from fastapi import APIRouter, Request

from app.routers.deps import SessionDep
from app.schemas.common import NOT_FOUND
from app.schemas.metrics import ProjectMetrics
from app.services.metrics import project_metrics

router = APIRouter(prefix="/projects", tags=["metrics"])


@router.get("/{project_id}/metrics", name="get", response_model=ProjectMetrics, responses=NOT_FOUND)
def get_metrics(request: Request, session: SessionDep, project_id: int) -> ProjectMetrics:
    """P(on time), P50/P80 finish, SPI, CPI, open risks and overloaded members at the
    project's clock. All engine output; refetch after an approval to get the "after" values."""
    return project_metrics(session, project_id, request.app.state.settings.sim_seed)
