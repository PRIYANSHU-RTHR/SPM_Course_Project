from fastapi import APIRouter, status

from app.routers.deps import PageDep, SessionDep
from app.schemas.common import NOT_FOUND
from app.schemas.epic import EpicCreate, EpicPage, EpicRead, EpicUpdate
from app.services import epics as service

router = APIRouter(tags=["epics"])


@router.get(
    "/projects/{project_id}/epics", name="list", response_model=EpicPage, responses=NOT_FOUND
)
def list_epics(session: SessionDep, project_id: int, page: PageDep) -> EpicPage:
    items, total = service.list_epics(session, project_id, page)
    return EpicPage(
        items=[EpicRead.model_validate(e) for e in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "/projects/{project_id}/epics",
    name="create",
    status_code=status.HTTP_201_CREATED,
    response_model=EpicRead,
    responses=NOT_FOUND,
)
def create_epic(session: SessionDep, project_id: int, body: EpicCreate) -> EpicRead:
    return EpicRead.model_validate(service.create_epic(session, project_id, body))


@router.get("/epics/{epic_id}", name="get", response_model=EpicRead, responses=NOT_FOUND)
def get_epic(session: SessionDep, epic_id: int) -> EpicRead:
    return EpicRead.model_validate(service.get_epic(session, epic_id))


@router.patch("/epics/{epic_id}", name="update", response_model=EpicRead, responses=NOT_FOUND)
def update_epic(session: SessionDep, epic_id: int, body: EpicUpdate) -> EpicRead:
    return EpicRead.model_validate(service.update_epic(session, epic_id, body))


@router.delete(
    "/epics/{epic_id}", name="delete", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND
)
def delete_epic(session: SessionDep, epic_id: int) -> None:
    service.delete_epic(session, epic_id)
