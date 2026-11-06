from typing import Annotated

from fastapi import APIRouter, Query, status

from app.routers.deps import PageDep, SessionDep
from app.schemas.common import NOT_FOUND
from app.schemas.task import TaskCreate, TaskPage, TaskRead, TaskUpdate
from app.services import tasks as service

router = APIRouter(tags=["tasks"])


@router.get(
    "/projects/{project_id}/tasks", name="list", response_model=TaskPage, responses=NOT_FOUND
)
def list_tasks(
    session: SessionDep,
    project_id: int,
    page: PageDep,
    epic_id: Annotated[int | None, Query(description="Only tasks in this epic")] = None,
) -> TaskPage:
    items, total = service.list_tasks(session, project_id, page, epic_id=epic_id)
    return TaskPage(
        items=[TaskRead.model_validate(t) for t in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "/projects/{project_id}/tasks",
    name="create",
    status_code=status.HTTP_201_CREATED,
    response_model=TaskRead,
    responses=NOT_FOUND,
)
def create_task(session: SessionDep, project_id: int, body: TaskCreate) -> TaskRead:
    return TaskRead.model_validate(service.create_task(session, project_id, body))


@router.get("/tasks/{task_id}", name="get", response_model=TaskRead, responses=NOT_FOUND)
def get_task(session: SessionDep, task_id: int) -> TaskRead:
    return TaskRead.model_validate(service.get_task(session, task_id))


@router.patch("/tasks/{task_id}", name="update", response_model=TaskRead, responses=NOT_FOUND)
def update_task(session: SessionDep, task_id: int, body: TaskUpdate) -> TaskRead:
    return TaskRead.model_validate(service.update_task(session, task_id, body))


@router.delete(
    "/tasks/{task_id}", name="delete", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND
)
def delete_task(session: SessionDep, task_id: int) -> None:
    service.delete_task(session, task_id)
