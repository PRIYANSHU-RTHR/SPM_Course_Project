"""GET /projects/{id}/forecast (needs Postgres; skipped otherwise)."""

from datetime import date

from sqlalchemy.orm import Session

from app.models import Project, Task
from tests.routers.helpers import Client, make_project


def _seed(s: Session) -> int:
    """One fixed 16 h task starting Monday; deadline Tuesday = 16 working hours."""
    project, epic = make_project(s)
    project.start_date, project.deadline = date(2026, 11, 9), date(2026, 11, 10)
    project.sim_date = date(2026, 11, 9)  # the clock at the start: nothing late yet
    Task(
        project=project,
        epic=epic,
        title="Checkout flow",
        optimistic_hours=16,
        most_likely_hours=16,
        pessimistic_hours=16,
    )
    s.add_all(project.tasks)  # SQLAlchemy 2.x: backrefs don't add to the session
    s.commit()
    return project.id


def test_forecast_converts_deadline_and_percentiles_to_dates(api: Client) -> None:
    http, factory = api
    with factory() as s:
        pid = _seed(s)

    body = http.get(f"/projects/{pid}/forecast?n=200").json()

    assert body["runs"] == 200
    assert body["deadline_hours"] == 16
    assert body["p_on_time"] == 1.0
    assert body["p95"] == {"hours": 16, "on": "2026-11-10"}
    assert (body["as_of"], body["resource_shift_hours"]) == ("2026-11-09", 0)


def test_forecast_moves_with_the_project_clock(api: Client) -> None:
    """A day passes with no progress: the remaining 16 h now end a day later, past the deadline."""
    http, factory = api
    with factory() as s:
        pid = _seed(s)
        s.get_one(Project, pid).sim_date = date(2026, 11, 10)
        s.commit()

    body = http.get(f"/projects/{pid}/forecast?n=200").json()

    assert body["resource_shift_hours"] == 8
    assert body["p_on_time"] == 0.0
    assert body["p95"] == {"hours": 24, "on": "2026-11-11"}


def test_forecast_rejects_too_few_runs(api: Client) -> None:
    http, factory = api
    with factory() as s:
        pid = _seed(s)

    assert http.get(f"/projects/{pid}/forecast?n=5").status_code == 422


def test_forecast_unknown_project_is_404(api: Client) -> None:
    http, _ = api
    assert http.get("/projects/999/forecast").status_code == 404
