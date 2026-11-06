from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field

from app.models.enums import RiskCategory, RiskStatus
from app.schemas.common import Page, ReadModel


class RiskRead(ReadModel):
    id: int
    project_id: int
    rule_key: str
    subject_ref: str = Field(description='"project", "task:<id>" or "member:<id>"')
    title: str
    description: str | None
    category: RiskCategory
    probability: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    status: RiskStatus
    evidence: dict[str, Any] = Field(description="Numbers that made the rule fire")
    rmmm: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> int:
        """Probability x impact, 1-25."""
        return self.probability * self.impact


class RiskPage(Page[RiskRead]):
    pass


class RiskRefreshResult(BaseModel):
    as_of: date
    opened: list[int] = Field(description="Risk ids raised for the first time")
    reopened: list[int] = Field(description="Closed risks whose rule fires again")
    updated: list[int] = Field(
        description="Still-firing risks whose P, I, title or evidence changed"
    )
    closed: list[int] = Field(description="Risks whose rule no longer fires")
    open_total: int = Field(description="Risks not closed after the refresh")
