"""SQLAlchemy models. Importing this package registers every table on `Base.metadata`."""

from app.models.assignment import Assignment
from app.models.base import Base
from app.models.enums import (
    AssignmentSource,
    AvailabilityKind,
    DependencyType,
    RiskCategory,
    RiskStatus,
    TaskStatus,
)
from app.models.project import Dependency, Epic, Project, Task
from app.models.risk import Risk
from app.models.team import Availability, Member, MemberSkill, Skill
from app.models.tracking import AuditLog, Snapshot

__all__ = [
    "Assignment",
    "AssignmentSource",
    "AuditLog",
    "Availability",
    "AvailabilityKind",
    "Base",
    "Dependency",
    "DependencyType",
    "Epic",
    "Member",
    "MemberSkill",
    "Project",
    "Risk",
    "RiskCategory",
    "RiskStatus",
    "Skill",
    "Snapshot",
    "Task",
    "TaskStatus",
]
