"""A project's audit trail. `audit_log` has no project column, so rows are matched through
the entity they describe (project, task, assignment, risk, reallocation)."""

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import Assignment, AuditLog, Reallocation, Risk, Task
from app.services.common import PageParams, paginate
from app.services.inputs import get_project


def list_audit(session: Session, project_id: int, page: PageParams) -> tuple[list[AuditLog], int]:
    get_project(session, project_id)
    task_ids = select(Task.id).where(Task.project_id == project_id)
    by_entity = {
        "task": task_ids,
        "assignment": select(Assignment.id).where(Assignment.task_id.in_(task_ids)),
        "risk": select(Risk.id).where(Risk.project_id == project_id),
        "reallocation": select(Reallocation.id).where(Reallocation.project_id == project_id),
    }
    belongs = or_(
        and_(AuditLog.entity == "project", AuditLog.entity_id == project_id),
        *(
            and_(AuditLog.entity == entity, AuditLog.entity_id.in_(ids))
            for entity, ids in by_entity.items()
        ),
    )
    stmt = select(AuditLog).where(belongs).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    return paginate(session, stmt, page)
