from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import Page, PatchModel, ReadModel


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, description="Stored lowercase, e.g. `react`")

    @field_validator("name")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return value.strip().lower()


class SkillUpdate(PatchModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def _normalise(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None


class SkillRead(ReadModel):
    id: int
    name: str
    created_at: datetime


class SkillPage(Page[SkillRead]):
    pass
