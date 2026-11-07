"""Workflow endpoints shared by the planning (Step 15) and reallocation (Step 17) graphs:
start a plan, live events (SSE), state, PM decision. Thread ids starting with `realloc-`
belong to the reallocation runner."""

import json
import threading
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import Field
from sse_starlette import EventSourceResponse, ServerSentEvent

from app.db import get_session_factory
from app.schemas.common import CONFLICT, NOT_FOUND
from app.schemas.reallocation import ReallocationState
from app.schemas.workflow import (
    PlanDecision,
    PlanStart,
    PlanStarted,
    ResumeAccepted,
    WorkflowEvent,
    WorkflowState,
)
from app.services.workflows import Workflows, postgres_workflows

router = APIRouter(prefix="/workflows", tags=["workflows"])
_init_lock = threading.Lock()

AnyWorkflowState = Annotated[WorkflowState | ReallocationState, Field(discriminator="kind")]


def get_workflows(request: Request) -> Workflows:
    """Created on first use (not at startup), so the API starts even when Postgres is down.
    Tests put their own InMemorySaver-backed instance on `app.state.workflows` first."""
    state = request.app.state
    with _init_lock:
        if getattr(state, "workflows", None) is None:
            state.workflows = postgres_workflows(state.settings, get_session_factory())
    workflows: Workflows = state.workflows
    return workflows


WorkflowsDep = Annotated[Workflows, Depends(get_workflows)]


@router.post("/plan", name="start_plan", status_code=202, response_model=PlanStarted)
def start_plan(body: PlanStart, workflows: WorkflowsDep) -> PlanStarted:
    """Start brief -> WBS -> estimates -> schedule -> owners; it pauses for PM review."""
    return PlanStarted(thread_id=workflows.plan.start(body))


@router.get(
    "/{thread_id}/events",
    name="events",
    response_class=EventSourceResponse,
    responses={
        200: {
            "description": "Server-sent events; each `data` is a WorkflowEvent as JSON",
            "content": {"text/event-stream": {"schema": WorkflowEvent.model_json_schema()}},
        },
        **NOT_FOUND,
    },
)
async def events(
    thread_id: str,
    workflows: WorkflowsDep,
    last_event_id: Annotated[int, Header(alias="Last-Event-ID")] = 0,
) -> EventSourceResponse:
    """Past events, then live ones; the stream ends when the run is committed, rejected or
    failed. Reconnecting clients send `Last-Event-ID` to skip what they already have."""
    runner = workflows.runner(thread_id)
    await run_in_threadpool(runner.state, thread_id)  # 404 before the stream starts

    async def stream() -> AsyncIterator[ServerSentEvent]:
        async for event in runner.subscribe(thread_id, last_event_id):
            body = WorkflowEvent.model_validate(event).model_dump(mode="json")
            yield ServerSentEvent(data=json.dumps(body), event=body["type"], id=str(body["seq"]))

    return EventSourceResponse(stream(), ping=15)


@router.get(
    "/{thread_id}/state", name="get_state", response_model=AnyWorkflowState, responses=NOT_FOUND
)
def get_state(thread_id: str, workflows: WorkflowsDep) -> WorkflowState | ReallocationState:
    """Status, current node, and what the PM must decide on while waiting
    (`kind` = plan: `review`; `kind` = reallocate: `proposal`)."""
    return workflows.runner(thread_id).state(thread_id)


@router.post(
    "/{thread_id}/resume",
    name="resume",
    status_code=202,
    response_model=ResumeAccepted,
    responses={**NOT_FOUND, **CONFLICT},
)
def resume(
    thread_id: str, decision: Annotated[PlanDecision, Body()], workflows: WorkflowsDep
) -> ResumeAccepted:
    """Plan: approve -> commit; edit -> re-estimate and review again; reject -> end.
    Reallocation: approve -> apply new owners; reject (reason required) -> owners unchanged."""
    workflows.runner(thread_id).resume(thread_id, decision)
    return ResumeAccepted(thread_id=thread_id, status="running")
