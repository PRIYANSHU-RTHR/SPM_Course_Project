"""GET /projects/{id}/cpm (needs Postgres; skipped otherwise)."""

from sqlalchemy.orm import Session

from app.models import Dependency, Task
from tests.routers.helpers import Client, make_project


def _network(s: Session, hours: list[float], edges: list[tuple[int, int]]) -> tuple[int, list[int]]:
    """Tasks with o=m=p=hours (so te = hours); edges are (pred index, succ index)."""
    project, epic = make_project(s)
    tasks = [
        Task(
            project=project,
            epic=epic,
            title=f"T{i}",
            optimistic_hours=h,
            most_likely_hours=h,
            pessimistic_hours=h,
        )
        for i, h in enumerate(hours)
    ]
    s.add_all(project.tasks)  # SQLAlchemy 2.x: backrefs don't add to the session
    s.flush()
    s.add_all(Dependency(pred_task_id=tasks[a].id, succ_task_id=tasks[b].id) for a, b in edges)
    s.commit()
    return project.id, [t.id for t in tasks]


def test_cpm_returns_schedule_and_critical_path(api: Client) -> None:
    http, factory = api
    with factory() as s:
        pid, ids = _network(s, [3, 2, 4], [(0, 1)])  # T0 -> T1, T2 alone

    body = http.get(f"/projects/{pid}/cpm").json()

    assert body["project_duration_hours"] == 5
    assert body["critical_paths"] == [[ids[0], ids[1]]]
    t2 = next(t for t in body["tasks"] if t["task_id"] == ids[2])
    assert (t2["total_slack"], t2["critical"]) == (1, False)


def test_cpm_cycle_is_409_with_path(api: Client) -> None:
    http, factory = api
    with factory() as s:
        pid, ids = _network(s, [1, 1], [(0, 1), (1, 0)])

    response = http.get(f"/projects/{pid}/cpm")

    assert response.status_code == 409
    cycle = response.json()["error"]["details"]["cycle"]
    assert cycle[0] == cycle[-1]
    assert set(cycle) == set(ids)


def test_cpm_unknown_project_is_404(api: Client) -> None:
    http, _ = api
    assert http.get("/projects/999/cpm").status_code == 404
