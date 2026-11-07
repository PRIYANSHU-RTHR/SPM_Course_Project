"""Explanation and risk agents in fixture mode: grounded replies pass, invented numbers don't."""

import json
from pathlib import Path

from pydantic import BaseModel

from app.agents.explanation import (
    CandidateFacts,
    ExplanationFacts,
    ExplanationReply,
    SkillFact,
    explain,
    template,
)
from app.agents.grounding import fact_numbers, ungrounded_numbers
from app.agents.llm import LLMClient, fixture_path, prompt_hash
from app.agents.prompts import load_prompt
from app.agents.risk_plan import RiskFacts, RmmmReply, plan_risk
from app.agents.risk_plan import template as risk_template
from app.config import Settings


def _cand(member_id: int, name: str, total: float, has: int) -> CandidateFacts:
    return CandidateFacts(
        member_id=member_id,
        name=name,
        total=total,
        skill_fit=round(min(has / 4, 1), 2),
        capacity_fit=1.0,
        balance=0.8,
        skill_part=60 * min(has / 4, 1),
        capacity_part=25.0,
        balance_part=12.0,
        free_hours=32.0,
        skills=[SkillFact(skill="payments", required=4, has=has, fit=round(min(has / 4, 1), 2))],
    )


FACTS = ExplanationFacts(
    task_id=14,
    title="Integrate UPI payment gateway",
    hours=25.3,
    candidates=[_cand(3, "Aarav Mehta", 97.0, 4), _cand(5, "Diya Shah", 82.0, 3)],
)
RISK = RiskFacts(
    risk_id=7,
    rule_key="spi_low",
    title="Schedule slipping: SPI 0.82",
    category="schedule",
    probability=4,
    impact=4,
    score=16,
    evidence={"spi": 0.82, "sv": -12800.0, "bac": 640000.0},
)


def _client(tmp_path: Path, prompt_name: str, prompt: str, schema: type[BaseModel], reply: dict):
    path = fixture_path(tmp_path, prompt_name, prompt_hash(prompt_name, prompt, schema))
    path.write_text(json.dumps({"model": "test", "response_json": reply}), encoding="utf-8")
    return LLMClient(Settings(_env_file=None, llm_mode="fixture"), fixtures_dir=tmp_path)  # type: ignore[call-arg]


def _explain_with(tmp_path: Path, reply: dict):
    prompt = load_prompt("explanation", facts=FACTS.model_dump_json(indent=2))
    return explain(_client(tmp_path, "explanation", prompt, ExplanationReply, reply), FACTS)


def test_grounded_model_reply_passes(tmp_path: Path) -> None:
    result = _explain_with(
        tmp_path,
        {
            "recommended_member_id": 3,
            "explanation": "Aarav Mehta scores 97 because his payments level 4 meets the "
            "required 4 and he has 32 free hours.",
            "runner_up_note": "Diya Shah follows at 82 with payments 3 of 4.",
        },
    )
    assert (result.source, result.grounded, result.recommended_member_id) == ("model", True, 3)
    assert result.text.startswith("Aarav Mehta scores 97")


def test_invented_number_falls_back_to_template(tmp_path: Path) -> None:
    result = _explain_with(
        tmp_path,
        {
            "recommended_member_id": 3,
            "explanation": "Aarav Mehta scores 97 and will finish 30% faster than Diya.",
            "runner_up_note": "",
        },
    )
    assert (result.source, result.grounded) == ("template", False)
    assert result.ungrounded == ["30%"]
    assert result.text == template(FACTS)


def test_wrong_member_falls_back(tmp_path: Path) -> None:
    result = _explain_with(
        tmp_path,
        {"recommended_member_id": 5, "explanation": "Diya Shah scores 82.", "runner_up_note": ""},
    )
    assert result.source == "template"


def test_missing_fixture_falls_back_without_error(tmp_path: Path) -> None:
    client = LLMClient(Settings(_env_file=None, llm_mode="fixture"), fixtures_dir=tmp_path)  # type: ignore[call-arg]
    assert explain(client, FACTS).source == "template"


def test_template_cites_only_given_numbers() -> None:
    text = template(FACTS)
    assert text == (
        "Aarav Mehta scores 97.0: skill fit 1.00 (payments 4/4), capacity fit 1.00 with 32.0 h "
        "free, balance 0.80. Next is Diya Shah at 82.0."
    )
    assert ungrounded_numbers(text, fact_numbers(FACTS)) == []


def test_no_candidates() -> None:
    empty = FACTS.model_copy(update={"candidates": []})
    client = LLMClient(Settings(_env_file=None, llm_mode="fixture"))  # type: ignore[call-arg]
    result = explain(client, empty)
    assert (result.recommended_member_id, result.source) == (None, "template")


def _plan_with(tmp_path: Path, reply: dict):
    prompt = load_prompt("risk_plan", facts=RISK.model_dump_json(indent=2))
    return plan_risk(_client(tmp_path, "risk_plan", prompt, RmmmReply, reply), RISK)


def test_grounded_rmmm_is_used(tmp_path: Path) -> None:
    plan = _plan_with(
        tmp_path,
        {
            "mitigation": "Move the critical payment tasks ahead of vendor reports.",
            "monitoring_trigger": "Escalate if SPI drops below 0.82 at the next refresh.",
            "contingency": "Defer the CSV sales report to after launch.",
            "owner_role": "Project manager",
        },
    )
    assert (plan.source, plan.grounded) == ("model", True)


def test_rmmm_with_invented_threshold_falls_back(tmp_path: Path) -> None:
    plan = _plan_with(
        tmp_path,
        {
            "mitigation": "Add 2 developers.",
            "monitoring_trigger": "Escalate if SPI drops below 0.75.",
            "contingency": "Defer reports.",
            "owner_role": "Project manager",
        },
    )
    assert (plan.source, plan.grounded) == ("template", False)
    assert plan.ungrounded == ["2", "0.75"]
    assert plan.owner_role == "Project manager"


def test_risk_template_is_grounded() -> None:
    reply = risk_template(RISK)
    assert "score rises above 16" in reply.monitoring_trigger
    assert ungrounded_numbers(" ".join(reply.model_dump().values()), fact_numbers(RISK)) == []
