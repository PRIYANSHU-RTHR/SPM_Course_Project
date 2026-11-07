"""Planning workflow end to end (needs Postgres): fixture LLM, in-memory checkpointer.

The planning fixture is keyed on the demo brief and the seed skill vocabulary, so every test
seeds the demo team first. `PlanWorkflows.wait` blocks until a run segment is over, which
keeps the asynchronous endpoints deterministic in tests.
"""

import json
from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.agents.llm import LLMClient
from app.agents.planning import DEMO_BRIEF
from app.config import Settings
from app.models import Assignment, AuditLog, Dependency, Epic, Project, Task
from app.seed import seed_demo
from app.services.workflows import PlanWorkflows, build_workflows
from app.workflows.events import EventBus
from app.workflows.plan import PlanDeps, build_plan_graph

START = "2026-11-09"  # a Monday
BODY = {
    "brief": DEMO_BRIEF.read_text(encoding="utf-8"),
    "project_name": "Campus Food-Ordering App v2",
    "deadline": "2027-02-26",
    "budget": "900000.00",
    "start_date": START,
}
WAIT = 30  # seconds; a full run takes well under one


def _llm() -> LLMClient:
    return LLMClient(Settings(_env_file=None, llm_mode="fixture"))  # type: ignore[call-arg]


@pytest.fixture
def workflows(
    client: TestClient, session_factory: sessionmaker[Session], db: Session
) -> Iterator[PlanWorkflows]:
    seed_demo(db, seed=42, as_of=date(2026, 11, 6))
    db.commit()
    runners = build_workflows(InMemorySaver(), session_factory, _llm(), seed=42)
    client.app.state.workflows = runners  # type: ignore[attr-defined]
    yield runners.plan
    runners.shutdown()


def _start(client: TestClient, runner: PlanWorkflows) -> str:
    response = client.post("/workflows/plan", json=BODY)
    assert response.status_code == 202, response.text
    thread_id: str = response.json()["thread_id"]
    runner.wait(thread_id, WAIT)
    return thread_id


def _resume(client: TestClient, runner: PlanWorkflows, thread_id: str, body: dict) -> None:
    response = client.post(f"/workflows/{thread_id}/resume", json=body)
    assert response.status_code == 202, response.text
    runner.wait(thread_id, WAIT)


def _state(client: TestClient, thread_id: str) -> dict:
    response = client.get(f"/workflows/{thread_id}/state")
    assert response.status_code == 200, response.text
    body: dict = response.json()
    return body


