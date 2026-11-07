"""GET .../assignments/{task_id}/explain and POST .../risks/{risk_id}/plan (needs Postgres).

No fixtures are recorded for these inputs, so fixture mode falls back to the templates.
"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Risk, RiskCategory
from tests.routers.helpers import (
    create_epic,
    create_member,
    create_project,
    create_skill,
    create_task,
)

WORK = [
    {"kind": "work", "start_date": "2026-11-02", "end_date": "2027-01-29", "hours_per_week": 40}
]


def _project(client: TestClient) -> tuple[int, int, int]:
    payments = create_skill(client, "payments")
    project = create_project(client)
    epic = create_epic(client, project["id"])
    task = create_task(
        client,
        project["id"],
        epic["id"],
        "Integrate UPI payment gateway",
        required_skills=[{"skill": "payments", "level": 4, "must": True}],
    )
    member = create_member(
        client, skills=[{"skill_id": payments["id"], "level": 4}], availability=WORK
    )
    return project["id"], task["id"], member["id"]


def test_explain_returns_grounded_template(client: TestClient) -> None:
    pid, tid, mid = _project(client)

    response = client.get(f"/projects/{pid}/assignments/{tid}/explain")

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["recommended_member_id"], body["source"], body["grounded"]) == (
        mid,
        "template",
        False,
    )
    assert "payments 4/4" in body["text"]


def test_explain_unknown_task_is_404(client: TestClient) -> None:
    pid, _, _ = _project(client)
    assert client.get(f"/projects/{pid}/assignments/999/explain").status_code == 404


def test_risk_plan_is_stored_and_audited(client: TestClient, db: Session) -> None:
    pid, _, _ = _project(client)
    risk = Risk(
        project_id=pid,
        rule_key="spi_low",
        subject_ref="project",
        title="Schedule slipping: SPI 0.82",
        category=RiskCategory.SCHEDULE,
        probability=4,
        impact=4,
        evidence={"spi": 0.82},
    )
    db.add(risk)
    db.commit()

    response = client.post(f"/projects/{pid}/risks/{risk.id}/plan")

    assert response.status_code == 200, response.text
    rmmm = response.json()["rmmm"]
    assert rmmm["source"] == "template"
    assert rmmm["owner_role"] == "Project manager"
    assert "score rises above 16" in rmmm["monitoring_trigger"]
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "risk.plan")).one()
    assert (audit.entity, audit.entity_id) == ("risk", risk.id)


def test_risk_plan_unknown_risk_is_404(client: TestClient) -> None:
    pid, _, _ = _project(client)
    assert client.post(f"/projects/{pid}/risks/999/plan").status_code == 404
