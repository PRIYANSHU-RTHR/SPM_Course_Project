"""GET /projects/{id}/risks and POST /projects/{id}/risks/refresh (needs Postgres)."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Risk, RiskCategory, RiskStatus
from tests.routers.helpers import (
    create_epic,
    create_member,
    create_project,
    create_skill,
    create_task,
)

START = "2026-11-02"
BEFORE_START = "2026-10-30"  # nothing planned yet: isolates the rules a test targets
WORK = [{"kind": "work", "start_date": START, "end_date": "2027-01-29", "hours_per_week": 40}]


def _project_with_skill_gap(client: TestClient) -> tuple[int, int, int]:
    """One task needs python 4; the only member knows react. Returns (project, task, member)."""
    python = create_skill(client, "python")
    react = create_skill(client, "react")
    project = create_project(client)
    epic = create_epic(client, project["id"])
    task = create_task(
        client,
        project["id"],
        epic["id"],
        "Payment API",
        required_skills=[{"skill": "python", "level": 4, "must": True}],
    )
    member = create_member(
        client, skills=[{"skill_id": react["id"], "level": 4}], availability=WORK
    )
    assert python["id"]
    return project["id"], task["id"], member["id"]


def _refresh(client: TestClient, project_id: int) -> dict:
    response = client.post(f"/projects/{project_id}/risks/refresh", params={"as_of": BEFORE_START})
    assert response.status_code == 200, response.text
    body: dict = response.json()
    return body


def _counts(db: Session) -> tuple[int, int]:
    risks = db.scalar(select(func.count()).select_from(Risk)) or 0
    audits = db.scalar(select(func.count()).select_from(AuditLog)) or 0
    return risks, audits


def test_refresh_is_idempotent(client: TestClient, db: Session) -> None:
    project_id, task_id, _ = _project_with_skill_gap(client)

    first = _refresh(client, project_id)
    after_first = _counts(db)
    second = _refresh(client, project_id)

    assert len(first["opened"]) == 1
    assert first["open_total"] == 1
    assert (second["opened"], second["reopened"], second["updated"], second["closed"]) == (
        [],
        [],
        [],
        [],
    )
    assert _counts(db) == after_first == (1, 1)  # no duplicate risk, no extra audit row

    [risk] = client.get(f"/projects/{project_id}/risks").json()["items"]
    assert (risk["rule_key"], risk["subject_ref"], risk["status"]) == (
        "skill_gap",
        f"task:{task_id}",
        "open",
    )
    assert risk["score"] == risk["probability"] * risk["impact"] == 25
    assert risk["evidence"]["must_skills"] == "python>=4"


def test_rule_that_stops_firing_is_closed_then_reopened(client: TestClient, db: Session) -> None:
    project_id, _, member_id = _project_with_skill_gap(client)
    python_id = client.get("/skills").json()["items"][0]["id"]
    gap_id = _refresh(client, project_id)["opened"][0]

    # Give the member the skill: no gap any more (but now a one-person critical task).
    client.put(
        f"/members/{member_id}/skills", json={"skills": [{"skill_id": python_id, "level": 4}]}
    )
    closing = _refresh(client, project_id)

    assert closing["closed"] == [gap_id]
    open_rules = [
        r["rule_key"] for r in client.get(f"/projects/{project_id}/risks").json()["items"]
    ]
    assert open_rules == ["bus_factor"]
    with_closed = client.get(f"/projects/{project_id}/risks", params={"include_closed": True})
    statuses = {r["id"]: r["status"] for r in with_closed.json()["items"]}
    assert statuses[gap_id] == "closed"  # history kept

    closed_audit = db.scalars(
        select(AuditLog).where(AuditLog.action == "risk_closed", AuditLog.entity_id == gap_id)
    ).one()
    assert closed_audit.actor == "system:risk-engine"
    assert closed_audit.before is not None
    assert closed_audit.before["status"] == "open"
    assert closed_audit.after is not None
    assert closed_audit.after["status"] == "closed"

    # Take the skill away again: the same row comes back.
    client.put(f"/members/{member_id}/skills", json={"skills": []})
    reopening = _refresh(client, project_id)

    assert reopening["reopened"] == [gap_id]
    assert reopening["opened"] == []
    actions = db.scalars(
        select(AuditLog.action).where(AuditLog.entity_id == gap_id).order_by(AuditLog.id)
    ).all()
    assert actions == ["risk_opened", "risk_closed", "risk_reopened"]


def test_list_is_sorted_by_score(client: TestClient, db: Session) -> None:
    project_id = create_project(client)["id"]
    for key, p, i in [("a", 2, 2), ("b", 5, 4), ("c", 3, 3), ("d", 4, 5)]:
        db.add(
            Risk(
                project_id=project_id,
                rule_key=key,
                subject_ref="project",
                title=key,
                category=RiskCategory.SCHEDULE,
                probability=p,
                impact=i,
                status=RiskStatus.OPEN,
            )
        )
    db.commit()

    items = client.get(f"/projects/{project_id}/risks").json()["items"]

    assert [(r["rule_key"], r["score"]) for r in items] == [
        ("b", 20),
        ("d", 20),
        ("c", 9),
        ("a", 4),
    ]


def test_unknown_project_is_404(client: TestClient) -> None:
    assert client.get("/projects/999/risks").status_code == 404
    refresh = client.post("/projects/999/risks/refresh")
    assert refresh.status_code == 404
    assert refresh.json()["error"]["code"] == "not_found"
