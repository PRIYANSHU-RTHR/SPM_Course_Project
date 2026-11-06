from fastapi.testclient import TestClient

from tests.routers.helpers import create_epic, create_project, create_skill, create_task


def test_task_crud_and_epic_filter(client: TestClient) -> None:
    project = create_project(client)
    create_skill(client, "React")  # normalised to "react"
    ordering = create_epic(client, project["id"], "Ordering")
    payments = create_epic(client, project["id"], "Payments")
    menu = create_task(
        client,
        project["id"],
        ordering["id"],
        "Menu screen",
        priority=2,
        required_skills=[{"skill": " React ", "level": 3, "must": True}],
    )
    create_task(client, project["id"], payments["id"], "UPI checkout")

    assert menu["status"] == "todo"
    assert menu["required_skills"] == [{"skill": "react", "level": 3, "must": True}]

    only_ordering = client.get(
        f"/projects/{project['id']}/tasks", params={"epic_id": ordering["id"]}
    ).json()
    assert only_ordering["total"] == 1
    assert only_ordering["items"][0]["title"] == "Menu screen"

    updated = client.patch(
        f"/tasks/{menu['id']}",
        json={"status": "in_progress", "percent_complete": 40, "actual_hours": 3.5},
    ).json()
    assert (updated["status"], updated["percent_complete"], updated["actual_hours"]) == (
        "in_progress",
        40,
        3.5,
    )

    assert client.delete(f"/tasks/{menu['id']}").status_code == 204
    assert client.get(f"/tasks/{menu['id']}").status_code == 404


def test_task_validation_failures(client: TestClient) -> None:
    project = create_project(client)
    other = create_project(client, name="Library Seat Booking")
    epic = create_epic(client, project["id"])
    foreign_epic = create_epic(client, other["id"])
    url = f"/projects/{project['id']}/tasks"
    base = {"epic_id": epic["id"], "title": "Cart API"}

    bad_order = client.post(
        url,
        json={**base, "optimistic_hours": 8, "most_likely_hours": 6, "pessimistic_hours": 10},
    )
    assert bad_order.status_code == 422

    estimates = {"optimistic_hours": 4, "most_likely_hours": 6, "pessimistic_hours": 10}
    unknown_skill = client.post(
        url,
        json={**base, **estimates, "required_skills": [{"skill": "cobol", "level": 2}]},
    )
    assert unknown_skill.status_code == 422
    assert unknown_skill.json()["error"]["details"] == {"unknown_skills": ["cobol"]}

    wrong_epic = client.post(url, json={**base, **estimates, "epic_id": foreign_epic["id"]})
    assert wrong_epic.status_code == 422

    # PATCH that breaks o <= m <= p against the stored values.
    task = create_task(client, project["id"], epic["id"], "Cart API")
    patched = client.patch(f"/tasks/{task['id']}", json={"most_likely_hours": 20})
    assert patched.status_code == 422
    assert client.get(f"/tasks/{task['id']}").json()["most_likely_hours"] == 6
