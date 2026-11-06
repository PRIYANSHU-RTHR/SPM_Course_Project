"""Tiny schema + prompt used to exercise the LLM client. The fixture next to it is committed."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.prompts import load_prompt

TEST_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
FIXTURES_DIR = TEST_FIXTURES / "llm"
PROMPTS_DIR = TEST_FIXTURES / "prompts"
PROMPT_NAME = "dummy_risk"


class DummyVerdict(BaseModel):
    label: Literal["low", "high"]
    reasons: list[str] = Field(min_length=1)


def dummy_prompt(task: str = "T-014 Integrate UPI payment gateway") -> str:
    return load_prompt(PROMPT_NAME, prompts_dir=PROMPTS_DIR, task=task)
