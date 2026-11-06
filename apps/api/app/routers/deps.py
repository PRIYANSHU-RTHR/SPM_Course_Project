"""Shared router dependencies."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.services.common import PageParams

SessionDep = Annotated[Session, Depends(get_session)]


def page_params(
    limit: Annotated[int, Query(ge=1, le=200, description="Page size")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


PageDep = Annotated[PageParams, Depends(page_params)]
