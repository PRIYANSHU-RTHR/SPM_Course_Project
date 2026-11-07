"""Explanation agent: why the engine picked this member, in 2-3 sentences.

The model only sees the engine's score breakdowns and may only repeat those numbers. If the
reply names a different member, cites a number that isn't in the facts, or the call fails,
a deterministic template built from the same numbers is used instead.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.grounding import fact_numbers, ungrounded_numbers
from app.agents.llm import LLMClient, LLMError
from app.agents.prompts import load_prompt

PROMPT_NAME = "explanation"


class SkillFact(BaseModel):
    skill: str
    required: int
    has: int
    fit: float


class CandidateFacts(BaseModel):
    member_id: int
    name: str
    total: float = Field(description="score 0-100")
    skill_fit: float
    capacity_fit: float
    balance: float
    skill_part: float
    capacity_part: float
    balance_part: float
    free_hours: float
    skills: list[SkillFact]


class ScoreWeights(BaseModel):
    skill: float = 0.60
    capacity: float = 0.25
    balance: float = 0.15


class ExplanationFacts(BaseModel):
    task_id: int
    title: str
    hours: float
    weights: ScoreWeights = Field(default_factory=ScoreWeights)
    level_max: int = Field(default=5, description="skill levels are 1 to level_max")
    candidates: list[CandidateFacts] = Field(description="Best first, at most 3")


class ExplanationReply(BaseModel):
    recommended_member_id: int
    explanation: str = Field(description="2-3 sentences")
    runner_up_note: str = ""


class Explanation(BaseModel):
    recommended_member_id: int | None
    text: str
    grounded: bool = Field(description="True when the model's text passed the number check")
    source: Literal["model", "template"]
    ungrounded: list[str] = Field(default_factory=list, description="Numbers that failed")


def template(facts: ExplanationFacts) -> str:
    if not facts.candidates:
        return f"Nobody is eligible for {facts.title!r} yet."
    best = facts.candidates[0]
    skills = ", ".join(f"{s.skill} {s.has}/{s.required}" for s in best.skills)
    text = (
        f"{best.name} scores {best.total:.1f}: skill fit {best.skill_fit:.2f}"
        f"{f' ({skills})' if skills else ''}, capacity fit {best.capacity_fit:.2f} with "
        f"{best.free_hours:.1f} h free, balance {best.balance:.2f}."
    )
    if len(facts.candidates) > 1:
        runner = facts.candidates[1]
        text += f" Next is {runner.name} at {runner.total:.1f}."
    return text


def explain(client: LLMClient, facts: ExplanationFacts) -> Explanation:
    best = facts.candidates[0].member_id if facts.candidates else None
    fallback = Explanation(
        recommended_member_id=best, text=template(facts), grounded=False, source="template"
    )
    if best is None:
        return fallback
    prompt = load_prompt(PROMPT_NAME, facts=facts.model_dump_json(indent=2))
    try:
        reply = client.generate_structured(PROMPT_NAME, prompt, ExplanationReply)
    except LLMError:
        return fallback

    text = " ".join(p.strip() for p in (reply.explanation, reply.runner_up_note) if p.strip())
    bad = ungrounded_numbers(text, fact_numbers(facts))
    if reply.recommended_member_id != best or bad or not text:
        return fallback.model_copy(update={"ungrounded": bad})
    return Explanation(recommended_member_id=best, text=text, grounded=True, source="model")
