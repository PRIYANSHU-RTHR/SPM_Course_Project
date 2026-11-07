"""Disruptions, reallocation proposals, approval/rejection, simulated clock, audit trail
(needs Postgres). Demo seed with the clock pinned to 2026-11-06; in-memory checkpointer.

In the seed, Aarav Mehta (member 1) owns the two open payment tasks: T-11 "Cart and checkout
API" (90% done) and T-12 "Payment gateway integration" (blocked). Putting him on leave for
the next two weeks is the plan.md demo disruption. T-11's last 10% is planned for Friday
2026-11-06, before the leave, so only T-12 loses its owner.
"""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.agents.llm import LLMClient
from app.config import Settings
from app.models import (
    Assignment,
    AuditLog,
    Availability,
    AvailabilityKind,
    Dependency,
    Project,
    Reallocation,
    Snapshot,
    Task,
)
from app.seed import seed_demo
from app.services.workflows import ReallocateWorkflows, build_workflows

TODAY = date(2026, 11, 6)  # a Friday; the seed's "today"
AARAV = 1
LEAVE = {
    "type": "leave",
    "member_id": AARAV,
    "start_date": "2026-11-09",
    "end_date": "2026-11-20",
    "reason": "Family emergency",
}
WAIT = 60


def _seed(db: Session) -> None:
    seed_demo(db, seed=42, as_of=TODAY)
    db.flush()
    db.get_one(Project, 1).sim_date = TODAY
    db.commit()


@pytest.fixture
def realloc(
    client: TestClient, session_factory: sessionmaker[Session], db: Session
) -> Iterator[ReallocateWorkflows]:
    _seed(db)
    llm = LLMClient(Settings(_env_file=None, llm_mode="fixture"))  # type: ignore[call-arg]
    runners = build_workflows(InMemorySaver(), session_factory, llm, seed=42, runs=1000)
    client.app.state.workflows = runners  # type: ignore[attr-defined]
    yield runners.reallocate
    runners.shutdown()


def _disrupt(client: TestClient, runner: ReallocateWorkflows, body: dict) -> dict:
    """Post a disruption, wait for the proposal, return the workflow state."""
    response = client.post("/projects/1/disruptions", json=body)
    assert response.status_code == 202, response.text
    thread_id = response.json()["thread_id"]
    assert thread_id.startswith("realloc-")
    runner.wait(thread_id, WAIT)
    state = client.get(f"/workflows/{thread_id}/state").json()
    assert state["status"] == "waiting", state
    return state


def _decide(client: TestClient, runner: ReallocateWorkflows, thread_id: str, body: dict) -> dict:
    response = client.post(f"/workflows/{thread_id}/resume", json=body)
    assert response.status_code == 202, response.text
    runner.wait(thread_id, WAIT)
    state: dict = client.get(f"/workflows/{thread_id}/state").json()
    return state


def _owners(db: Session) -> dict[int, int]:
    db.expire_all()
    rows = db.execute(select(Assignment.task_id, Assignment.member_id).where(Assignment.is_current))
    return dict(rows.all())


def _actions(db: Session) -> list[str]:
    db.expire_all()
    return list(db.scalars(select(AuditLog.action).order_by(AuditLog.id)))


def test_leave_proposes_moving_that_members_tasks(
    client: TestClient, realloc: ReallocateWorkflows, db: Session
) -> None:
    owners_before = _owners(db)
    state = _disrupt(client, realloc, LEAVE)
    proposal = state["proposal"]

    assert (state["kind"], state["node"]) == ("reallocate", "pm_approval")
    items = {i["task_id"]: i for i in proposal["items"]}
    assert 11 not in items or "owner_unavailable" not in items[11]["reasons"]
    for task_id in (12,):  # Aarav's open task inside the leave
        item = items[task_id]
        assert "owner_unavailable" in item["reasons"]
        assert item["before"] == {"member_id": AARAV, "name": "Aarav Mehta"}
        assert item["before_eligible"] is False
        assert item["before_ineligible_reason"].startswith("on leave")
        assert item["changed"] is True
        assert item["after"]["member_id"] not in (None, AARAV)
        assert item["finish_after"] <= item["finish_before"]
    # The leave hurts, the proposal recovers part of it, all computed by engines.
    before, now, after = (proposal[k] for k in ("before_disruption", "now", "if_approved"))
    assert now["finish"] > before["finish"]
    assert now["p_on_time"] <= before["p_on_time"]
    assert after["finish"] < now["finish"]
    assert after["p_on_time"] >= now["p_on_time"]
    assert "Aarav Mehta is on leave 2026-11-09 to 2026-11-20." in proposal["summary"]

    # The leave is a fact now; the owners are not touched until the PM decides.
    leave = db.scalars(
        select(Availability).where(
            Availability.member_id == AARAV, Availability.kind == AvailabilityKind.LEAVE
        )
    ).all()
    assert [(a.start_date.isoformat(), a.end_date.isoformat()) for a in leave] == [
        ("2026-11-09", "2026-11-20")
    ]
    assert _owners(db) == owners_before
    pending = client.get("/projects/1/proposals", params={"status": "pending"}).json()
    assert [p["id"] for p in pending["items"]] == [proposal["reallocation_id"]]
    assert pending["items"][0]["payload"]["items"] == proposal["items"]
    assert "disruption.leave" in _actions(db)


