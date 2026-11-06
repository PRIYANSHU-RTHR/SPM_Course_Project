"""POST /projects/{id}/assignments/recommend and /apply (needs Postgres; skipped otherwise)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    AuditLog,
    Availability,
    AvailabilityKind,
    Member,
    MemberSkill,
    Skill,
    Task,
)
from tests.routers.conftest import Client, make_project


def _seed(s: Session) -> tuple[int, list[int], list[int]]:
    """Same case as the engine test: greedy 177.5 vs optimal 200."""
    python, ml = Skill(name="python"), Skill(name="ml")
    members = []
    for name, levels in (("Aarav Shah", (5, 4)), ("Diya Patel", (3, 1))):
        m = Member(name=name, role="Developer")
        m.skills = [
            MemberSkill(skill=python, level=levels[0]),
            MemberSkill(skill=ml, level=levels[1]),
        ]
        m.availability = [
            Availability(
                kind=AvailabilityKind.WORK,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 12, 31),
                hours_per_week=40,
            )
        ]
        members.append(m)
    project, epic = make_project(s)
    project.start_date = date(2026, 11, 9)  # Monday
    tasks = [
        Task(
            project=project,
            epic=epic,
            title="Order API",
            optimistic_hours=30,
            most_likely_hours=30,
            pessimistic_hours=30,
            priority=1,
            required_skills=[{"skill": "python", "level": 3}],
        ),
        Task(
            project=project,
            epic=epic,
            title="Delivery-time model",
            optimistic_hours=30,
            most_likely_hours=30,
            pessimistic_hours=30,
            priority=2,
            required_skills=[
                {"skill": "python", "level": 3},
                {"skill": "ml", "level": 4, "must": False},
            ],
        ),
    ]
    s.add_all(members)
    s.commit()
    return project.id, [t.id for t in tasks], [m.id for m in members]


def test_recommend_optimal_beats_greedy(client: Client) -> None:
    http, factory = client
    with factory() as s:
        pid, _tasks, members = _seed(s)

    optimal = http.post(f"/projects/{pid}/assignments/recommend?mode=optimal").json()
    greedy = http.post(f"/projects/{pid}/assignments/recommend?mode=greedy").json()

    assert [r["member_id"] for r in optimal["recommendations"]] == [members[1], members[0]]
    assert optimal["total_score"] == 200
    assert greedy["total_score"] == 177.5
    assert optimal["comparison"]["greedy_total"] == 177.5
    rec = optimal["recommendations"][0]
    assert rec["window_start"] == "2026-11-09"
    assert len(rec["candidates"]) == 2


def test_apply_writes_assignment_and_audit_log(client: Client) -> None:
    http, factory = client
    with factory() as s:
        pid, tasks, members = _seed(s)

    first = http.post(
        f"/projects/{pid}/assignments/apply",
        json={"actor": "pm", "items": [{"task_id": tasks[0], "member_id": members[0]}]},
    )
    second = http.post(
        f"/projects/{pid}/assignments/apply",
        json={
            "actor": "pm",
            "items": [
                {
                    "task_id": tasks[0],
                    "member_id": members[1],
                    "source": "pm_override",
                    "reason": "Aarav is on the payments spike",
                }
            ],
        },
    )

    assert first.status_code == 200
    assert second.json()[0]["previous_member_id"] == members[0]
    with factory() as s:
        current = s.scalars(select(Assignment).where(Assignment.is_current)).all()
        assert [(a.task_id, a.member_id) for a in current] == [(tasks[0], members[1])]
        audit = s.scalars(select(AuditLog).order_by(AuditLog.id)).all()
        assert [a.action for a in audit] == ["assignment.ai", "assignment.pm_override"]
        assert audit[1].before == {"task_id": tasks[0], "member_id": members[0]}
        assert audit[1].reason == "Aarav is on the payments spike"


def test_override_without_reason_is_422(client: Client) -> None:
    http, factory = client
    with factory() as s:
        pid, tasks, members = _seed(s)

    response = http.post(
        f"/projects/{pid}/assignments/apply",
        json={
            "actor": "pm",
            "items": [{"task_id": tasks[0], "member_id": members[0], "source": "pm_override"}],
        },
    )
    assert response.status_code == 422


def test_apply_unknown_member_is_404(client: Client) -> None:
    http, factory = client
    with factory() as s:
        pid, tasks, _ = _seed(s)

    response = http.post(
        f"/projects/{pid}/assignments/apply",
        json={"actor": "pm", "items": [{"task_id": tasks[0], "member_id": 999}]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["details"] == {"member_ids": [999]}
