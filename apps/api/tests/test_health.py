from fastapi.testclient import TestClient

from app import __version__
from app.config import Settings
from app.errors import NotFoundError
from app.main import create_app


def _client(**overrides: object) -> TestClient:
    settings = Settings(_env_file=None, **overrides)  # type: ignore[call-arg]
    return TestClient(create_app(settings))


def test_health_returns_ok_and_version() -> None:
    response = _client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_cors_allows_configured_origin() -> None:
    client = _client(cors_origins="http://localhost:5173, http://example.test")

    response = client.get("/health", headers={"Origin": "http://example.test"})

    assert response.headers["access-control-allow-origin"] == "http://example.test"


def test_cors_rejects_unknown_origin() -> None:
    response = _client().get("/health", headers={"Origin": "http://evil.test"})

    assert "access-control-allow-origin" not in response.headers


def test_domain_error_is_mapped_to_json() -> None:
    app = create_app(Settings(_env_file=None))  # type: ignore[call-arg]

    @app.get("/boom")
    def boom() -> None:
        raise NotFoundError("Project 7 not found", details={"project_id": 7})

    response = TestClient(app).get("/boom")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Project 7 not found",
            "details": {"project_id": 7},
        }
    }


def test_blank_gemini_values_are_treated_as_unset() -> None:
    settings = Settings(_env_file=None, gemini_api_key="", gemini_model="  ")  # type: ignore[call-arg]

    assert settings.gemini_api_key is None
    assert settings.gemini_model is None
    assert settings.llm_mode == "fixture"
