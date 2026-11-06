"""LLM client tests. Fixture mode only; no network and no API key needed."""

import json
import logging
import shutil
from pathlib import Path

import pytest

from app.agents.llm import (
    FixtureNotFoundError,
    LLMClient,
    LLMConfigError,
    LLMResponseError,
    accepts_temperature,
    fixture_path,
    prompt_hash,
)
from app.agents.prompts import PromptNotFoundError, load_prompt
from app.config import Settings
from tests.agents.dummy import (
    FIXTURES_DIR,
    PROMPT_NAME,
    PROMPTS_DIR,
    DummyVerdict,
    dummy_prompt,
)


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, llm_mode="fixture", **overrides)  # type: ignore[call-arg]


def _client(fixtures_dir: Path = FIXTURES_DIR, **overrides: object) -> LLMClient:
    return LLMClient(_settings(**overrides), fixtures_dir=fixtures_dir)


def test_fixture_mode_replays_committed_response() -> None:
    client = _client()

    verdict = client.generate_structured(PROMPT_NAME, dummy_prompt(), DummyVerdict)

    assert verdict == DummyVerdict(
        label="high", reasons=["Critical path task", "Single owner with UPI experience"]
    )
    assert client._client is None  # never built a Gemini client


def test_missing_fixture_names_the_expected_file() -> None:
    changed_prompt = dummy_prompt(task="T-099 Something new")
    expected = fixture_path(
        FIXTURES_DIR, PROMPT_NAME, prompt_hash(PROMPT_NAME, changed_prompt, DummyVerdict)
    )

    with pytest.raises(FixtureNotFoundError) as exc_info:
        _client().generate_structured(PROMPT_NAME, changed_prompt, DummyVerdict)

    assert str(expected) in str(exc_info.value)
    assert "LLM_MODE=record" in str(exc_info.value)


def test_fixture_that_breaks_the_schema_is_rejected(tmp_path: Path) -> None:
    source = fixture_path(
        FIXTURES_DIR, PROMPT_NAME, prompt_hash(PROMPT_NAME, dummy_prompt(), DummyVerdict)
    )
    broken = tmp_path / source.name
    shutil.copy(source, broken)
    data = json.loads(broken.read_text())
    data["response_json"] = {"label": "medium", "reasons": []}
    broken.write_text(json.dumps(data))

    with pytest.raises(LLMResponseError, match="does not match DummyVerdict"):
        _client(fixtures_dir=tmp_path).generate_structured(
            PROMPT_NAME, dummy_prompt(), DummyVerdict
        )


def test_hash_depends_on_prompt_and_schema_but_not_model() -> None:
    class OtherSchema(DummyVerdict):
        confidence: float

    base = prompt_hash(PROMPT_NAME, dummy_prompt(), DummyVerdict)

    assert base == prompt_hash(PROMPT_NAME, dummy_prompt(), DummyVerdict)
    assert base != prompt_hash(PROMPT_NAME, dummy_prompt("T-001 Other"), DummyVerdict)
    assert base != prompt_hash(PROMPT_NAME, dummy_prompt(), OtherSchema)
    # Same fixture replays whatever GEMINI_MODEL is configured.
    replayed = _client(gemini_model="gemini-3.8-flash").generate_structured(
        PROMPT_NAME, dummy_prompt(), DummyVerdict
    )
    assert replayed.label == "high"


def test_logs_call_metadata_but_never_the_api_key(caplog: pytest.LogCaptureFixture) -> None:
    client = _client(gemini_api_key="sk-test-do-not-log-123")

    with caplog.at_level(logging.INFO, logger="app.agents.llm"):
        client.generate_structured(PROMPT_NAME, dummy_prompt(), DummyVerdict)

    text = caplog.text
    assert f"prompt={PROMPT_NAME}" in text
    assert "model=hand-written-test-fixture" in text
    assert "latency_ms=" in text
    assert "input_tokens=42 output_tokens=17" in text
    assert "sk-test-do-not-log-123" not in text


def test_live_mode_without_key_fails_fast_without_network() -> None:
    client = LLMClient(_settings(), mode="live")

    with pytest.raises(LLMConfigError, match="GEMINI_API_KEY"):
        client.generate_structured(PROMPT_NAME, dummy_prompt(), DummyVerdict)


def test_rejects_prompt_names_that_could_escape_the_fixture_dir() -> None:
    with pytest.raises(ValueError, match="invalid prompt_name"):
        _client().generate_structured("../etc/passwd", "x", DummyVerdict)


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("gemini-3.1-flash-lite", True),
        ("gemini-3.5-flash-lite", True),
        ("gemini-3.6-flash", False),
        ("gemini-3.8-flash", False),
        ("gemini-4-argon", False),
        ("some-tuned-model", True),
    ],
)
def test_temperature_only_sent_to_models_that_honour_it(model: str, expected: bool) -> None:
    assert accepts_temperature(model) is expected


def test_load_prompt_substitutes_and_validates() -> None:
    text = load_prompt(PROMPT_NAME, prompts_dir=PROMPTS_DIR, task="T-007 Menu API")

    assert "Task: T-007 Menu API" in text
    assert '{"label": "low" | "high"' in text  # literal JSON braces survive
    with pytest.raises(KeyError):
        load_prompt(PROMPT_NAME, prompts_dir=PROMPTS_DIR)
    with pytest.raises(PromptNotFoundError):
        load_prompt("does_not_exist", prompts_dir=PROMPTS_DIR)
    with pytest.raises(ValueError, match="invalid prompt name"):
        load_prompt("../secrets", prompts_dir=PROMPTS_DIR)
