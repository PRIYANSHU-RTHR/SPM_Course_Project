"""Helpers shared by services: lookup-or-404, pagination, PATCH application, safe commit."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.interfaces import ORMOption

from app.errors import ConflictError, NotFoundError, ValidationFailedError
from app.models import Base

# Friendly messages for constraint names (stable thanks to the naming convention in models/base.py).
_CONSTRAINT_MESSAGES = {
    "uq_skill_name": "A skill with this name already exists",
    "uq_member_email": "A member with this email already exists",
    "uq_member_skill_member_id_skill_id": "The member already has this skill",
    "uq_dependency_pred_task_id_succ_task_id": "This dependency already exists",
    "fk_assignment_member_id_member": "The member has assignment history and cannot be deleted",
}


@dataclass(frozen=True)
class PageParams:
    limit: int = 50
    offset: int = 0


def get_or_404[M: Base](session: Session, model: type[M], obj_id: int, label: str) -> M:
    obj = session.get(model, obj_id)
    if obj is None:
        raise NotFoundError(f"{label} {obj_id} not found", details={"id": obj_id})
    return obj


def paginate[M: Base](
    session: Session,
    stmt: Select[tuple[M]],
    page: PageParams,
    options: Sequence[ORMOption] = (),
) -> tuple[list[M], int]:
    total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = session.scalars(stmt.options(*options).limit(page.limit).offset(page.offset)).all()
    return list(rows), total


def apply_changes(obj: Base, changes: dict[str, Any]) -> None:
    for name, value in changes.items():
        setattr(obj, name, value)


def commit(session: Session) -> None:
    """Commit, turning constraint violations into domain errors (409 / 422)."""
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        diag = getattr(exc.orig, "diag", None)
        constraint = getattr(diag, "constraint_name", None) or "unknown"
        message = _CONSTRAINT_MESSAGES.get(constraint, f"Constraint {constraint} violated")
        details = {"constraint": constraint}
        if constraint.startswith("ck_"):
            raise ValidationFailedError(message, details=details) from exc
        raise ConflictError(message, details=details) from exc
