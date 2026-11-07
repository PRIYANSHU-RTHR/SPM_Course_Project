"""Runs the explanation and risk agents on engine output and stores RMMM plans."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.explanation import CandidateFacts, Explanation, ExplanationFacts, SkillFact, explain
from app.agents.llm import LLMClient
from app.agents.risk_plan import RiskFacts, RiskPlan, plan_risk
from app.errors import NotFoundError
from app.models import AuditLog, Member, Risk, Task
from app.schemas.assignment import Mode
from app.services.assignment import recommend
from app.services.common import commit
from app.services.inputs import get_project

ACTOR = "system:risk-agent"


def explain_assignment(
    session: Session, client: LLMClient, project_id: int, task_id: int, mode: Mode
) -> Explanation:
    plan = recommend(session, project_id, mode)
    rec = next((r for r in plan.recommendations if r.task_id == task_id), None)
    task = session.get(Task, task_id)
    if rec is None or task is None:
        raise NotFoundError(
            f"Task {task_id} not found in project {project_id}", details={"task_id": task_id}
        )
    names = dict(session.execute(select(Member.id, Member.name)).tuples().all())
    facts = ExplanationFacts(
        task_id=task_id,
        title=task.title,
        hours=(task.optimistic_hours + 4 * task.most_likely_hours + task.pessimistic_hours) / 6,
        candidates=[
            CandidateFacts(
                member_id=c.member_id,
                name=names.get(c.member_id, f"Member {c.member_id}"),
                total=round(c.score.total, 1),
                skill_fit=round(c.score.skill_fit, 2),
                capacity_fit=round(c.score.capacity_fit, 2),
                balance=round(c.score.balance, 2),
                skill_part=round(c.score.skill_part, 1),
                capacity_part=round(c.score.capacity_part, 1),
                balance_part=round(c.score.balance_part, 1),
                free_hours=round(c.score.free_hours, 1),
                skills=[
                    SkillFact(skill=s.skill, required=s.required, has=s.has, fit=round(s.fit, 2))
                    for s in c.score.skills
                ],
            )
            for c in rec.candidates
        ],
    )
    return explain(client, facts)


def plan_risk_rmmm(session: Session, client: LLMClient, project_id: int, risk_id: int) -> Risk:
    """Generate the RMMM plan for one risk and store it on the row (audited)."""
    get_project(session, project_id)
    risk = session.get(Risk, risk_id)
    if risk is None or risk.project_id != project_id:
        raise NotFoundError(
            f"Risk {risk_id} not found in project {project_id}", details={"risk_id": risk_id}
        )
    facts = RiskFacts(
        risk_id=risk.id,
        rule_key=risk.rule_key,
        title=risk.title,
        category=risk.category.value,
        probability=risk.probability,
        impact=risk.impact,
        score=risk.probability * risk.impact,
        evidence=risk.evidence,
    )
    plan: RiskPlan = plan_risk(client, facts)
    before = risk.rmmm
    risk.rmmm = plan.model_dump()
    session.add(
        AuditLog(
            actor=ACTOR,
            action="risk.plan",
            entity="risk",
            entity_id=risk.id,
            before={"rmmm": before},
            after={"rmmm": risk.rmmm},
            reason=f"RMMM plan generated ({plan.source})",
        )
    )
    commit(session)
    return risk
