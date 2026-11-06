from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import TaskStatus
from app.schemas.common import Page, PatchModel, ReadModel

Hours = float


class RequiredSkill(BaseModel):
    skill: str = Field(min_length=1, max_length=64, description="Skill name from /skills")
    level: int = Field(ge=1, le=5)
    must: bool = True

    @field_validator("skill")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return value.strip().lower()


def _check_pert_order(o: float, m: float, p: float) -> None:
    if not o <= m <= p:
        raise ValueError("estimates must satisfy optimistic <= most_likely <= pessimistic")


class TaskCreate(BaseModel):
    epic_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    optimistic_hours: Hours = Field(ge=0)
    most_likely_hours: Hours = Field(ge=0)
    pessimistic_hours: Hours = Field(ge=0)
    priority: int = Field(default=3, ge=1, le=5)
    required_skills: list[RequiredSkill] = Field(default_factory=list)

    @model_validator(mode="after")
    def _pert_order(self) -> Self:
        _check_pert_order(self.optimistic_hours, self.most_likely_hours, self.pessimistic_hours)
        return self


class TaskUpdate(PatchModel):
    """o/m/p order is re-checked against the stored values in the service."""

    nullable_fields = frozenset({"description"})

    epic_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    optimistic_hours: Hours | None = Field(default=None, ge=0)
    most_likely_hours: Hours | None = Field(default=None, ge=0)
    pessimistic_hours: Hours | None = Field(default=None, ge=0)
    priority: int | None = Field(default=None, ge=1, le=5)
    status: TaskStatus | None = None
    required_skills: list[RequiredSkill] | None = None
    percent_complete: float | None = Field(default=None, ge=0, le=100)
    actual_hours: Hours | None = Field(default=None, ge=0)


class TaskRead(ReadModel):
    id: int
    project_id: int
    epic_id: int
    title: str
    description: str | None
    optimistic_hours: Hours
    most_likely_hours: Hours
    pessimistic_hours: Hours
    priority: int
    status: TaskStatus
    required_skills: list[RequiredSkill]
    percent_complete: float
    actual_hours: Hours
    created_at: datetime
    updated_at: datetime


class TaskPage(Page[TaskRead]):
    pass
