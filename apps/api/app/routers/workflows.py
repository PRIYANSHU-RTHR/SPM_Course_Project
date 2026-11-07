"""Planning workflow endpoints: start, live events (SSE), state, PM decision."""

import json
import threading
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, Request
from fastapi.concurrency import run_in_threadpool
from sse_starlette import EventSourceResponse, ServerSentEvent

from app.db import get_session_factory
from app.schemas.common import CONFLICT, NOT_FOUND
from app.schemas.workflow import (
    PlanDecision,
    PlanStart,
    PlanStarted,
    ResumeAccepted,
    WorkflowEvent,
    WorkflowState,
)
from app.services.workflows import PlanWorkflows, postgres_workflows

router = APIRouter(prefix="/workflows", tags=["workflows"])
_init_lock = threading.Lock()


def get_plan_workflows(request: Request) -> PlanWorkflows:
    """Created on first use (not at startup), so the API starts even when Postgres is down.
    Tests put their own InMemorySaver-backed instance on `app.state.plan_workflows` first."""
    state = request.app.state
    with _init_lock:
        if getattr(state, "plan_workflows", None) is None:
            state.plan_workflows, state.plan_workflows_pool = postgres_workflows(
                state.settings, get_session_factory()
            )
    workflows: PlanWorkflows = state.plan_workflows
    return workflows


WorkflowsDep = Annotated[PlanWorkflows, Depends(get_plan_workflows)]


@router.post("/plan", name="start_plan", status_code=202, response_model=PlanStarted)
def start_plan(body: PlanStart, workflows: WorkflowsDep) -> PlanStarted:
    """Start brief -> WBS -> estimates -> schedule -> owners; it pauses for PM review."""
    return PlanStarted(thread_id=workflows.start(body))


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
    await run_in_threadpool(workflows.state, thread_id)  # 404 before the stream starts

    async def stream() -> AsyncIterator[ServerSentEvent]:
        async for event in workflows.subscribe(thread_id, last_event_id):
            body = WorkflowEvent.model_validate(event).model_dump(mode="json")
            yield ServerSentEvent(data=json.dumps(body), event=body["type"], id=str(body["seq"]))

    return EventSourceResponse(stream(), ping=15)


@router.get(
    "/{thread_id}/state", name="get_state", response_model=WorkflowState, responses=NOT_FOUND
)
def get_state(thread_id: str, workflows: WorkflowsDep) -> WorkflowState:
    """Status, current node, and the review payload while waiting for the PM."""
    return workflows.state(thread_id)


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
    """approve -> commit; edit -> re-estimate and review again; reject -> end."""
    workflows.resume(thread_id, decision)
    return ResumeAccepted(thread_id=thread_id, status="running")