def test_approve_applies_new_owners_with_audit(
    client: TestClient, realloc: ReallocateWorkflows, db: Session
) -> None:
    proposal = _disrupt(client, realloc, LEAVE)["proposal"]
    changed = {i["task_id"]: i["after"]["member_id"] for i in proposal["items"] if i["changed"]}
    thread_id = proposal["thread_id"]
    audit_before = len(_actions(db))

    state = _decide(
        client,
        realloc,
        thread_id,
        {"action": "approve", "actor": "pm:asha", "reason": "Diya knows the payments code"},
    )

    assert state["status"] == "committed"
    assert len(state["applied"]) == len(changed)
    owners = _owners(db)
    assert {t: owners[t] for t in changed} == changed
    # The outcome after approval is exactly what the proposal predicted.
    assert state["outcome"]["finish"] == proposal["if_approved"]["finish"]
    assert state["outcome"]["p_on_time"] == proposal["if_approved"]["p_on_time"]

    db.expire_all()
    new_rows = db.scalars(select(AuditLog).where(AuditLog.id > audit_before)).all()
    approved = [a for a in new_rows if a.action == "reallocation.approved"]
    assert len(approved) == 1
    assert (approved[0].before, approved[0].after) == (
        {"status": "pending"},
        {"status": "approved"},
    )
    moves = [a for a in new_rows if a.action == "assignment.ai"]
    assert len(moves) == len(changed)
    assert all(a.actor == "pm:asha" and a.reason == "Diya knows the payments code" for a in moves)
    by_task = {a.after["task_id"]: a for a in moves if a.after}
    assert by_task[12].before == {"task_id": 12, "member_id": AARAV}
    assert by_task[12].after is not None
    assert by_task[12].after["member_id"] == changed[12]

    row = db.get_one(Reallocation, proposal["reallocation_id"])
    assert (row.status.value, row.decided_by) == ("approved", "pm:asha")
    assert row.decided_at is not None
    audit = client.get("/projects/1/audit", params={"limit": 200}).json()
    actions = [a["action"] for a in audit["items"]]
    assert {"disruption.leave", "reallocation.approved", "assignment.ai"} <= set(actions)
    ids = [a["id"] for a in audit["items"]]
    assert ids == sorted(ids, reverse=True)  # newest first


def test_reject_changes_no_owner(
    client: TestClient, realloc: ReallocateWorkflows, db: Session
) -> None:
    owners_before = _owners(db)
    proposal = _disrupt(client, realloc, LEAVE)["proposal"]

    state = _decide(
        client, realloc, proposal["thread_id"], {"action": "reject", "reason": "He is back early"}
    )

    assert (state["status"], state["reason"], state["applied"]) == (
        "rejected",
        "He is back early",
        [],
    )
    assert _owners(db) == owners_before
    row = db.get_one(Reallocation, proposal["reallocation_id"])
    assert (row.status.value, row.reason) == ("rejected", "He is back early")
    assert "assignment.ai" not in _actions(db)
    assert _actions(db)[-1] == "reallocation.rejected"
    # Deciding again is refused; a new disruption is allowed now.
    again = client.post(f"/workflows/{proposal['thread_id']}/resume", json={"action": "approve"})
    assert again.status_code == 409
    nothing_pending = client.get("/projects/1/proposals", params={"status": "pending"}).json()
    assert nothing_pending["total"] == 0


def test_one_reallocation_at_a_time_and_only_approve_or_reject(
    client: TestClient, realloc: ReallocateWorkflows
) -> None:
    proposal = _disrupt(client, realloc, LEAVE)["proposal"]

    second = client.post("/projects/1/disruptions", json={**LEAVE, "member_id": 2})
    assert second.status_code == 409
    assert second.json()["error"]["details"]["thread_ids"] == [proposal["thread_id"]]
    edit = client.post(
        f"/workflows/{proposal['thread_id']}/resume",
        json={"action": "edit", "changes": [{"op": "remove", "task_id": "T-001"}]},
    )
    assert edit.status_code == 422


