from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.models.enums import AvailabilityKind
from app.schemas.common import Page, PatchModel, ReadModel

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class MemberSkillIn(BaseModel):
    skill_id: int
    level: int = Field(ge=1, le=5)


class MemberSkillRead(BaseModel):
    skill_id: int
    skill: str = Field(description="Skill name")
    level: int


class AvailabilityCreate(BaseModel):
    """`work` needs hours_per_week; `leave` is always 0 h/week (may be omitted)."""

    kind: AvailabilityKind
    start_date: date
    end_date: date
    hours_per_week: float | None = Field(default=None, ge=0, le=80)
    note: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.kind is AvailabilityKind.LEAVE:
            if self.hours_per_week not in (None, 0):
                raise ValueError("leave must have 0 hours_per_week")
            self.hours_per_week = 0.0
        elif self.hours_per_week is None:
            raise ValueError("hours_per_week is required for work availability")
        return self


class AvailabilityRead(ReadModel):
    id: int
    kind: AvailabilityKind
    start_date: date
    end_date: date
    hours_per_week: float
    note: str | None


def _unique_skill_ids(skills: list[MemberSkillIn]) -> None:
    ids = [s.skill_id for s in skills]
    if len(ids) != len(set(ids)):
        raise ValueError("each skill_id may appear only once")


class MemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)
    skills: list[MemberSkillIn] = Field(default_factory=list)
    availability: list[AvailabilityCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Self:
        _unique_skill_ids(self.skills)
        return self


class MemberUpdate(PatchModel):
    nullable_fields = frozenset({"email"})

    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)


class MemberSkillsReplace(BaseModel):
    """Full replacement of a member's skill levels."""

    skills: list[MemberSkillIn]

    @model_validator(mode="after")
    def _check(self) -> Self:
        _unique_skill_ids(self.skills)
        return self


class MemberRead(BaseModel):
    id: int
    name: str
    role: str
    email: str | None
    skills: list[MemberSkillRead]
    availability: list[AvailabilityRead]
    created_at: datetime
    updated_at: datetime


class MemberPage(Page[MemberRead]):
    pass
