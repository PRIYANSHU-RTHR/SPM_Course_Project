from collections import defaultdict

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.errors import ConflictError, ValidationFailedError
from app.models import Dependency, Task
from app.schemas.dependency import DependencyCreate
from app.services.common import PageParams, commit, get_or_404, paginate
from app.services.projects import get_project
from app.services.tasks import get_task


def _project_dependencies(project_id: int) -> Select[tuple[Dependency]]:
    task_ids = select(Task.id).where(Task.project_id == project_id)
    return select(Dependency).where(Dependency.pred_task_id.in_(task_ids)).order_by(Dependency.id)


def list_dependencies(
    session: Session, project_id: int, page: PageParams
) -> tuple[list[Dependency], int]:
    get_project(session, project_id)
    return paginate(session, _project_dependencies(project_id), page)


def find_path(edges: dict[int, list[int]], start: int, goal: int) -> list[int] | None:
    """Iterative DFS over pred -> succ edges; returns the node path start..goal or None.

    TODO(step 07): replace with the CPM engine's cycle detection (Kahn topo sort) once it lands.
    """
    stack: list[tuple[int, list[int]]] = [(start, [start])]
    seen: set[int] = set()
    while stack:
        node, path = stack.pop()
        if node == goal:
            return path
        if node in seen:
            continue
        seen.add(node)
        for nxt in reversed(edges.get(node, [])):
            if nxt not in seen:
                stack.append((nxt, [*path, nxt]))
    return None


def create_dependency(session: Session, project_id: int, data: DependencyCreate) -> Dependency:
    get_project(session, project_id)
    for task_id in (data.pred_task_id, data.succ_task_id):
        if get_task(session, task_id).project_id != project_id:
            raise ValidationFailedError(
                f"Task {task_id} belongs to another project",
                details={"task_id": task_id, "project_id": project_id},
            )

    edges: dict[int, list[int]] = defaultdict(list)
    for dep in session.scalars(_project_dependencies(project_id)):
        if (dep.pred_task_id, dep.succ_task_id) == (data.pred_task_id, data.succ_task_id):
            raise ConflictError("This dependency already exists", details={"dependency_id": dep.id})
        edges[dep.pred_task_id].append(dep.succ_task_id)

    # Adding pred -> succ closes a cycle iff succ already reaches pred.
    path = find_path(edges, data.succ_task_id, data.pred_task_id)
    if path is not None:
        cycle = [data.pred_task_id, *path]
        raise ConflictError(
            "Dependency would create a cycle: " + " -> ".join(f"T-{t}" for t in cycle),
            details={"cycle": cycle},
        )

    dependency = Dependency(pred_task_id=data.pred_task_id, succ_task_id=data.succ_task_id)
    session.add(dependency)
    commit(session)
    return dependency


def delete_dependency(session: Session, dependency_id: int) -> None:
    session.delete(get_or_404(session, Dependency, dependency_id, "Dependency"))
    commit(session)