@pytest.mark.parametrize(
    ("project_id", "body", "status"),
    [
        (999, LEAVE, 404),
        (1, {**LEAVE, "member_id": 999}, 404),
        (1, {**LEAVE, "end_date": "2026-11-01"}, 422),
        (1, {"type": "slip", "task_id": 1, "extra_hours": 8}, 422),  # T-1 is done
        (1, {"type": "slip", "task_id": 999, "extra_hours": 8}, 404),
        (1, {"type": "slip", "task_id": 15, "extra_hours": 0}, 422),
        (1, {"type": "meteor"}, 422),
    ],
)
def test_bad_disruptions_are_refused_before_anything_is_written(
    client: TestClient,
    realloc: ReallocateWorkflows,
    db: Session,
    project_id: int,
    body: dict,
    status: int,
) -> None:
    audit_before = _actions(db)
    response = client.post(f"/projects/{project_id}/disruptions", json=body)

    assert response.status_code == status
    assert _actions(db) == audit_before


def test_slip_and_new_scope_are_written_then_proposed(
    client: TestClient, realloc: ReallocateWorkflows, db: Session
) -> None:
    hours_before = db.get_one(Task, 12).most_likely_hours
    slip = _disrupt(client, realloc, {"type": "slip", "task_id": 12, "extra_hours": 16})
    db.expire_all()
    assert db.get_one(Task, 12).most_likely_hours == hours_before + 16
    assert "Task 12 needs 16 more hours." in slip["proposal"]["summary"]
    assert all("critical_slip" in i["reasons"] for i in slip["proposal"]["items"])
    _decide(client, realloc, slip["thread_id"], {"action": "reject", "reason": "keep owners"})

    scope = _disrupt(
        client,
        realloc,
        {
            "type": "scope_add",
            "task": {
                "epic_id": 3,
                "title": "UPI refund flow",
                "optimistic_hours": 8,
                "most_likely_hours": 12,
                "pessimistic_hours": 20,
                "required_skills": [{"skill": "payments", "level": 3}],
            },
            "predecessors": [12],
        },
    )
    db.expire_all()
    new_task = db.scalars(select(Task).where(Task.title == "UPI refund flow")).one()
    assert db.scalar(
        select(func.count()).where(
            Dependency.pred_task_id == 12, Dependency.succ_task_id == new_task.id
        )
    )
    [item] = [i for i in scope["proposal"]["items"] if i["task_id"] == new_task.id]
    assert item["reasons"] == ["new_scope"]
    assert item["before"]["member_id"] is None
    assert item["after"]["member_id"] is not None  # someone on the team has payments >= 2
    assert _actions(db)[-3:].count("disruption.scope_add") == 1


def _advance(client: TestClient, days: int) -> dict:
    response = client.post("/projects/1/simulate/advance", params={"days": days})
    assert response.status_code == 200, response.text
    body: dict = response.json()
    return body


def _progress(db: Session) -> tuple[list[tuple], list[tuple]]:
    db.expire_all()
    snaps = db.execute(
        select(Snapshot.date, Snapshot.pv, Snapshot.ev, Snapshot.ac).order_by(Snapshot.date)
    ).all()
    tasks = db.execute(
        select(Task.id, Task.percent_complete, Task.actual_hours, Task.status).order_by(Task.id)
    ).all()
    return [tuple(r) for r in snaps], [tuple(r) for r in tasks]


def test_advance_is_deterministic_and_moves_the_clock(client: TestClient, db: Session) -> None:
    _seed(db)
    one_jump = _advance(client, 14)
    after_14 = _progress(db)

    assert (one_jump["from_date"], one_jump["to_date"], one_jump["working_days"]) == (
        "2026-11-06",
        "2026-11-20",
        10,
    )
    snapshots = {s[0]: s for s in after_14[0]}
    assert len([d for d in snapshots if d > TODAY]) == 10
    assert all(isinstance(s[2], Decimal) for s in after_14[0])
    assert client.get("/projects/1").json()["sim_date"] == "2026-11-20"
    assert client.get("/projects/1/evm").json()["as_of"] == "2026-11-20"  # follows the clock
    assert "simulation.advance" in _actions(db)

    _seed(db)  # same start again, but in two steps
    _advance(client, 7)
    two_steps = _advance(client, 7)

    assert two_steps["to_date"] == "2026-11-20"
    assert _progress(db) == after_14
    assert (two_steps["spi"], two_steps["cpi"]) == (one_jump["spi"], one_jump["cpi"])


def test_advance_validates_days_and_project(client: TestClient, db: Session) -> None:
    _seed(db)
    assert client.post("/projects/1/simulate/advance", params={"days": 0}).status_code == 422
    assert client.post("/projects/1/simulate/advance", params={"days": 91}).status_code == 422
    assert client.post("/projects/999/simulate/advance", params={"days": 1}).status_code == 404
    assert client.get("/projects/999/audit").status_code == 404
