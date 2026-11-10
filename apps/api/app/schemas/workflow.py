"""Planning workflow API: start request, PM review payload, resume decisions, state, events."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.agents.planning import SkillReq, WBSPlan
from app.schemas.assignment import ScoreOut
from app.schemas.common import DEFAULT_ACTOR, Actor
from app.schemas.estimate import Cocomo

DEFAULT_HOURLY_RATE = Decimal("850.00")

WorkflowStatus = Literal["running", "waiting", "committed", "rejected", "failed"]
TERMINAL_STATUSES: frozenset[str] = frozenset({"committed", "rejected", "failed"})

# -- start ------------------------------------------------------------------------------------


class PlanStart(BaseModel):
    brief: str = Field(min_length=20, max_length=20_000, description="Project brief in prose")
    project_name: str = Field(min_length=1, max_length=200)
    deadline: date
    budget: Decimal = Field(ge=0, max_digits=14, decimal_places=2, description="INR")
    start_date: date | None = Field(default=None, description="Default: the next working day (UTC)")
    hourly_rate: Decimal = Field(
        default=DEFAULT_HOURLY_RATE, ge=0, max_digits=10, decimal_places=2, description="INR"
    )

    @model_validator(mode="after")
    def _deadline_after_start(self) -> Self:
        if self.start_date is not None and self.deadline <= self.start_date:
            raise ValueError("deadline must be after start_date")
        return self


class PlanStarted(BaseModel):
    thread_id: str


# -- PM review payload (the interrupt value) --------------------------------------------------


class TaskEstimate(BaseModel):
    task_id: str
    te_hours: float = Field(description="(o + 4m + p) / 6")
    std_hours: float = Field(description="(p - o) / 6")


class PlanEstimates(BaseModel):
    total_te_hours: float = Field(description="Sum of task te (effort, not duration)")
    total_std_hours: float = Field(description="sqrt of summed task variances")
    total_effort_pm: float = Field(description="total_te_hours / 152")
    estimated_cost: Decimal = Field(description="total_te_hours x hourly_rate, INR")
    budget: Decimal
    cocomo: Cocomo | None
    tasks: list[TaskEstimate]


class ScheduledWbsTask(BaseModel):
    task_id: str
    start: date
    end: date
    total_slack_hours: float
    critical: bool


class PlanSchedule(BaseModel):
    start: date
    finish: date = Field(description="Unassigned plan on the project calendar")
    deadline: date
    duration_hours: float = Field(description="CPM project duration")
    meets_deadline: bool
    critical_path: list[str]
    tasks: list[ScheduledWbsTask]


class CandidateBrief(BaseModel):
    member_id: int
    name: str
    total: float


class PlanRecommendation(BaseModel):
    task_id: str
    member_id: int | None = Field(description="null = nobody eligible")
    member_name: str | None
    score: ScoreOut | None
    candidates: list[CandidateBrief] = Field(description="Top 3 eligible, best first")
    ineligible_count: int


class PlanRecommendations(BaseModel):
    mode: Literal["optimal"] = "optimal"
    total_score: float
    utilisation_std: float
    unassigned: int
    finish_with_owners: date | None = Field(
        description="Resource-constrained finish with the recommended owners"
    )
    items: list[PlanRecommendation]


class PlanReview(BaseModel):
    """What the PM sees at the review interrupt."""

    thread_id: str
    revision: int = Field(description="0 = first draft; +1 per applied edit")
    project_name: str
    wbs: WBSPlan
    warnings: list[str]
    estimates: PlanEstimates
    schedule: PlanSchedule
    recommendations: PlanRecommendations


# -- resume -----------------------------------------------------------------------------------


class TaskChange(BaseModel):
    """`update` sets only the fields given; `remove` deletes the task and links to it."""

    op: Literal["update", "remove"]
    task_id: str = Field(description="WBS id, e.g. T-004")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    o: float | None = None
    m: float | None = None
    p: float | None = None
    required_skills: list[SkillReq] | None = None
    predecessors: list[str] | None = None


class _Decision(BaseModel):
    actor: Actor = DEFAULT_ACTOR


class ApproveDecision(_Decision):
    action: Literal["approve"]
    reason: str | None = Field(default=None, max_length=2000)


class EditDecision(_Decision):
    action: Literal["edit"]
    changes: list[TaskChange] = Field(min_length=1)


class RejectDecision(_Decision):
    action: Literal["reject"]
    reason: str = Field(min_length=1, max_length=2000)


PlanDecision = Annotated[
    ApproveDecision | EditDecision | RejectDecision, Field(discriminator="action")
]


class ResumeAccepted(BaseModel):
    thread_id: str
    status: WorkflowStatus


# -- state and events -------------------------------------------------------------------------


class WorkflowState(BaseModel):
    kind: Literal["plan"] = "plan"
    thread_id: str
    status: WorkflowStatus
    node: str | None = Field(description="Running: node in progress. Waiting: pm_review")
    revision: int
    review: PlanReview | None = Field(description="Set while waiting for the PM")
    project_id: int | None = Field(description="Set once committed")
    reason: str | None = Field(description="Rejection reason")
    error: str | None = Field(description="Why the run failed")


class WorkflowEvent(BaseModel):
    """One SSE message. `node` events time each graph node; `run` events change the status."""

    seq: int
    thread_id: str
    type: Literal["node", "run"]
    node: str | None = None
    phase: Literal["start", "end"] | None = None
    status: WorkflowStatus | None = None
    duration_ms: float | None = None
    summary: str = ""
