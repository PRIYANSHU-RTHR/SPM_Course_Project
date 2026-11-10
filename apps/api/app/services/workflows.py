"""Runs the LangGraph workflows in worker threads and answers state/resume/event requests.

One graph run per `thread_id`. `start` and `resume` return at once; the graph runs in a
thread pool (the nodes do blocking DB and LLM work) and reports progress on the event bus.
The checkpointer is the source of truth for state: PostgresSaver in the app, InMemorySaver
in tests. `WorkflowRunner` holds what both workflows share; `PlanWorkflows` (Step 15) and
`ReallocateWorkflows` (Step 17) add their start/resume checks and state shape.
"""

import logging
import threading
import uuid
from collections.abc import AsyncIterator, Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from sqlalchemy import make_url, select
from sqlalchemy.orm import Session, sessionmaker

from app.agents.llm import LLMClient
from app.agents.planning import DEMO_BRIEF, WBSPlan
from app.config import Settings
from app.engines.calendar import next_working_day
from app.engines.montecarlo import DEFAULT_RUNS
from app.errors import ConflictError, NotFoundError, ValidationFailedError
from app.models import Reallocation, ReallocationStatus
from app.schemas.reallocation import (
    Disruption,
    ProposalPayload,
    ReallocationState,
    ScenarioMetrics,
)
from app.schemas.workflow import (
    TERMINAL_STATUSES,
    EditDecision,
    PlanDecision,
    PlanReview,
    PlanStart,
    WorkflowState,
    WorkflowStatus,
)
from app.services.disruptions import check_disruption, pending_for_project
from app.services.inputs import project_today
from app.workflows.events import Event, EventBus, is_terminal
from app.workflows.plan import EditError, PlanDeps, apply_changes, build_plan_graph
from app.workflows.reallocate import ReallocDeps, build_reallocate_graph

logger = logging.getLogger(__name__)

REALLOCATE_PREFIX = "realloc-"

EXAMPLE_PROJECT_NAME = "Campus Food-Ordering App v2"
EXAMPLE_WEEKS = 16
EXAMPLE_BUDGET = Decimal("900000.00")


def example_plan(today: date) -> PlanStart:
    """The demo brief with sensible defaults: start next Monday, deadline 16 weeks later.
    Its planning reply is recorded, so it runs with LLM_MODE=fixture (no API key)."""
    start = today + timedelta(days=7 - today.weekday())
    return PlanStart(
        brief=DEMO_BRIEF.read_text(encoding="utf-8"),
        project_name=EXAMPLE_PROJECT_NAME,
        start_date=start,
        deadline=start + timedelta(weeks=EXAMPLE_WEEKS) - timedelta(days=3),  # a Friday
        budget=EXAMPLE_BUDGET,
    )


def _config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


