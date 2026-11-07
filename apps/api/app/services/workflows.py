"""Runs the planning workflow in worker threads and answers state/resume/event requests.

One graph run per `thread_id`. `start` and `resume` return at once; the graph runs in a
thread pool (the nodes do blocking DB and LLM work) and reports progress on the event bus.
The checkpointer is the source of truth for state: PostgresSaver in the app, InMemorySaver
in tests.
"""

import logging
import threading
import uuid
from collections.abc import AsyncIterator
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from sqlalchemy import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.agents.llm import LLMClient
from app.agents.planning import WBSPlan
from app.config import Settings
from app.engines.calendar import next_working_day
from app.errors import ConflictError, NotFoundError, ValidationFailedError
from app.schemas.workflow import (
    TERMINAL_STATUSES,
    EditDecision,
    PlanDecision,
    PlanReview,
    PlanStart,
    WorkflowState,
    WorkflowStatus,
)
from app.workflows.events import Event, EventBus, is_terminal
from app.workflows.plan import EditError, PlanDeps, apply_changes, build_plan_graph

logger = logging.getLogger(__name__)


def _config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


class PlanWorkflows:
    def __init__(
        self,
        checkpointer: BaseCheckpointSaver,
        session_factory: sessionmaker[Session],
        llm: LLMClient,
        bus: EventBus | None = None,
        max_workers: int = 4,
    ) -> None:
        self.bus = bus or EventBus()
        deps = PlanDeps(session_factory=session_factory, llm=llm, publish=self.bus.publish)
        self.graph = build_plan_graph(deps).compile(checkpointer=checkpointer)
        self._executor = ThreadPoolExecutor(max_workers, thread_name_prefix="plan-workflow")
        self._lock = threading.Lock()
        self._running: dict[str, Future[None]] = {}
        self._errors: dict[str, str] = {}

    # -- commands ---------------------------------------------------------------------------

    def start(self, request: PlanStart) -> str:
        start = request.start_date or next_working_day(datetime.now(UTC).date())
        if request.deadline <= start:
            raise ValidationFailedError(
                "deadline must be after the start date",
                details={"start_date": start.isoformat(), "deadline": request.deadline.isoformat()},
            )
        thread_id = uuid.uuid4().hex
        payload = {
            "thread_id": thread_id,
            "request": {**request.model_dump(mode="json"), "start_date": start.isoformat()},
        }
        with self._lock:
            self._submit(thread_id, payload)
        return thread_id

    def resume(self, thread_id: str, decision: PlanDecision) -> None:
        with self._lock:
            if thread_id in self._running:
                raise ConflictError("The workflow is still running", details={"status": "running"})
            snapshot = self.graph.get_state(_config(thread_id))
            if not snapshot.values:
                raise self._not_found(thread_id)
            if self._interrupt(snapshot) is None:
                status = self._status(thread_id, snapshot)
                raise ConflictError(
                    f"The workflow is not waiting for review (status: {status})",
                    details={"status": status},
                )
            if isinstance(decision, EditDecision):
                values = snapshot.values
                try:  # same check the node repeats, so a bad edit is a 422 now, not a failed run
                    apply_changes(
                        WBSPlan.model_validate(values["wbs"]),
                        decision.changes,
                        values["vocabulary"],
                    )
                except EditError as exc:
                    raise ValidationFailedError(str(exc)) from exc
            self._submit(thread_id, Command(resume=decision.model_dump(mode="json")))

    # -- queries ----------------------------------------------------------------------------

    def state(self, thread_id: str) -> WorkflowState:
        with self._lock:
            running = thread_id in self._running
        snapshot = self.graph.get_state(_config(thread_id))
        values = snapshot.values or {}
        if not values and not running:
            raise self._not_found(thread_id)
        status: WorkflowStatus = "running" if running else self._status(thread_id, snapshot)
        review = self._interrupt(snapshot) if status == "waiting" else None
        if status == "running":
            node = self.bus.current_node(thread_id)
        elif status in ("waiting", "failed") and snapshot.next:
            node = snapshot.next[0]
        else:
            node = None
        return WorkflowState(
            thread_id=thread_id,
            status=status,
            node=node,
            revision=values.get("revision", 0),
            review=PlanReview.model_validate(review) if review is not None else None,
            project_id=values.get("project_id"),
            reason=values.get("reason"),
            error=self._errors.get(thread_id) if status == "failed" else None,
        )

    async def subscribe(self, thread_id: str, after_seq: int = 0) -> AsyncIterator[Event]:
        """Replay + live events. A finished run with no history here (e.g. after a restart)
        gets one synthetic run event with its final status, so the stream still closes."""
        history = self.bus.history(thread_id)
        if not any(is_terminal(e) for e in history):
            state = self.state(thread_id)  # 404 for unknown threads
            if state.status in TERMINAL_STATUSES:
                yield {
                    "seq": 0,
                    "thread_id": thread_id,
                    "type": "run",
                    "status": state.status,
                    "summary": f"run already {state.status}",
                }
                return
        async for event in self.bus.subscribe(thread_id, after_seq):
            yield event

    def wait(self, thread_id: str, timeout: float | None = None) -> None:
        """Block until the current run segment (to the next interrupt or the end) is over."""
        with self._lock:
            future = self._running.get(thread_id)
        if future is not None:
            future.result(timeout)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)

    # -- internals --------------------------------------------------------------------------

    def _submit(self, thread_id: str, payload: Any) -> None:
        """Caller holds the lock."""
        self._errors.pop(thread_id, None)
        self._running[thread_id] = self._executor.submit(self._run, thread_id, payload)

    def _run(self, thread_id: str, payload: Any) -> None:
        config = _config(thread_id)
        try:
            self.graph.invoke(payload, config)
            snapshot = self.graph.get_state(config)
            status = self._status(thread_id, snapshot)
            summary = {
                "waiting": "waiting for PM review",
                "committed": f"project {snapshot.values.get('project_id')} committed",
                "rejected": "plan rejected",
            }.get(status, status)
        except Exception as exc:  # the run must report *something*; keep the server alive
            logger.exception("planning workflow %s failed", thread_id)
            status, summary = "failed", f"{type(exc).__name__}: {exc}"
            with self._lock:
                self._errors[thread_id] = summary
        with self._lock:
            self._running.pop(thread_id, None)
        self.bus.publish(
            {"thread_id": thread_id, "type": "run", "status": status, "summary": summary}
        )

    @staticmethod
    def _interrupt(snapshot: Any) -> Any | None:
        for task in snapshot.tasks:
            if task.interrupts:
                return task.interrupts[0].value
        return None

    def _status(self, thread_id: str, snapshot: Any) -> WorkflowStatus:
        if self._interrupt(snapshot) is not None:
            return "waiting"
        status = (snapshot.values or {}).get("status")
        if status in ("committed", "rejected"):
            return status  # type: ignore[no-any-return]
        if thread_id not in self._errors:
            self._errors[thread_id] = "the run stopped before finishing (server restart?)"
        return "failed"

    @staticmethod
    def _not_found(thread_id: str) -> NotFoundError:
        return NotFoundError(f"Workflow {thread_id} not found", details={"thread_id": thread_id})


def postgres_workflows(
    settings: Settings, session_factory: sessionmaker[Session]
) -> tuple[PlanWorkflows, ConnectionPool]:
    """App wiring: PostgresSaver on a small psycopg pool in the app database."""
    from langgraph.checkpoint.postgres import PostgresSaver

    conninfo = make_url(settings.database_url).set(drivername="postgresql")
    pool: ConnectionPool = ConnectionPool(
        conninfo=conninfo.render_as_string(hide_password=False),
        min_size=1,
        max_size=4,
        # Required by PostgresSaver (same as its from_conn_string).
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )
    saver = PostgresSaver(pool)  # type: ignore[arg-type]
    saver.setup()  # creates/migrates its checkpoint_* tables; idempotent
    return PlanWorkflows(saver, session_factory, LLMClient(settings)), pool
