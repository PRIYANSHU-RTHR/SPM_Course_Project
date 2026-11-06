"""Small factories that create rows through the API and return the JSON body."""

from typing import Any

from fastapi.testclient import TestClient

Json = dict[str, Any]


def _ok(response: Any, status: int = 201) -> Json:
    assert response.status_code == status, response.text
    body: Json = response.json()
    return body


def create_project(client: TestClient, **overrides: Any) -> Json:
    body = {
        "name": "Campus Food-Ordering App",
        "brief": "Students order from campus canteens and pick up without queueing.",
        "start_date": "2026-11-02",
        "deadline": "2027-01-29",
        "budget": "850000.00",
        "hourly_rate": "1200.00",
        **overrides,
    }
    return _ok(client.post("/projects", json=body))


def create_epic(client: TestClient, project_id: int, title: str = "Ordering") -> Json:
    return _ok(client.post(f"/projects/{project_id}/epics", json={"title": title}))


def create_skill(client: TestClient, name: str) -> Json:
    return _ok(client.post("/skills", json={"name": name}))


def create_task(
    client: TestClient, project_id: int, epic_id: int, title: str, **overrides: Any
) -> Json:
    body = {
        "epic_id": epic_id,
        "title": title,
        "optimistic_hours": 4,
        "most_likely_hours": 6,
        "pessimistic_hours": 10,
        **overrides,
    }
    return _ok(client.post(f"/projects/{project_id}/tasks", json=body))


def create_member(client: TestClient, name: str = "Aditi Sharma", **overrides: Any) -> Json:
    body = {"name": name, "role": "Backend Engineer", **overrides}
    return _ok(client.post("/members", json=body))
