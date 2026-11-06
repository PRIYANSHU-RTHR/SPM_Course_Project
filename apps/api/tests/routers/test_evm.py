"""GET /projects/{id}/evm (needs Postgres; skipped otherwise)."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Snapshot, Task
from tests.routers.helpers import Client, make_project


def _seed(s: Session) -> int:
    """One unassigned 40 h task Mon-Fri at INR 800/h: BAC 32,000, PV 6,400 a day."""
    project, epic = make_project(s)
    project.start_date = date(2026, 11, 9)
    Task(
        project=project,
        epic=epic,
        title="Payments integration",
        optimistic_hours=40,
        most_likely_hours=40,
        pessimistic_hours=40,
        percent_complete=25,
        actual_hours=12,
    )
    s.add_all(project.tasks)  # SQLAlchemy 2.x: backrefs don't add to the session
    s.flush()
    s.add(
        Snapshot(
            project_id=project.id,
            date=date(2026, 11, 10),
            pv=Decimal("0"),
            ev=Decimal("6400.00"),
            ac=Decimal("7200.00"),
        )
    )
    s.commit()
    return project.id


def test_evm_metrics_as_of_date(api: Client) -> None:
    http, factory = api
    with factory() as s:
        pid = _seed(s)

    body = http.get(f"/projects/{pid}/evm?as_of=2026-11-10").json()

    # PV = 2 days x 6,400; EV = 25% of 32,000; AC = 12 h x 800
    assert (body["bac"], body["pv"], body["ev"], body["ac"]) == (
        "32000.00",
        "12800.00",
        "8000.00",
        "9600.00",
    )
    assert body["spi"] == 0.625
    assert body["cpi"] == 8000 / 9600
    assert body["snapshots"] == [
        {"on": "2026-11-10", "pv": "12800.00", "ev": "6400.00", "ac": "7200.00"}
    ]
    assert body["planned"][0] == {"on": "2026-11-13", "pv": "32000.00", "ev": None, "ac": None}


def test_evm_before_start_has_null_ratios_with_reasons(api: Client) -> None:
    http, factory = api
    with factory() as s:
        pid = _seed(s)

    body = http.get(f"/projects/{pid}/evm?as_of=2026-11-01").json()

    assert body["pv"] == "0.00"
    assert body["spi"] is None
    assert "PV = 0" in body["notes"]["spi"]


def test_evm_unknown_project_is_404(api: Client) -> None:
    http, _ = api
    assert http.get("/projects/999/evm").status_code == 404
