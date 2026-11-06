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
