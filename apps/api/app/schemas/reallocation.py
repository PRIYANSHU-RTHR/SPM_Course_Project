"""Disruptions, reallocation proposals, the reallocation workflow state and the audit log."""

from datetime import date, datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import ReallocationStatus
from app.schemas.common import Page, ReadModel
from app.schemas.risk import RiskRefreshResult
from app.schemas.task import TaskCreate
from app.schemas.workflow import WorkflowStatus

# -- disruptions ------------------------------------------------------------------------------


class _DisruptionBase(BaseModel):
    actor: str = Field(default="pm", min_length=1, max_length=120)
    reason: str | None = Field(default=None, max_length=2000)


class LeaveDisruption(_DisruptionBase):
    """A member is unavailable for an inclusive date range."""

    type: Literal["leave"]
    member_id: int
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _range_order(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class SlipDisruption(_DisruptionBase):
    """A task needs more effort than estimated: o, m and p all grow by `extra_hours`."""

    type: Literal["slip"]
    task_id: int
    extra_hours: float = Field(gt=0, le=200)


class ScopeAddDisruption(_DisruptionBase):
    """New work enters the project mid-flight."""

    type: Literal["scope_add"]
    task: TaskCreate
    predecessors: list[int] = Field(default_factory=list, description="Task ids in this project")


Disruption = Annotated[
    LeaveDisruption | SlipDisruption | ScopeAddDisruption, Field(discriminator="type")
]


class DisruptionStarted(BaseModel):
    thread_id: str
    project_id: int


# -- proposal (the pm_approval interrupt value) -----------------------------------------------

AffectReason = Literal["owner_unavailable", "critical_slip", "new_scope"]


class OwnerRef(BaseModel):
    member_id: int | None
    name: str | None


class ProposalItem(BaseModel):
    task_id: int
    title: str
    reasons: list[AffectReason]
    before: OwnerRef
    after: OwnerRef
    changed: bool = Field(description="False = keep the current owner (nobody better/eligible)")
    before_eligible: bool
    before_ineligible_reason: str | None
    score_before: float | None = Field(description="Assignment score of the current owner now")
    score_after: float | None
    finish_before: date | None = Field(description="Planned finish with current owners")
    finish_after: date | None = Field(description="Planned finish if the proposal is approved")


class ScenarioMetrics(BaseModel):
    """Engine output for one what-if. Dates are on the project's working calendar."""

    p_on_time: float | None = Field(
        description="Resource-adjusted Monte Carlo P(finish <= deadline)"
    )
    p50: date | None
    p80: date | None
    p80_hours: float | None
    finish: date = Field(description="Resource-constrained schedule finish (remaining work)")
    resource_shift_hours: float = Field(
        description="Resource-constrained finish minus the unconstrained network finish (h); "
        "added to every Monte Carlo run"
    )


class RiskRef(BaseModel):
    risk_id: int | None = Field(description="Register row, if the risk is in the register")
    rule_key: str
    subject_ref: str
    title: str
    score: int


class ProposalPayload(BaseModel):
    reallocation_id: int
    thread_id: str
    project_id: int
    as_of: date
    disruption: dict[str, Any]
    summary: str = Field(description="Template sentence from the numbers below (no LLM)")
    before_disruption: ScenarioMetrics
    now: ScenarioMetrics = Field(description="Disruption applied, current owners")
    if_approved: ScenarioMetrics = Field(description="Disruption applied, proposed owners")
    items: list[ProposalItem]
    risks_that_would_close: list[RiskRef]
    risks_that_would_open: list[RiskRef]


class ReallocationRead(ReadModel):
    id: int
    project_id: int
    thread_id: str
    disruption: dict[str, Any]
    payload: ProposalPayload | None
    status: ReallocationStatus
    decided_by: str | None
    reason: str | None
    created_at: datetime
    decided_at: datetime | None

    @field_validator("payload", mode="before")
    @classmethod
    def _empty_is_none(cls, value: Any) -> Any:
        return value or None


class ReallocationPage(Page[ReallocationRead]):
    pass


class ReallocationState(BaseModel):
    """GET /workflows/{thread_id}/state for a reallocation run."""

    kind: Literal["reallocate"] = "reallocate"
    thread_id: str
    status: WorkflowStatus
    node: str | None
    project_id: int
    reallocation_id: int | None
    proposal: ProposalPayload | None = Field(description="Set while waiting for the PM")
    outcome: ScenarioMetrics | None = Field(description="Recomputed after an approval")
    applied: list[int] = Field(description="Assignment ids written on approval")
    reason: str | None
    error: str | None


# -- simulation clock and audit log -----------------------------------------------------------


class AdvanceResult(BaseModel):
    project_id: int
    from_date: date
    to_date: date
    working_days: int
    snapshots: int = Field(description="Snapshot rows written (one per working day)")
    spi: float | None
    cpi: float | None
    p_on_time: float | None
    risks: RiskRefreshResult


class AuditRead(ReadModel):
    id: int
    actor: str
    action: str
    entity: str
    entity_id: int
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    created_at: datetime


class AuditPage(Page[AuditRead]):
    pass
