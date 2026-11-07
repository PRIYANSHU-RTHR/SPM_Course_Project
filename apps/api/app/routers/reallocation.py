"""Disruptions start a reallocation run; proposals are what the PM approves or rejects."""

from typing import Annotated

from fastapi import APIRouter, Body, Query
from sqlalchemy import select

from app.models import Reallocation, ReallocationStatus
from app.routers.deps import PageDep, SessionDep
from app.routers.workflows import WorkflowsDep
from app.schemas.common import CONFLICT, NOT_FOUND
from app.schemas.reallocation import (
    Disruption,
    DisruptionStarted,
    ReallocationPage,
    ReallocationRead,
)
from app.services.common import paginate
from app.services.inputs import get_project

router = APIRouter(prefix="/projects", tags=["reallocation"])


@router.post(
    "/{project_id}/disruptions",
    name="create_disruption",
    status_code=202,
    response_model=DisruptionStarted,
    responses={**NOT_FOUND, **CONFLICT},
)
def create_disruption(
    project_id: int, disruption: Annotated[Disruption, Body()], workflows: WorkflowsDep
) -> DisruptionStarted:
    """Record the disruption (leave, slip, new scope) and start the reallocation run. Its
    proposal appears under `/proposals?status=pending`; decide with `/workflows/{id}/resume`."""
    thread_id = workflows.reallocate.start(project_id, disruption)
    return DisruptionStarted(thread_id=thread_id, project_id=project_id)


@router.get(
    "/{project_id}/proposals",
    name="list_proposals",
    response_model=ReallocationPage,
    responses=NOT_FOUND,
)
def list_proposals(
    session: SessionDep,
    project_id: int,
    page: PageDep,
    status: Annotated[ReallocationStatus | None, Query(description="Filter by status")] = None,
) -> ReallocationPage:
    """Reallocation proposals, newest first."""
    get_project(session, project_id)
    stmt = select(Reallocation).where(Reallocation.project_id == project_id)
    if status is not None:
        stmt = stmt.where(Reallocation.status == status)
    items, total = paginate(session, stmt.order_by(Reallocation.id.desc()), page)
    return ReallocationPage(
        items=[ReallocationRead.model_validate(r) for r in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
