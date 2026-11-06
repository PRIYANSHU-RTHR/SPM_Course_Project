from fastapi import APIRouter, status

from app.routers.deps import PageDep, SessionDep
from app.schemas.common import CONFLICT, NOT_FOUND
from app.schemas.dependency import DependencyCreate, DependencyPage, DependencyRead
from app.services import dependencies as service

router = APIRouter(tags=["dependencies"])


@router.get(
    "/projects/{project_id}/dependencies",
    name="list",
    response_model=DependencyPage,
    responses=NOT_FOUND,
)
def list_dependencies(session: SessionDep, project_id: int, page: PageDep) -> DependencyPage:
    items, total = service.list_dependencies(session, project_id, page)
    return DependencyPage(
        items=[DependencyRead.model_validate(d) for d in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "/projects/{project_id}/dependencies",
    name="create",
    status_code=status.HTTP_201_CREATED,
    response_model=DependencyRead,
    responses={**NOT_FOUND, **CONFLICT},
)
def create_dependency(
    session: SessionDep, project_id: int, body: DependencyCreate
) -> DependencyRead:
    """409 if it duplicates an edge or would close a cycle (`details.cycle` holds the task ids)."""
    return DependencyRead.model_validate(service.create_dependency(session, project_id, body))


@router.delete(
    "/dependencies/{dependency_id}",
    name="delete",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND,
)
def delete_dependency(session: SessionDep, dependency_id: int) -> None:
    service.delete_dependency(session, dependency_id)