class WorkflowRunner:
    name = "workflow"

    def __init__(self, graph: CompiledStateGraph, bus: EventBus, max_workers: int = 4) -> None:
        self.graph = graph
        self.bus = bus
        self._executor = ThreadPoolExecutor(max_workers, thread_name_prefix=f"{self.name}-run")
        self._lock = threading.Lock()
        self._running: dict[str, Future[None]] = {}
        self._errors: dict[str, str] = {}

    # -- shared commands ------------------------------------------------------------------------

    def _resume(
        self, thread_id: str, value: dict[str, Any], check: Callable[[Any], None] | None = None
    ) -> None:
        """Resume an interrupted run. `check(snapshot)` may raise to refuse the value."""
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
            if check is not None:
                check(snapshot)
            self._submit(thread_id, Command(resume=value))

    def _snapshot(self, thread_id: str) -> tuple[WorkflowStatus, Any, str | None]:
        """(status, snapshot, current node). 404 for threads this runner never saw."""
        with self._lock:
            running = thread_id in self._running
        snapshot = self.graph.get_state(_config(thread_id))
        if not snapshot.values and not running:
            raise self._not_found(thread_id)
        status: WorkflowStatus = "running" if running else self._status(thread_id, snapshot)
        if status == "running":
            node = self.bus.current_node(thread_id)
        elif status in ("waiting", "failed") and snapshot.next:
            node = snapshot.next[0]
        else:
            node = None
        return status, snapshot, node

    def state(self, thread_id: str) -> Any:
        raise NotImplementedError

    async def subscribe(self, thread_id: str, after_seq: int = 0) -> AsyncIterator[Event]:
        """Replay + live events. A finished run with no history here (e.g. after a restart)
        gets one synthetic run event with its final status, so the stream still closes."""
        history = self.bus.history(thread_id)
        if not any(is_terminal(e) for e in history):
            status = self._snapshot(thread_id)[0]  # 404 for unknown threads
            if status in TERMINAL_STATUSES:
                yield {
                    "seq": 0,
                    "thread_id": thread_id,
                    "type": "run",
                    "status": status,
                    "summary": f"run already {status}",
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

    # -- hooks ----------------------------------------------------------------------------------

    def _summary(self, status: str, values: dict[str, Any]) -> str:
        return {"waiting": "waiting for PM review"}.get(status, status)

    def _on_failed(self, thread_id: str) -> None:
        """Called after a run raised."""

    # -- internals ------------------------------------------------------------------------------

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
            summary = self._summary(status, snapshot.values or {})
        except Exception as exc:  # the run must report *something*; keep the server alive
            logger.exception("%s workflow %s failed", self.name, thread_id)
            status, summary = "failed", f"{type(exc).__name__}: {exc}"
            with self._lock:
                self._errors[thread_id] = summary
            try:
                self._on_failed(thread_id)
            except Exception:
                logger.exception("could not record the failure of %s", thread_id)
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


class PlanWorkflows(WorkflowRunner):
    """Brief -> WBS -> estimates -> schedule -> owners -> PM review -> project (Step 15)."""

    name = "plan"

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver,
        session_factory: sessionmaker[Session],
        llm: LLMClient,
        bus: EventBus | None = None,
        max_workers: int = 4,
    ) -> None:
        bus = bus or EventBus()
        deps = PlanDeps(session_factory=session_factory, llm=llm, publish=bus.publish)
        graph = build_plan_graph(deps).compile(checkpointer=checkpointer)
        super().__init__(graph, bus, max_workers)

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
        def check(snapshot: Any) -> None:
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

        self._resume(thread_id, decision.model_dump(mode="json"), check)

    def state(self, thread_id: str) -> WorkflowState:
        status, snapshot, node = self._snapshot(thread_id)
        values = snapshot.values or {}
        review = self._interrupt(snapshot) if status == "waiting" else None
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

    def _summary(self, status: str, values: dict[str, Any]) -> str:
        if status == "committed":
            return f"project {values.get('project_id')} committed"
        if status == "rejected":
            return "plan rejected"
        return super()._summary(status, values)


