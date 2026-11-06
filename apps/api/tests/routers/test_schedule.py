"""GET /projects/{id}/schedule (needs Postgres; skipped otherwise)."""

from datetime import date

from sqlalchemy.orm import Session

from app.models import Assignment, AssignmentSource, Availability, AvailabilityKind, Member, Task
from tests.routers.helpers import Client, make_project


def _seed(s: Session, hours_per_week: float) -> tuple[int, list[int]]:
    """Two independent 8 h tasks, both on one member: the second must slip a day."""
    member = Member(name="Kabir Rao", role="Backend developer")
    member.availability = [
        Availability(
            kind=AvailabilityKind.WORK,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 12, 31),
            hours_per_week=hours_per_week,
        )
    ]
    project, epic = make_project(s)
    project.start_date = date(2026, 11, 9)
    tasks = [
        Task(
            project=project,
            epic=epic,
            title=title,
            optimistic_hours=8,
            most_likely_hours=8,
            pessimistic_hours=8,
        )
        for title in ("Menu API", "Cart API")
    ]
    s.add(member)
    s.add_all(project.tasks)  # SQLAlchemy 2.x: backrefs don't add to the session
    s.flush()
    s.add_all(
        Assignment(task_id=t.id, member_id=member.id, source=AssignmentSource.AI) for t in tasks
    )
    s.commit()
    return project.id, [t.id for t in tasks]


def test_schedule_delays_second_task_on_same_member(api: Client) -> None:
    http, factory = api
    with factory() as s:
        pid, tasks = _seed(s, 40)

    body = http.get(f"/projects/{pid}/schedule").json()

    assert [(t["task_id"], t["start"]) for t in body["tasks"]] == [
        (tasks[0], "2026-11-09"),
        (tasks[1], "2026-11-10"),
    ]
    assert body["delayed"] == [tasks[1]]
    assert body["finish"] == "2026-11-10"
    assert body["loads"][0]["hours"] == 16


def test_schedule_zero_capacity_is_422(api: Client) -> None:
    http, factory = api
    with factory() as s:
        pid, _ = _seed(s, 0)

    response = http.get(f"/projects/{pid}/schedule")

    assert response.status_code == 422
    assert "no working capacity" in response.json()["error"]["message"]


def test_schedule_unknown_project_is_404(api: Client) -> None:
    http, _ = api
    assert http.get("/projects/999/schedule").status_code == 404
