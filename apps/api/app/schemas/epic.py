from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import Page, PatchModel, ReadModel


class EpicCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    position: int = Field(default=0, ge=0)


class EpicUpdate(PatchModel):
    nullable_fields = frozenset({"description"})

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    position: int | None = Field(default=None, ge=0)


class EpicRead(ReadModel):
    id: int
    project_id: int
    title: str
    description: str | None
    position: int
    created_at: datetime
    updated_at: datetime


class EpicPage(Page[EpicRead]):
    pass
