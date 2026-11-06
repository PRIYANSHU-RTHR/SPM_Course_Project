from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import Page, PatchModel, ReadModel

Money = Decimal  # INR, 2 dp; serialised as a string in JSON to stay exact.


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brief: str | None = None
    start_date: date
    deadline: date
    budget: Money = Field(ge=0, max_digits=14, decimal_places=2)
    hourly_rate: Money = Field(ge=0, max_digits=10, decimal_places=2)

    @model_validator(mode="after")
    def _deadline_after_start(self) -> Self:
        if self.deadline < self.start_date:
            raise ValueError("deadline must be on or after start_date")
        return self


class ProjectUpdate(PatchModel):
    nullable_fields = frozenset({"brief"})

    name: str | None = Field(default=None, min_length=1, max_length=200)
    brief: str | None = None
    start_date: date | None = None
    deadline: date | None = None
    budget: Money | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    hourly_rate: Money | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class ProjectRead(ReadModel):
    id: int
    name: str
    brief: str | None
    start_date: date
    deadline: date
    budget: Money
    hourly_rate: Money
    created_at: datetime
    updated_at: datetime


class ProjectPage(Page[ProjectRead]):
    pass
