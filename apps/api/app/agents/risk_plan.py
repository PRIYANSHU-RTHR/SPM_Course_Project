"""Risk agent: an RMMM plan (mitigation, monitoring trigger, contingency, owner) for one risk.

Same rule as the explanation agent: the model may only cite numbers from the risk's
evidence. Otherwise, or if the call fails, a per-category template is used.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.grounding import fact_numbers, ungrounded_numbers
from app.agents.llm import LLMClient, LLMError
from app.agents.prompts import load_prompt

PROMPT_NAME = "risk_plan"


class RiskFacts(BaseModel):
    risk_id: int
    rule_key: str
    title: str
    category: str
    probability: int
    impact: int
    score: int
    scale_max: int = Field(default=5, description="probability and impact are 1 to scale_max")
    evidence: dict[str, float | int | str | None]


class RmmmReply(BaseModel):
    mitigation: str = Field(description="What to do now to lower probability or impact")
    monitoring_trigger: str = Field(description="Observable condition that escalates it")
    contingency: str = Field(description="What to do if the risk happens")
    owner_role: str


class RiskPlan(RmmmReply):
    grounded: bool
    source: Literal["model", "template"]
    ungrounded: list[str] = Field(default_factory=list)


_TEMPLATES = {
    "schedule": (
        "Re-sequence work on the critical path and move non-critical tasks out of its way.",
        "Project manager",
        "Cut or defer the lowest-priority scope and re-baseline the plan.",
    ),
    "resource": (
        "Rebalance assignments so no member is booked above capacity; pair on critical work.",
        "Project manager",
        "Reassign the affected tasks and move the deadline of non-critical ones.",
    ),
    "cost": (
        "Review actual hours against estimates weekly and stop scope that is not paying back.",
        "Project manager",
        "Agree a budget change with the sponsor or reduce scope to stay within BAC.",
    ),
    "skill": (
        "Pair a second member with the current expert and write down the key steps.",
        "Tech lead",
        "Bring in help from outside the team or simplify the task to fit available skills.",
    ),
    "technical": (
        "Spike the risky part early and add tests around it.",
        "Tech lead",
        "Fall back to the simpler design and accept the reduced feature.",
    ),
}


def template(facts: RiskFacts) -> RmmmReply:
    mitigation, owner, contingency = _TEMPLATES.get(facts.category, _TEMPLATES["technical"])
    numeric = [f"{k} {v}" for k, v in facts.evidence.items() if isinstance(v, int | float)]
    trigger = f"Review at every refresh; escalate if the score rises above {facts.score}"
    trigger += f" (now {', '.join(numeric)})." if numeric else "."
    return RmmmReply(
        mitigation=mitigation,
        monitoring_trigger=trigger,
        contingency=contingency,
        owner_role=owner,
    )


def plan_risk(client: LLMClient, facts: RiskFacts) -> RiskPlan:
    fallback = RiskPlan(**template(facts).model_dump(), grounded=False, source="template")
    prompt = load_prompt(PROMPT_NAME, facts=facts.model_dump_json(indent=2))
    try:
        reply = client.generate_structured(PROMPT_NAME, prompt, RmmmReply)
    except LLMError:
        return fallback
    text = " ".join(reply.model_dump().values())
    bad = ungrounded_numbers(text, fact_numbers(facts))
    if bad:
        return fallback.model_copy(update={"ungrounded": bad})
    return RiskPlan(**reply.model_dump(), grounded=True, source="model")
