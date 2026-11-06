"""FastAPI routers. Thin: validate -> call service -> return. Route `name` = operationId suffix."""

from fastapi import APIRouter

from app.routers import dependencies, epics, members, projects, skills, tasks

ROUTERS: tuple[APIRouter, ...] = (
    projects.router,
    epics.router,
    tasks.router,
    dependencies.router,
    members.router,
    skills.router,
)
