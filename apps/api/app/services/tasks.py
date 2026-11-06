from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ValidationFailedError
from app.models import Skill, Task
from app.schemas.task import RequiredSkill, TaskCreate, TaskUpdate
from app.services.common import PageParams, apply_changes, commit, get_or_404, paginate
from app.services.epics import get_epic
from app.services.projects import get_project


def get_task(session: Session, task_id: int) -> Task:
    return get_or_404(session, Task, task_id, "Task")


def list_tasks(
    session: Session, project_id: int, page: PageParams, epic_id: int | None = None
) -> tuple[list[Task], int]:
    get_project(session, project_id)
    stmt = select(Task).where(Task.project_id == project_id).order_by(Task.id)
    if epic_id is not None:
        stmt = stmt.where(Task.epic_id == epic_id)
    return paginate(session, stmt, page)


def _check_epic_in_project(session: Session, epic_id: int, project_id: int) -> None:
    epic = get_epic(session, epic_id)
    if epic.project_id != project_id:
        raise ValidationFailedError(
            f"Epic {epic_id} belongs to another project",
            details={"epic_id": epic_id, "project_id": project_id},
        )


def _check_skills_exist(session: Session, skills: list[RequiredSkill]) -> None:
    names = {s.skill for s in skills}
    if not names:
        return
    known = set(session.scalars(select(Skill.name).where(Skill.name.in_(names))))
    unknown = sorted(names - known)
    if unknown:
        raise ValidationFailedError(
            "Unknown skills in required_skills", details={"unknown_skills": unknown}
        )


def create_task(session: Session, project_id: int, data: TaskCreate) -> Task:
    get_project(session, project_id)
    _check_epic_in_project(session, data.epic_id, project_id)
    _check_skills_exist(session, data.required_skills)
    task = Task(project_id=project_id, **data.model_dump())
    session.add(task)
    commit(session)
    return task


def update_task(session: Session, task_id: int, data: TaskUpdate) -> Task:
    task = get_task(session, task_id)
    if data.epic_id is not None:
        _check_epic_in_project(session, data.epic_id, task.project_id)
    if data.required_skills is not None:
        _check_skills_exist(session, data.required_skills)

    apply_changes(task, data.changes())
    if not task.optimistic_hours <= task.most_likely_hours <= task.pessimistic_hours:
        session.rollback()
        raise ValidationFailedError(
            "estimates must satisfy optimistic <= most_likely <= pessimistic",
            details={
                "optimistic_hours": task.optimistic_hours,
                "most_likely_hours": task.most_likely_hours,
                "pessimistic_hours": task.pessimistic_hours,
            },
        )
    commit(session)
    return task


def delete_task(session: Session, task_id: int) -> None:
    """Deletes the task plus (by FK cascade) its dependencies and assignments."""
    session.delete(get_task(session, task_id))
    commit(session)
