"""Application settings, read from environment variables (and the repo-root `.env` if present)."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _repo_root_env(config_file: Path) -> Path | None:
    """`<repo>/.env` for apps/api/app/config.py (three levels above app/). None when the code
    is installed shallower than that (e.g. /src/app in a container), instead of failing."""
    parents = config_file.resolve().parents
    return parents[3] / ".env" if len(parents) > 3 else None


_REPO_ROOT_ENV = _repo_root_env(Path(__file__))

LlmMode = Literal["live", "record", "fixture"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT_ENV,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://orchestrai:orchestrai@localhost:5432/orchestrai"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    llm_mode: LlmMode = "fixture"
    gemini_model: str | None = None
    gemini_api_key: SecretStr | None = None
    llm_timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    sim_seed: int = 42

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string (`a,b`) as well as a list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("gemini_api_key", "gemini_model", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        """Treat an empty env var (as in `.env.example`) as unset."""
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
