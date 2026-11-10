"""Simulated project clock (demo) and the project's audit trail."""

from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.routers.deps import ActorDep, PageDep, SessionDep
from app.schemas.common import NOT_FOUND
from app.schemas.reallocation import AdvanceResult, AuditPage
from app.services.audit import list_audit
from app.services.simulation import advance

router = APIRouter(prefix="/projects", tags=["simulation"])
audit_router = APIRouter(prefix="/projects", tags=["audit"])


@router.post(
    "/{project_id}/simulate/advance",
    name="advance",
    response_model=AdvanceResult,
    responses=NOT_FOUND,
)
def advance_clock(
    request: Request,
    session: SessionDep,
    project_id: int,
    days: Annotated[int, Query(ge=1, le=90, description="Calendar days to move forward")],
    actor: ActorDep,
) -> AdvanceResult:
    """Move the project's simulated "today" forward; generate progress and one snapshot per
    working day (seeded by SIM_SEED), then recompute EVM and the risk register."""
    return advance(session, project_id, days, request.app.state.settings.sim_seed, actor)


@audit_router.get("/{project_id}/audit", name="list", response_model=AuditPage, responses=NOT_FOUND)
def list_project_audit(session: SessionDep, project_id: int, page: PageDep) -> AuditPage:
    """Every audited change to the project, its tasks, assignments, risks and proposals,
    newest first, each with a one-line human-readable `summary`."""
    items, total = list_audit(session, project_id, page)
    return AuditPage(
        items=items,
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
