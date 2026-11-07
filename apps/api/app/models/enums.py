"""Domain enums shared by models and (later) Pydantic schemas."""

from enum import StrEnum


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class DependencyType(StrEnum):
    FS = "FS"  # finish-to-start; the only type the engines support


class AssignmentSource(StrEnum):
    AI = "ai"
    PM_OVERRIDE = "pm_override"


class AvailabilityKind(StrEnum):
    WORK = "work"
    LEAVE = "leave"


class RiskCategory(StrEnum):
    SCHEDULE = "schedule"
    RESOURCE = "resource"
    COST = "cost"
    SKILL = "skill"
    TECHNICAL = "technical"


class RiskStatus(StrEnum):
    OPEN = "open"
    MITIGATING = "mitigating"
    CLOSED = "closed"


class ReallocationStatus(StrEnum):
    PENDING = "pending"  # proposal waiting for the PM
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
