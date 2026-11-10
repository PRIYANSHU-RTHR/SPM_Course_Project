"""Shared router dependencies."""

from typing import Annotated

from fastapi import Depends, Header, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.common import DEFAULT_ACTOR
from app.services.common import PageParams

SessionDep = Annotated[Session, Depends(get_session)]


def page_params(
    limit: Annotated[int, Query(ge=1, le=200, description="Page size")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


PageDep = Annotated[PageParams, Depends(page_params)]


def actor_header(
    x_actor: Annotated[
        str,
        Header(
            alias="X-Actor",
            min_length=1,
            max_length=120,
            description="Who is acting; recorded as `audit_log.actor`",
        ),
    ] = DEFAULT_ACTOR,
) -> str:
    return x_actor.strip() or DEFAULT_ACTOR


ActorDep = Annotated[str, Depends(actor_header)]
