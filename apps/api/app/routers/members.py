from fastapi import APIRouter, status

from app.routers.deps import PageDep, SessionDep
from app.schemas.common import CONFLICT, NOT_FOUND
from app.schemas.member import (
    AvailabilityCreate,
    MemberCreate,
    MemberPage,
    MemberRead,
    MemberSkillsReplace,
    MemberUpdate,
)
from app.services import members as service

router = APIRouter(prefix="/members", tags=["members"])


@router.get("", name="list", response_model=MemberPage)
def list_members(session: SessionDep, page: PageDep) -> MemberPage:
    items, total = service.list_members(session, page)
    return MemberPage(
        items=[service.to_read(m) for m in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    name="create",
    status_code=status.HTTP_201_CREATED,
    response_model=MemberRead,
    responses=CONFLICT,
)
def create_member(session: SessionDep, body: MemberCreate) -> MemberRead:
    return service.to_read(service.create_member(session, body))


@router.get("/{member_id}", name="get", response_model=MemberRead, responses=NOT_FOUND)
def get_member(session: SessionDep, member_id: int) -> MemberRead:
    return service.to_read(service.get_member(session, member_id))


@router.patch(
    "/{member_id}", name="update", response_model=MemberRead, responses={**NOT_FOUND, **CONFLICT}
)
def update_member(session: SessionDep, member_id: int, body: MemberUpdate) -> MemberRead:
    return service.to_read(service.update_member(session, member_id, body))


@router.delete(
    "/{member_id}",
    name="delete",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**NOT_FOUND, **CONFLICT},
)
def delete_member(session: SessionDep, member_id: int) -> None:
    """409 when the member has assignment history."""
    service.delete_member(session, member_id)


@router.put(
    "/{member_id}/skills", name="replace_skills", response_model=MemberRead, responses=NOT_FOUND
)
def replace_member_skills(
    session: SessionDep, member_id: int, body: MemberSkillsReplace
) -> MemberRead:
    return service.to_read(service.replace_skills(session, member_id, body))


@router.post(
    "/{member_id}/availability",
    name="add_availability",
    status_code=status.HTTP_201_CREATED,
    response_model=MemberRead,
    responses=NOT_FOUND,
)
def add_member_availability(
    session: SessionDep, member_id: int, body: AvailabilityCreate
) -> MemberRead:
    return service.to_read(service.add_availability(session, member_id, body))


@router.delete(
    "/{member_id}/availability/{availability_id}",
    name="delete_availability",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND,
)
def delete_member_availability(session: SessionDep, member_id: int, availability_id: int) -> None:
    service.delete_availability(session, member_id, availability_id)
