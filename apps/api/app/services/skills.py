from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ConflictError
from app.models import Skill, Task
from app.schemas.skill import SkillCreate, SkillUpdate
from app.services.common import PageParams, apply_changes, commit, get_or_404, paginate


def get_skill(session: Session, skill_id: int) -> Skill:
    return get_or_404(session, Skill, skill_id, "Skill")


def list_skills(session: Session, page: PageParams) -> tuple[list[Skill], int]:
    return paginate(session, select(Skill).order_by(Skill.name), page)


def create_skill(session: Session, data: SkillCreate) -> Skill:
    skill = Skill(name=data.name)
    session.add(skill)
    commit(session)
    return skill


def _ensure_unused_by_tasks(session: Session, skill: Skill, action: str) -> None:
    """Tasks reference skills by name (JSONB), so renames/deletes would leave dangling names."""
    used_by = list(
        session.scalars(
            select(Task.id)
            .where(Task.required_skills.contains([{"skill": skill.name}]))
            .order_by(Task.id)
        )
    )
    if used_by:
        raise ConflictError(
            f"Cannot {action} skill '{skill.name}': required by {len(used_by)} task(s)",
            details={"task_ids": used_by},
        )


def update_skill(session: Session, skill_id: int, data: SkillUpdate) -> Skill:
    skill = get_skill(session, skill_id)
    changes = data.changes()
    if changes.get("name", skill.name) != skill.name:
        _ensure_unused_by_tasks(session, skill, "rename")
    apply_changes(skill, changes)
    commit(session)
    return skill


def delete_skill(session: Session, skill_id: int) -> None:
    skill = get_skill(session, skill_id)
    _ensure_unused_by_tasks(session, skill, "delete")
    session.delete(skill)
    commit(session)
