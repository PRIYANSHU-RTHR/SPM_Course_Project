from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.agents.llm import LLMClient
from app.routers.deps import PageDep, SessionDep
from app.schemas.common import CONFLICT, NOT_FOUND
from app.schemas.risk import RiskPage, RiskRead, RiskRefreshResult
from app.services import agents
from app.services import risk_service as service

router = APIRouter(prefix="/projects", tags=["risks"])


@router.get("/{project_id}/risks", name="list", response_model=RiskPage, responses=NOT_FOUND)
def list_risks(
    session: SessionDep,
    project_id: int,
    page: PageDep,
    include_closed: Annotated[bool, Query(description="Also return closed risks")] = False,
) -> RiskPage:
    """Risk register, highest score (probability x impact) first."""
    items, total = service.list_risks(session, project_id, page, include_closed)
    return RiskPage(
        items=[RiskRead.model_validate(r) for r in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "/{project_id}/risks/refresh",
    name="refresh",
    response_model=RiskRefreshResult,
    responses={**NOT_FOUND, **CONFLICT},
)
def refresh_risks(
    request: Request,
    session: SessionDep,
    project_id: int,
    as_of: Annotated[date | None, Query(description="Status date (default: today, UTC)")] = None,
) -> RiskRefreshResult:
    """Re-run every risk rule; opens, updates, reopens and closes register rows."""
    return service.refresh_risks(
        session,
        project_id,
        as_of or datetime.now(UTC).date(),
        request.app.state.settings.sim_seed,
    )


@router.post(
    "/{project_id}/risks/{risk_id}/plan", name="plan", response_model=RiskRead, responses=NOT_FOUND
)
def plan_risk(request: Request, session: SessionDep, project_id: int, risk_id: int) -> RiskRead:
    """Generate and store the RMMM plan (mitigation, monitoring trigger, contingency, owner)."""
    client = LLMClient(request.app.state.settings)
    return RiskRead.model_validate(agents.plan_risk_rmmm(session, client, project_id, risk_id))