class ReallocateWorkflows(WorkflowRunner):
    """Disruption -> proposal -> PM approval -> new owners (Step 17)."""

    name = "reallocate"

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver,
        session_factory: sessionmaker[Session],
        seed: int,
        bus: EventBus | None = None,
        runs: int = DEFAULT_RUNS,
        max_workers: int = 4,
    ) -> None:
        bus = bus or EventBus()
        deps = ReallocDeps(session_factory=session_factory, publish=bus.publish)
        graph = build_reallocate_graph(deps).compile(checkpointer=checkpointer)
        super().__init__(graph, bus, max_workers)
        self._session_factory = session_factory
        self._seed = seed
        self._runs = runs
        self._projects: dict[str, int] = {}  # thread id -> project id, for runs in flight

    def start(self, project_id: int, disruption: Disruption) -> str:
        with self._session_factory() as s:
            project = check_disruption(s, project_id, disruption)  # 404 / 422
            as_of = project_today(project)
            pending = pending_for_project(s, project_id)
        with self._lock:
            busy = [t for t, p in self._projects.items() if p == project_id and t in self._running]
            if pending or busy:
                raise ConflictError(
                    "This project already has a reallocation in progress; approve or reject it "
                    "first",
                    details={"thread_ids": sorted({*pending, *busy})},
                )
            thread_id = f"{REALLOCATE_PREFIX}{uuid.uuid4().hex}"
            self._projects[thread_id] = project_id
            self._submit(
                thread_id,
                {
                    "thread_id": thread_id,
                    "project_id": project_id,
                    "disruption": disruption.model_dump(mode="json"),
                    "as_of": as_of.isoformat(),
                    "seed": self._seed,
                    "runs": self._runs,
                },
            )
        return thread_id

    def resume(self, thread_id: str, decision: PlanDecision) -> None:
        if isinstance(decision, EditDecision):
            raise ValidationFailedError(
                "A reallocation proposal can only be approved or rejected",
                details={"action": "edit"},
            )
        self._resume(thread_id, decision.model_dump(mode="json"))

    def state(self, thread_id: str) -> ReallocationState:
        status, snapshot, node = self._snapshot(thread_id)
        values = snapshot.values or {}
        proposal = self._interrupt(snapshot) if status == "waiting" else None
        return ReallocationState(
            thread_id=thread_id,
            status=status,
            node=node,
            project_id=values.get("project_id", self._projects.get(thread_id, 0)),
            reallocation_id=values.get("reallocation_id"),
            proposal=ProposalPayload.model_validate(proposal) if proposal is not None else None,
            outcome=ScenarioMetrics.model_validate(values["outcome"])
            if values.get("outcome")
            else None,
            applied=values.get("applied", []),
            reason=values.get("reason"),
            error=self._errors.get(thread_id) if status == "failed" else None,
        )

    def _summary(self, status: str, values: dict[str, Any]) -> str:
        if status == "committed":
            return f"reallocation applied: {len(values.get('applied', []))} assignments changed"
        if status == "rejected":
            return "reallocation rejected; owners unchanged"
        return super()._summary(status, values)

    def _on_failed(self, thread_id: str) -> None:
        """A pending proposal whose run broke must not block the project forever."""
        with self._session_factory() as s:
            row = s.scalar(select(Reallocation).where(Reallocation.thread_id == thread_id))
            if row is not None and row.status == ReallocationStatus.PENDING:
                row.status = ReallocationStatus.FAILED
                row.reason = self._errors.get(thread_id)
                s.commit()


@dataclass
class Workflows:
    """Both runners on one event bus and one checkpointer."""

    plan: PlanWorkflows
    reallocate: ReallocateWorkflows
    bus: EventBus
    pool: ConnectionPool | None = None

    def runner(self, thread_id: str) -> PlanWorkflows | ReallocateWorkflows:
        return self.reallocate if thread_id.startswith(REALLOCATE_PREFIX) else self.plan

    def shutdown(self) -> None:
        self.plan.shutdown()
        self.reallocate.shutdown()
        if self.pool is not None:
            self.pool.close()


def build_workflows(
    checkpointer: BaseCheckpointSaver,
    session_factory: sessionmaker[Session],
    llm: LLMClient,
    seed: int,
    runs: int = DEFAULT_RUNS,
    pool: ConnectionPool | None = None,
) -> Workflows:
    bus = EventBus()
    return Workflows(
        plan=PlanWorkflows(checkpointer, session_factory, llm, bus),
        reallocate=ReallocateWorkflows(checkpointer, session_factory, seed, bus, runs),
        bus=bus,
        pool=pool,
    )


def postgres_workflows(settings: Settings, session_factory: sessionmaker[Session]) -> Workflows:
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
    return build_workflows(
        saver, session_factory, LLMClient(settings), settings.sim_seed, pool=pool
    )
