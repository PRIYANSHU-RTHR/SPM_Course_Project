from fastapi.testclient import TestClient

from tests.routers.helpers import create_epic, create_project, create_skill, create_task


def test_skill_crud(client: TestClient) -> None:
    create_skill(client, "Python")
    react = create_skill(client, "react")

    page = client.get("/skills").json()
    assert page["total"] == 2
    assert [s["name"] for s in page["items"]] == ["python", "react"]

    renamed = client.patch(f"/skills/{react['id']}", json={"name": "React Native"})
    assert renamed.json()["name"] == "react native"
    assert client.delete(f"/skills/{react['id']}").status_code == 204


def test_skill_conflicts(client: TestClient) -> None:
    python = create_skill(client, "python")
    assert client.post("/skills", json={"name": "PYTHON"}).status_code == 409

    project = create_project(client)
    epic = create_epic(client, project["id"])
    task = create_task(
        client,
        project["id"],
        epic["id"],
        "Menu API",
        required_skills=[{"skill": "python", "level": 3}],
    )

    in_use = client.delete(f"/skills/{python['id']}")
    assert in_use.status_code == 409
    assert in_use.json()["error"]["details"] == {"task_ids": [task["id"]]}
    assert client.patch(f"/skills/{python['id']}", json={"name": "py"}).status_code == 409
