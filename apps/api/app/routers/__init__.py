"""FastAPI routers. Thin: validate -> call service -> return. Route `name` = operationId suffix."""

from fastapi import APIRouter

from app.routers import (
    assignment,
    cpm,
    dependencies,
    epics,
    estimate,
    evm,
    forecast,
    members,
    metrics,
    projects,
    reallocation,
    risks,
    schedule,
    simulation,
    skills,
    tasks,
    workflows,
)

ROUTERS: tuple[APIRouter, ...] = (
    projects.router,
    epics.router,
    tasks.router,
    dependencies.router,
    members.router,
    skills.router,
    estimate.router,
    cpm.router,
    assignment.router,
    schedule.router,
    forecast.router,
    evm.router,
    risks.router,
    workflows.router,
    reallocation.router,
    simulation.router,
    simulation.audit_router,
    metrics.router,
)
