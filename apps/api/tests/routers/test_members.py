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


def test_member_with_skills_and_availability(client: TestClient) -> None:
    python = create_skill(client, "python")
    react = create_skill(client, "react")
    member = create_member(
        client,
        email="aditi@campus.test",
        skills=[{"skill_id": python["id"], "level": 4}],
        availability=[
            {
                "kind": "work",
                "start_date": "2026-11-02",
                "end_date": "2027-01-29",
                "hours_per_week": 30,
            }
        ],
    )
    assert member["skills"] == [{"skill_id": python["id"], "skill": "python", "level": 4}]
    assert member["availability"][0]["hours_per_week"] == 30

    replaced = client.put(
        f"/members/{member['id']}/skills",
        json={
            "skills": [
                {"skill_id": python["id"], "level": 5},
                {"skill_id": react["id"], "level": 2},
            ]
        },
    ).json()
    assert [(s["skill"], s["level"]) for s in replaced["skills"]] == [("python", 5), ("react", 2)]

    with_leave = client.post(
        f"/members/{member['id']}/availability",
        json={"kind": "leave", "start_date": "2026-12-14", "end_date": "2026-12-23"},
    )
    assert with_leave.status_code == 201
    leave = with_leave.json()["availability"][1]
    assert (leave["kind"], leave["hours_per_week"]) == ("leave", 0)

    assert client.patch(f"/members/{member['id']}", json={"role": "Tech Lead"}).status_code == 200
    page = client.get("/members").json()
    assert page["total"] == 1
    assert page["items"][0]["role"] == "Tech Lead"

    deleted = client.delete(f"/members/{member['id']}/availability/{leave['id']}")
    assert deleted.status_code == 204
    assert client.delete(f"/members/{member['id']}").status_code == 204


def test_member_failures(client: TestClient) -> None:
    create_member(client, email="ravi@campus.test")

    duplicate = client.post(
        "/members", json={"name": "Ravi K", "role": "Frontend", "email": "ravi@campus.test"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["details"] == {"constraint": "uq_member_email"}

    unknown_skill = client.post(
        "/members", json={"name": "Eva", "role": "QA", "skills": [{"skill_id": 99, "level": 3}]}
    )
    assert unknown_skill.status_code == 422

    leave_with_hours = client.post(
        "/members",
        json={
            "name": "Eva",
            "role": "QA",
            "availability": [
                {
                    "kind": "leave",
                    "start_date": "2026-12-01",
                    "end_date": "2026-12-05",
                    "hours_per_week": 10,
                }
            ],
        },
    )
    assert leave_with_hours.status_code == 422
    assert client.get("/members/999").status_code == 404


def test_member_with_assignment_history_cannot_be_deleted(client: TestClient, db: Session) -> None:
    project = create_project(client)
    epic = create_epic(client, project["id"])
    task = create_task(client, project["id"], epic["id"], "Menu API")
    member = create_member(client)
    db.add(Assignment(task_id=task["id"], member_id=member["id"], source=AssignmentSource.AI))
    db.commit()

    response = client.delete(f"/members/{member['id']}")

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "conflict",
        "message": "The member has assignment history and cannot be deleted",
        "details": {"constraint": "fk_assignment_member_id_member"},
    }
