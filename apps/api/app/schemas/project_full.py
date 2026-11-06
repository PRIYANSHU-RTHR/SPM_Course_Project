from app.schemas.assignment import AssignmentRead
from app.schemas.common import ReadModel
from app.schemas.dependency import DependencyRead
from app.schemas.epic import EpicRead
from app.schemas.project import ProjectRead
from app.schemas.task import TaskRead


class ProjectFull(ReadModel):
    """Whole plan in one call. Flat lists keyed by id; `assignments` holds current ones only."""

    project: ProjectRead
    epics: list[EpicRead]
    tasks: list[TaskRead]
    dependencies: list[DependencyRead]
    assignments: list[AssignmentRead]
