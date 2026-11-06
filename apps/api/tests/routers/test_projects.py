from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Assignment, AssignmentSource
from tests.routers.helpers import (
    create_epic,
    create_member,
    create_project,
    create_skill,
    create_task,
)


def test_project_crud_and_pagination(client: TestClient) -> None:
    first = create_project(client)
    create_project(client, name="Library Seat Booking")
    create_project(client, name="Hostel Complaints Portal")

    assert first["budget"] == "850000.00"  # money stays an exact decimal string
    assert client.get(f"/projects/{first['id']}").json()["name"] == "Campus Food-Ordering App"

    page = client.get("/projects", params={"limit": 2, "offset": 1}).json()
    assert page["total"] == 3
    assert page["limit"] == 2
    assert page["offset"] == 1
    assert [p["name"] for p in page["items"]] == [
        "Library Seat Booking",
        "Hostel Complaints Portal",
    ]

    updated = client.patch(f"/projects/{first['id']}", json={"deadline": "2027-02-12"})
    assert updated.status_code == 200
    assert updated.json()["deadline"] == "2027-02-12"

    assert client.delete(f"/projects/{first['id']}").status_code == 204
    assert client.get("/projects").json()["total"] == 2


def test_project_full_returns_whole_plan(client: TestClient, db: Session) -> None:
    project = create_project(client)
    create_skill(client, "python")
    epic = create_epic(client, project["id"])
    api = create_task(
        client,
        project["id"],
        epic["id"],
        "Menu API",
        required_skills=[{"skill": "python", "level": 3, "must": True}],
    )
    ui = create_task(client, project["id"], epic["id"], "Menu screen")
    client.post(
        f"/projects/{project['id']}/dependencies",
        json={"pred_task_id": api["id"], "succ_task_id": ui["id"]},
    )
    member = create_member(client)
    db.add_all(
        [
            Assignment(
                task_id=api["id"],
                member_id=member["id"],
                source=AssignmentSource.AI,
                is_current=False,
            ),
            Assignment(
                task_id=api["id"],
                member_id=member["id"],
                source=AssignmentSource.PM_OVERRIDE,
                reason="Owns the menu service",
                is_current=True,
            ),
        ]
    )
    db.commit()

    full = client.get(f"/projects/{project['id']}/full")

    assert full.status_code == 200
    body = full.json()
    assert body["project"]["id"] == project["id"]
    assert [e["title"] for e in body["epics"]] == ["Ordering"]
    assert [t["title"] for t in body["tasks"]] == ["Menu API", "Menu screen"]
    assert body["tasks"][0]["required_skills"] == [{"skill": "python", "level": 3, "must": True}]
    assert [(d["pred_task_id"], d["succ_task_id"]) for d in body["dependencies"]] == [
        (api["id"], ui["id"])
    ]
    assert len(body["assignments"]) == 1  # current only
    assert body["assignments"][0]["source"] == "pm_override"


def test_missing_project_is_404_with_error_body(client: TestClient) -> None:
    response = client.get("/projects/999/full")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Project 999 not found", "details": {"id": 999}}
    }


def test_invalid_project_is_422(client: TestClient) -> None:
    response = client.post(
        "/projects",
        json={
            "name": "Backwards",
            "start_date": "2027-01-01",
            "deadline": "2026-12-01",
            "budget": "1000",
            "hourly_rate": "100",
        },
    )
    assert response.status_code == 422

    project = create_project(client)
    patched = client.patch(f"/projects/{project['id']}", json={"deadline": "2026-10-01"})
    assert patched.status_code == 422
    assert patched.json()["error"]["code"] == "validation_failed"

    null_name = client.patch(f"/projects/{project['id']}", json={"name": None})
    assert null_name.status_code == 422
