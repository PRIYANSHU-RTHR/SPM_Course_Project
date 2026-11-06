"""GET /projects/{id}/estimate (needs Postgres; skipped otherwise)."""

import pytest
from sqlalchemy.orm import Session

from app.models import Task
from tests.routers.conftest import Client, make_project


def _project(s: Session, *three_points: tuple[float, float, float]) -> int:
    project, epic = make_project(s)
    for i, (o, m, p) in enumerate(three_points):
        Task(
            project=project,
            epic=epic,
            title=f"Task {i}",
            optimistic_hours=o,
            most_likely_hours=m,
            pessimistic_hours=p,
        )
    s.commit()
    return project.id


def test_estimate_returns_pert_totals_and_cocomo(client: Client) -> None:
    http, factory = client
    with factory() as s:
        pid = _project(s, (2, 4, 12), (4, 6, 8))

    body = http.get(f"/projects/{pid}/estimate").json()

    assert body["task_count"] == 2
    assert body["total_te_hours"] == pytest.approx(11.0)
    assert body["total_std_hours"] == pytest.approx((116 / 36) ** 0.5)
    assert body["total_effort_pm"] == pytest.approx(11 / 152)
    assert [t["te_hours"] for t in body["tasks"]] == pytest.approx([5.0, 6.0])
    assert body["cocomo"]["ksloc"] == pytest.approx(0.11)  # 11 h * 10 LOC/h


def test_estimate_without_tasks_has_no_cocomo(client: Client) -> None:
    http, factory = client
    with factory() as s:
        pid = _project(s)

    body = http.get(f"/projects/{pid}/estimate").json()

    assert body["task_count"] == 0
    assert body["cocomo"] is None


def test_estimate_unknown_project_is_404(client: Client) -> None:
    http, _ = client
    response = http.get("/projects/999/estimate")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
