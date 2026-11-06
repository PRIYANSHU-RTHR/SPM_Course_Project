"""Response schema for GET /projects/{id}/forecast. Hours = working hours from project start."""

from datetime import date

from pydantic import BaseModel, Field


class HistogramBin(BaseModel):
    start_hours: float
    runs: int


class CdfPoint(BaseModel):
    hours: float
    probability: float


class Percentile(BaseModel):
    hours: float
    on: date = Field(description="Working day on which that many hours are reached")


class ProjectForecast(BaseModel):
    project_id: int
    runs: int
    seed: int
    deadline: date
    deadline_hours: float = Field(description="Working hours from start to deadline, 8 h/day")
    p_on_time: float = Field(description="Share of runs finishing by the deadline")
    mean_hours: float
    p50: Percentile
    p80: Percentile
    p95: Percentile
    histogram: list[HistogramBin]
    cdf: list[CdfPoint]
    criticality: dict[int, float] = Field(description="Task id -> share of runs on a longest path")
