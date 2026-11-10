import re

from app.config import Settings
from app.main import create_app

OPERATION_ID = re.compile(r"^[a-z]+_[a-z_]+$")


def test_operation_ids_are_clean_and_unique() -> None:
    spec = create_app(Settings(_env_file=None)).openapi()  # type: ignore[call-arg]
    ids = [op["operationId"] for path in spec["paths"].values() for op in path.values()]

    assert len(ids) == len(set(ids))
    assert all(OPERATION_ID.match(i) for i in ids), ids
    assert {"projects_list", "projects_get_full", "dependencies_create", "skills_delete"} <= set(
        ids
    )


def test_error_responses_are_documented() -> None:
    spec = create_app(Settings(_env_file=None)).openapi()  # type: ignore[call-arg]
    create_dep = spec["paths"]["/projects/{project_id}/dependencies"]["post"]["responses"]

    assert create_dep["409"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }


def test_pm_actions_take_the_actor_from_the_x_actor_header() -> None:
    spec = create_app(Settings(_env_file=None)).openapi()  # type: ignore[call-arg]
    pm_actions = [
        ("/projects/{project_id}/disruptions", "post"),
        ("/workflows/{thread_id}/resume", "post"),
        ("/projects/{project_id}/assignments/apply", "post"),
        ("/projects/{project_id}/simulate/advance", "post"),
        ("/projects/{project_id}/risks/{risk_id}/plan", "post"),
    ]
    for path, method in pm_actions:
        params = spec["paths"][path][method].get("parameters", [])
        [header] = [p for p in params if p["in"] == "header" and p["name"] == "X-Actor"]
        assert header["required"] is False
        assert header["schema"]["default"] == "PM"
        assert not any(p["name"] == "actor" for p in params)
    schemas = spec["components"]["schemas"]
    for body in ("ApplyRequest", "ApproveDecision", "RejectDecision", "LeaveDisruption"):
        assert "actor" not in schemas[body]["properties"], body


def test_step_24_read_endpoints_are_documented() -> None:
    spec = create_app(Settings(_env_file=None)).openapi()  # type: ignore[call-arg]
    paths = spec["paths"]

    detail = paths["/projects/{project_id}/proposals/{thread_id}"]["get"]
    assert detail["operationId"] == "reallocation_get_proposal"
    assert {"200", "404"} <= set(detail["responses"])
    metrics = paths["/projects/{project_id}/metrics"]["get"]
    assert metrics["operationId"] == "metrics_get"
    assert "summary" in spec["components"]["schemas"]["AuditRead"]["required"]
