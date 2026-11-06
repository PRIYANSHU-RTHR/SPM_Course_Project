"""Response schema for GET /projects/{id}/cpm. Times are hours from project start."""

from pydantic import BaseModel, Field


class CpmTask(BaseModel):
    task_id: int
    duration_hours: float = Field(description="PERT te")
    es: float = Field(description="Earliest start")
    ef: float = Field(description="Earliest finish")
    ls: float = Field(description="Latest start")
    lf: float = Field(description="Latest finish")
    total_slack: float = Field(description="LS - ES: delay possible without moving the end date")
    free_slack: float = Field(description="Delay possible without moving any successor")
    critical: bool


class ProjectCpm(BaseModel):
    project_id: int
    project_duration_hours: float
    critical_paths: list[list[int]] = Field(description="Task ids, start to end, one per path")
    tasks: list[CpmTask] = Field(description="In topological order")
