"""Schemas for POST /projects/{id}/assignments/recommend and /apply."""

from datetime import date
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import AssignmentSource

Mode = Literal["greedy", "optimal"]


class _FromEngine(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SkillMatchOut(_FromEngine):
    skill: str
    required: int
    has: int
    weight: float
    fit: float


class ScoreOut(_FromEngine):
    total: float = Field(description="0-100")
    skill_fit: float
    capacity_fit: float
    balance: float
    skill_part: float = Field(description="Points from skill_fit (weights x 100)")
    capacity_part: float
    balance_part: float
    free_hours: float
    utilisation: float | None = Field(description="null = member has work but zero capacity")
    skills: list[SkillMatchOut]

    @model_validator(mode="before")
    @classmethod
    def _inf_to_none(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            data = {k: getattr(data, k) for k in cls.model_fields}
        if data["utilisation"] == float("inf"):
            data = {**data, "utilisation": None}
        return data


class CandidateOut(_FromEngine):
    member_id: int
    score: ScoreOut


class Ineligible(BaseModel):
    member_id: int
    reason: str


class RecommendationOut(BaseModel):
    task_id: int
    window_start: date
    window_end: date
    member_id: int | None
    score: ScoreOut | None
    candidates: list[CandidateOut] = Field(description="Top 3 eligible, best first")
    ineligible: list[Ineligible]


class Comparison(_FromEngine):
    greedy_total: float
    optimal_total: float
    greedy_utilisation_std: float
    optimal_utilisation_std: float
    greedy_unassigned: int
    optimal_unassigned: int


class RecommendResponse(BaseModel):
    project_id: int
    mode: Mode
    total_score: float
    utilisation_std: float
    unassigned: int
    utilisation: dict[int, float | None]
    recommendations: list[RecommendationOut]
    comparison: Comparison


class ApplyItem(BaseModel):
    task_id: int
    member_id: int
    source: AssignmentSource = AssignmentSource.AI
    reason: str | None = None
    score_breakdown: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _override_needs_reason(self) -> Self:
        if self.source == AssignmentSource.PM_OVERRIDE and not (self.reason or "").strip():
            raise ValueError("a pm_override needs a reason")
        return self


class ApplyRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    items: list[ApplyItem] = Field(min_length=1)


class AppliedAssignment(BaseModel):
    assignment_id: int
    task_id: int
    member_id: int
    previous_member_id: int | None
    source: AssignmentSource
