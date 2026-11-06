import httpx
from fastapi.testclient import TestClient

from app.services.dependencies import find_path
from tests.routers.helpers import create_epic, create_project, create_task


def _chain(client: TestClient) -> tuple[int, list[int]]:
    project = create_project(client)
    epic = create_epic(client, project["id"])
    ids = [create_task(client, project["id"], epic["id"], t)["id"] for t in ("A", "B", "C")]
    return project["id"], ids


def _link(client: TestClient, project_id: int, pred: int, succ: int) -> httpx.Response:
    return client.post(
        f"/projects/{project_id}/dependencies", json={"pred_task_id": pred, "succ_task_id": succ}
    )


def test_dependency_create_list_delete(client: TestClient) -> None:
    project_id, (a, b, c) = _chain(client)
    ab = _link(client, project_id, a, b)
    _link(client, project_id, b, c)

    assert ab.status_code == 201
    assert ab.json()["type"] == "FS"
    page = client.get(f"/projects/{project_id}/dependencies").json()
    assert page["total"] == 2

    assert client.delete(f"/dependencies/{ab.json()['id']}").status_code == 204
    assert client.get(f"/projects/{project_id}/dependencies").json()["total"] == 1


def test_cycle_is_409_with_path(client: TestClient) -> None:
    project_id, (a, b, c) = _chain(client)
    _link(client, project_id, a, b)
    _link(client, project_id, b, c)

    response = _link(client, project_id, c, a)

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "conflict"
    assert error["details"] == {"cycle": [c, a, b, c]}
    assert error["message"] == f"Dependency would create a cycle: T-{c} -> T-{a} -> T-{b} -> T-{c}"


def test_duplicate_and_self_dependency_rejected(client: TestClient) -> None:
    project_id, (a, b, _) = _chain(client)
    _link(client, project_id, a, b)

    assert _link(client, project_id, a, b).status_code == 409
    assert _link(client, project_id, a, a).status_code == 422


def test_find_path_handles_diamonds_and_misses() -> None:
    edges = {1: [2, 3], 2: [4], 3: [4], 4: []}

    assert find_path(edges, 1, 4) == [1, 2, 4]
    assert find_path(edges, 4, 1) is None
