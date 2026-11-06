from fastapi import APIRouter, status

from app.routers.deps import PageDep, SessionDep
from app.schemas.common import NOT_FOUND
from app.schemas.project import ProjectCreate, ProjectPage, ProjectRead, ProjectUpdate
from app.schemas.project_full import ProjectFull
from app.services import projects as service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", name="list", response_model=ProjectPage)
def list_projects(session: SessionDep, page: PageDep) -> ProjectPage:
    items, total = service.list_projects(session, page)
    return ProjectPage(
        items=[ProjectRead.model_validate(p) for p in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("", name="create", status_code=status.HTTP_201_CREATED, response_model=ProjectRead)
def create_project(session: SessionDep, body: ProjectCreate) -> ProjectRead:
    return ProjectRead.model_validate(service.create_project(session, body))


@router.get("/{project_id}", name="get", response_model=ProjectRead, responses=NOT_FOUND)
def get_project(session: SessionDep, project_id: int) -> ProjectRead:
    return ProjectRead.model_validate(service.get_project(session, project_id))


@router.get("/{project_id}/full", name="get_full", response_model=ProjectFull, responses=NOT_FOUND)
def get_project_full(session: SessionDep, project_id: int) -> ProjectFull:
    """Project + epics + tasks + dependencies + current assignments in one call."""
    return ProjectFull.model_validate(service.get_project_graph(session, project_id))


@router.patch("/{project_id}", name="update", response_model=ProjectRead, responses=NOT_FOUND)
def update_project(session: SessionDep, project_id: int, body: ProjectUpdate) -> ProjectRead:
    return ProjectRead.model_validate(service.update_project(session, project_id, body))


@router.delete(
    "/{project_id}", name="delete", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND
)
def delete_project(session: SessionDep, project_id: int) -> None:
    service.delete_project(session, project_id)
