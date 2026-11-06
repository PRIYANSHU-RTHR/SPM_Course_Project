"""Response schema for GET /projects/{id}/estimate."""

from pydantic import BaseModel, Field


class TaskPert(BaseModel):
    task_id: int
    te_hours: float = Field(description="Expected hours, (o + 4m + p) / 6")
    variance: float = Field(description="((p - o) / 6)^2, hours^2")
    std_hours: float


class Cocomo(BaseModel):
    loc_per_hour: float = Field(description="Productivity assumption used to size the project")
    ksloc: float
    exponent: float = Field(description="E = B + 0.01 * sum(scale factors)")
    effort_pm: float = Field(description="Person-months")
    tdev_months: float = Field(description="Calendar months")
    avg_staff: float


class ProjectEstimate(BaseModel):
    project_id: int
    task_count: int
    total_te_hours: float = Field(description="Bottom-up PERT effort: sum of task te")
    total_std_hours: float = Field(
        description="sqrt of summed task variances (effort uncertainty, not schedule)"
    )
    total_effort_pm: float = Field(description="total_te_hours / 152")
    tasks: list[TaskPert]
    cocomo: Cocomo | None = Field(description="Top-down cross-check; null when no tasks")
