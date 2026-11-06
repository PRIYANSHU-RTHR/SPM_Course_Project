from fastapi import APIRouter, status

from app.routers.deps import PageDep, SessionDep
from app.schemas.common import CONFLICT, NOT_FOUND
from app.schemas.skill import SkillCreate, SkillPage, SkillRead, SkillUpdate
from app.services import skills as service

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", name="list", response_model=SkillPage)
def list_skills(session: SessionDep, page: PageDep) -> SkillPage:
    items, total = service.list_skills(session, page)
    return SkillPage(
        items=[SkillRead.model_validate(s) for s in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    name="create",
    status_code=status.HTTP_201_CREATED,
    response_model=SkillRead,
    responses=CONFLICT,
)
def create_skill(session: SessionDep, body: SkillCreate) -> SkillRead:
    return SkillRead.model_validate(service.create_skill(session, body))


@router.get("/{skill_id}", name="get", response_model=SkillRead, responses=NOT_FOUND)
def get_skill(session: SessionDep, skill_id: int) -> SkillRead:
    return SkillRead.model_validate(service.get_skill(session, skill_id))


@router.patch(
    "/{skill_id}", name="update", response_model=SkillRead, responses={**NOT_FOUND, **CONFLICT}
)
def update_skill(session: SessionDep, skill_id: int, body: SkillUpdate) -> SkillRead:
    """409 when renaming a skill that tasks still require by name."""
    return SkillRead.model_validate(service.update_skill(session, skill_id, body))


@router.delete(
    "/{skill_id}",
    name="delete",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**NOT_FOUND, **CONFLICT},
)
def delete_skill(session: SessionDep, skill_id: int) -> None:
    """409 when tasks still require the skill."""
    service.delete_skill(session, skill_id)
