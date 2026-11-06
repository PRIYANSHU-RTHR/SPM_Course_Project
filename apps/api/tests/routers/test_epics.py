from fastapi.testclient import TestClient

from tests.routers.helpers import create_epic, create_project, create_task


def test_epic_crud(client: TestClient) -> None:
    project = create_project(client)
    ordering = create_epic(client, project["id"], "Ordering")
    payments = create_epic(client, project["id"], "Payments")
    client.patch(f"/epics/{payments['id']}", json={"position": 0})
    client.patch(f"/epics/{ordering['id']}", json={"position": 1, "description": "Cart, menu"})

    page = client.get(f"/projects/{project['id']}/epics").json()
    assert page["total"] == 2
    assert [e["title"] for e in page["items"]] == ["Payments", "Ordering"]  # by position
    assert client.get(f"/epics/{ordering['id']}").json()["description"] == "Cart, menu"

    create_task(client, project["id"], ordering["id"], "Cart API")
    assert client.delete(f"/epics/{ordering['id']}").status_code == 204
    assert client.get(f"/projects/{project['id']}/tasks").json()["total"] == 0  # cascaded


def test_epic_on_missing_project_is_404(client: TestClient) -> None:
    response = client.post("/projects/42/epics", json={"title": "Ordering"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