def _events(client: TestClient, thread_id: str) -> list[dict]:
    """The whole SSE stream; it ends on its own once the run has finished."""
    response = client.get(f"/workflows/{thread_id}/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


def _count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_runs_to_review_then_approve_commits_the_project(
    client: TestClient, workflows: PlanWorkflows, db: Session
) -> None:
    thread_id = _start(client, workflows)
    state = _state(client, thread_id)

    assert (state["status"], state["node"], state["revision"]) == ("waiting", "pm_review", 0)
    review = state["review"]
    tasks = [t for e in review["wbs"]["epics"] for t in e["tasks"]]
    assert len(review["wbs"]["epics"]) == 5
    assert [t["local_id"] for t in tasks] == [f"T-{n:03d}" for n in range(1, 26)]
    assert len(review["warnings"]) >= 3  # the three skill-name fixes from validation
    est = review["estimates"]
    assert est["total_te_hours"] == pytest.approx(sum(t["te_hours"] for t in est["tasks"]))
    assert est["cocomo"]["effort_pm"] > 0
    sched = review["schedule"]
    assert sched["start"] == START
    assert sched["critical_path"]
    assert all(t["critical"] for t in sched["tasks"] if t["task_id"] in sched["critical_path"])
    recs = review["recommendations"]
    assert recs["mode"] == "optimal"
    assert [r["task_id"] for r in recs["items"]] == [t["local_id"] for t in tasks]
    chosen = [r for r in recs["items"] if r["member_id"] is not None]
    assert chosen
    assert all(r["member_name"] and r["candidates"] for r in chosen)
    assert all(0 < r["score"]["total"] <= 100 for r in chosen)
    assert recs["total_score"] == pytest.approx(sum(r["score"]["total"] for r in chosen))

    projects_before = _count(db, Project)
    _resume(client, workflows, thread_id, {"action": "approve", "actor": "pm:asha"})
    state = _state(client, thread_id)

    assert state["status"] == "committed"
    assert state["review"] is None
    project = db.get(Project, state["project_id"])
    assert project is not None
    assert project.name == BODY["project_name"]
    assert project.start_date == date.fromisoformat(START)
    assert _count(db, Project) == projects_before + 1
    task_ids = select(Task.id).where(Task.project_id == project.id)
    assert db.scalar(select(func.count()).where(Task.project_id == project.id)) == 25
    assert db.scalar(select(func.count()).where(Epic.project_id == project.id)) == 5
    links = sum(len(t["predecessors"]) for t in tasks)
    assert db.scalar(select(func.count()).where(Dependency.succ_task_id.in_(task_ids))) == links
    owners = db.scalar(
        select(func.count()).where(Assignment.task_id.in_(task_ids), Assignment.is_current)
    )
    assert owners == len(chosen)
    approved = db.scalars(select(AuditLog).where(AuditLog.action == "workflow.plan_approved")).one()
    assert (approved.actor, approved.entity_id) == ("pm:asha", project.id)
    assert approved.after is not None
    assert approved.after["thread_id"] == thread_id

    events = _events(client, thread_id)
    nodes = [e["node"] for e in events if e["type"] == "node" and e["phase"] == "end"]
    assert nodes == [
        "decompose",
        "validate",
        "estimate",
        "schedule",
        "recommend",
        "pm_review",  # ended as "waiting for PM review"
        "pm_review",  # re-run on resume: "approved"
        "commit",
    ]
    assert all(e["duration_ms"] >= 0 for e in events if e.get("phase") == "end")
    assert [e["status"] for e in events if e["type"] == "run"] == ["waiting", "committed"]


def test_edit_loops_back_to_estimate_then_reject_ends_without_a_project(
    client: TestClient, workflows: PlanWorkflows, db: Session
) -> None:
    thread_id = _start(client, workflows)
    before = _state(client, thread_id)["review"]
    te_before = {t["task_id"]: t["te_hours"] for t in before["estimates"]["tasks"]}

    _resume(
        client,
        workflows,
        thread_id,
        {
            "action": "edit",
            "changes": [
                {"op": "update", "task_id": "T-001", "o": 20, "m": 30, "p": 40},
                {"op": "remove", "task_id": "T-025"},
            ],
        },
    )
    state = _state(client, thread_id)
    after = state["review"]

    assert (state["status"], state["revision"], after["revision"]) == ("waiting", 1, 1)
    te_after = {t["task_id"]: t["te_hours"] for t in after["estimates"]["tasks"]}
    assert te_after["T-001"] == pytest.approx(30.0)
    assert "T-025" not in te_after
    assert len(te_after) == len(te_before) - 1
    expected = before["estimates"]["total_te_hours"] - te_before["T-001"] - te_before["T-025"]
    assert after["estimates"]["total_te_hours"] == pytest.approx(expected + 30)

    projects = _count(db, Project)
    _resume(client, workflows, thread_id, {"action": "reject", "reason": "Scope too large"})
    state = _state(client, thread_id)

    assert (state["status"], state["reason"], state["project_id"]) == (
        "rejected",
        "Scope too large",
        None,
    )
    assert _count(db, Project) == projects
    ends = [e["node"] for e in _events(client, thread_id) if e.get("phase") == "end"]
    # After the edit: straight back to estimate, not through decompose/validate again.
    assert ends[5:] == [
        "pm_review",
        "pm_review",
        "estimate",
        "schedule",
        "recommend",
        "pm_review",
        "pm_review",
    ]


def test_bad_edit_is_422_and_the_run_keeps_waiting(
    client: TestClient, workflows: PlanWorkflows
) -> None:
    thread_id = _start(client, workflows)
    cycle = {"op": "update", "task_id": "T-001", "predecessors": ["T-025"]}

    response = client.post(
        f"/workflows/{thread_id}/resume", json={"action": "edit", "changes": [cycle]}
    )

    assert response.status_code == 422
    assert "cycle" in response.json()["error"]["message"]
    assert _state(client, thread_id)["status"] == "waiting"
    bad_shape = client.post(f"/workflows/{thread_id}/resume", json={"action": "ship-it"})
    assert bad_shape.status_code == 422


def test_resume_after_the_end_is_409_and_unknown_threads_are_404(
    client: TestClient, workflows: PlanWorkflows
) -> None:
    thread_id = _start(client, workflows)
    _resume(client, workflows, thread_id, {"action": "reject", "reason": "no"})

    again = client.post(f"/workflows/{thread_id}/resume", json={"action": "approve"})
    assert again.status_code == 409
    assert again.json()["error"]["details"] == {"status": "rejected"}

    for response in (
        client.get("/workflows/nope/state"),
        client.get("/workflows/nope/events"),
        client.post("/workflows/nope/resume", json={"action": "approve"}),
    ):
        assert response.status_code == 404


def test_deadline_before_start_is_rejected(client: TestClient, workflows: PlanWorkflows) -> None:
    response = client.post("/workflows/plan", json={**BODY, "deadline": "2026-11-01"})
    assert response.status_code == 422


def test_graph_interrupts_with_payload_and_resumes(
    session_factory: sessionmaker[Session], db: Session
) -> None:
    """The compiled graph on its own, as LangGraph runs it: invoke -> __interrupt__ -> resume."""
    seed_demo(db, seed=42, as_of=date(2026, 11, 6))
    db.commit()
    bus = EventBus()
    graph = build_plan_graph(PlanDeps(session_factory, _llm(), bus.publish)).compile(
        checkpointer=InMemorySaver()
    )
    config = {"configurable": {"thread_id": "t-graph"}}
    request = {**BODY, "hourly_rate": "850.00"}

    paused = graph.invoke({"thread_id": "t-graph", "request": request}, config)

    [pending] = paused["__interrupt__"]
    assert set(pending.value) == {
        "thread_id",
        "revision",
        "project_name",
        "wbs",
        "warnings",
        "estimates",
        "schedule",
        "recommendations",
    }
    done = graph.invoke(Command(resume={"action": "approve"}), config)
    assert done["status"] == "committed"
    assert db.get(Project, done["project_id"]) is not None
    assert graph.get_state(config).next == ()
