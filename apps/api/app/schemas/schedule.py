"""Response schema for GET /projects/{id}/schedule."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class _FromEngine(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ScheduledTaskOut(_FromEngine):
    task_id: int
    member_id: int | None
    start: date
    end: date
    hours: float
    early_start: date = Field(description="CPM early start, ignoring resources")
    resource_delay_days: int = Field(description="Working days later than early_start")


class WeekLoadOut(_FromEngine):
    member_id: int
    week_start: date = Field(description="Monday of the ISO week")
    hours: float
    capacity: float
    utilisation: float = Field(description="hours / capacity; 0 when capacity is 0")


class ProjectSchedule(BaseModel):
    project_id: int
    start: date
    finish: date
    deadline: date
    tasks: list[ScheduledTaskOut]
    loads: list[WeekLoadOut]
    delayed: list[int] = Field(description="Task ids pushed back by resource limits")
