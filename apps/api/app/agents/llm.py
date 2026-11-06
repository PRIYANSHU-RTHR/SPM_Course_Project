"""Gemini client with structured output and record/replay fixtures.

`LLM_MODE`:
- `live`    call Gemini; the reply must be JSON matching the Pydantic schema.
- `record`  like live, then write the reply to `fixtures/llm/<prompt_name>__<hash12>.json`.
- `fixture` never touch the network: replay that file, or fail naming the file it expected.

The fixture key hashes the prompt name, the rendered prompt and the schema's JSON Schema, but
not the model id. Switching `GEMINI_MODEL` keeps replaying old recordings. Changing a prompt
or schema needs a re-record.

The LLM only returns structure and prose. It never computes KPI numbers (see CLAUDE.md).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

from app.config import LlmMode, Settings, get_settings

if TYPE_CHECKING:
    from google import genai

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "llm"

# Transient failures worth retrying. The SDK does the retrying (exponential backoff + jitter).
RETRY_ATTEMPTS = 3  # first try + 2 retries
RETRY_STATUS_CODES = (408, 429, 500, 502, 503, 504)

_PROMPT_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_MODEL_VERSION = re.compile(r"^gemini-(\d+)(?:\.(\d+))?")


class LLMError(RuntimeError):
    """Base class for LLM client failures."""


class LLMConfigError(LLMError):
    """Live/record mode without GEMINI_API_KEY or GEMINI_MODEL."""


class LLMResponseError(LLMError):
    """The model replied, but not with JSON matching the schema."""


class FixtureNotFoundError(LLMError):
    """Fixture mode and no recording exists for this prompt."""


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    thought_tokens: int | None = None


def prompt_hash(prompt_name: str, prompt: str, schema: type[BaseModel]) -> str:
    """Stable sha256 over what determines the reply's shape and content (not the model)."""
    payload = json.dumps(
        {"prompt_name": prompt_name, "prompt": prompt, "schema": schema.model_json_schema()},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fixture_path(fixtures_dir: Path, prompt_name: str, digest: str) -> Path:
    return fixtures_dir / f"{prompt_name}__{digest[:12]}.json"


def accepts_temperature(model: str) -> bool:
    """Gemini 3.6+ and 4.x ignore custom temperature/top_p/top_k; docs say to omit them."""
    match = _MODEL_VERSION.match(model)
    if match is None:
        return True
    major, minor = int(match.group(1)), int(match.group(2) or 0)
    return (major, minor) < (3, 6)


class LLMClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        mode: LlmMode | None = None,
        fixtures_dir: Path = FIXTURES_DIR,
    ) -> None:
        self._settings = settings or get_settings()
        self.mode: LlmMode = mode or self._settings.llm_mode
        self.model = self._settings.gemini_model or "fixture"
        self.fixtures_dir = fixtures_dir
        self._client: genai.Client | None = None

    # -- public -------------------------------------------------------------------------------

    def generate_structured[T: BaseModel](
        self,
        prompt_name: str,
        prompt: str,
        schema: type[T],
        *,
        temperature: float = 0.2,
    ) -> T:
        if not _PROMPT_NAME.match(prompt_name):
            raise ValueError(f"invalid prompt_name {prompt_name!r}")
        digest = prompt_hash(prompt_name, prompt, schema)
        started = time.perf_counter()

        if self.mode == "fixture":
            raw, model, usage = self._load_fixture(prompt_name, digest)
        else:
            raw, model, usage = self._call_gemini(prompt, schema, temperature)

        result = self._validate(prompt_name, raw, schema)
        if self.mode == "record":
            self._save_fixture(prompt_name, digest, model, raw, usage)

        logger.info(
            "llm call prompt=%s mode=%s model=%s hash=%s latency_ms=%d "
            "input_tokens=%s output_tokens=%s thought_tokens=%s",
            prompt_name,
            self.mode,
            model,
            digest[:12],
            (time.perf_counter() - started) * 1000,
            usage.input_tokens,
            usage.output_tokens,
            usage.thought_tokens,
        )
        return result

    # -- fixtures -----------------------------------------------------------------------------

    def _load_fixture(self, prompt_name: str, digest: str) -> tuple[str, str, Usage]:
        path = fixture_path(self.fixtures_dir, prompt_name, digest)
        if not path.is_file():
            raise FixtureNotFoundError(
                f"No LLM fixture for prompt {prompt_name!r}: expected {path}. "
                "Record it with LLM_MODE=record (needs GEMINI_API_KEY), or check that the "
                "prompt text and schema are unchanged since it was recorded."
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        usage = Usage(**data.get("usage", {}))
        return json.dumps(data["response_json"]), data.get("model", "fixture"), usage

    def _save_fixture(
        self, prompt_name: str, digest: str, model: str, raw: str, usage: Usage
    ) -> None:
        path = fixture_path(self.fixtures_dir, prompt_name, digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "prompt_name": prompt_name,
            "model": model,
            "prompt_hash": digest,
            "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "usage": usage.__dict__,
            "response_json": json.loads(raw),
        }
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        logger.info("llm fixture recorded prompt=%s file=%s", prompt_name, path.name)

    # -- live ---------------------------------------------------------------------------------

    def _gemini(self) -> genai.Client:
        if self._client is None:
            key = self._settings.gemini_api_key
            if key is None or not self._settings.gemini_model:
                raise LLMConfigError(
                    f"LLM_MODE={self.mode} needs GEMINI_API_KEY and GEMINI_MODEL; "
                    "use LLM_MODE=fixture to run without them"
                )
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=key.get_secret_value(),
                http_options=types.HttpOptions(
                    timeout=int(self._settings.llm_timeout_seconds * 1000),  # milliseconds
                    retry_options=types.HttpRetryOptions(
                        attempts=RETRY_ATTEMPTS,
                        initial_delay=1.0,
                        max_delay=8.0,
                        exp_base=2.0,
                        jitter=0.5,
                        http_status_codes=list(RETRY_STATUS_CODES),
                    ),
                ),
            )
        return self._client

    def _call_gemini(
        self, prompt: str, schema: type[BaseModel], temperature: float
    ) -> tuple[str, str, Usage]:
        client = self._gemini()
        generation_config: dict[str, Any] = {}
        if accepts_temperature(self.model):
            generation_config["temperature"] = temperature

        interaction = client.interactions.create(
            model=self.model,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": schema.model_json_schema(),
            },
            generation_config=generation_config,
            store=False,  # stateless: don't keep prompts server-side
        )
        usage = getattr(interaction, "usage", None)
        return (
            interaction.output_text or "",
            self.model,
            Usage(
                input_tokens=getattr(usage, "total_input_tokens", None),
                output_tokens=getattr(usage, "total_output_tokens", None),
                thought_tokens=getattr(usage, "total_thought_tokens", None),
            ),
        )

    # -- validation ---------------------------------------------------------------------------

    @staticmethod
    def _validate[T: BaseModel](prompt_name: str, raw: str, schema: type[T]) -> T:
        try:
            return schema.model_validate_json(raw)
        except ValidationError as exc:
            raise LLMResponseError(
                f"LLM reply for {prompt_name!r} does not match {schema.__name__}: "
                f"{exc.error_count()} error(s); first: {exc.errors()[0]['msg']}"
            ) from exc
