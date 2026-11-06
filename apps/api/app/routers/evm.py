from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.evm import ProjectEvm
from app.services.evm import project_evm

router = APIRouter(prefix="/projects", tags=["evm"])


@router.get("/{project_id}/evm", response_model=ProjectEvm)
def get_evm(
    project_id: int,
    session: Annotated[Session, Depends(get_session)],
    as_of: Annotated[date | None, Query(description="Status date (default: today, UTC)")] = None,
) -> ProjectEvm:
    return project_evm(session, project_id, as_of or datetime.now(UTC).date())
