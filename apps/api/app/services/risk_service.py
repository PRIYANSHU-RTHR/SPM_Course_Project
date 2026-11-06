"""Risk register: build a snapshot from the DB + engines, detect, upsert, close, audit.

Upsert key is (project_id, rule_key, subject_ref). Rows are never deleted. A risk whose rule
stops firing is set to `closed`; if it fires again later the same row is reopened. Opening,
reopening and closing each write one `audit_log` row. Plain P/I/evidence refreshes don't.
"""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.montecarlo import DEFAULT_RUNS
from app.engines.risk import RiskConfig, RiskFinding, RiskSnapshot, TaskState, detect_risks
from app.models import Assignment, AuditLog, Member, Project, Risk, RiskCategory, RiskStatus, Task
from app.schemas.risk import RiskRefreshResult
from app.services.common import PageParams, commit, paginate
from app.services.evm import build_evm
from app.services.forecast import build_forecast
from app.services.inputs import get_project, load_members, load_tasks, run_cpm
from app.services.schedule import build_schedule

ACTOR = "system:risk-engine"


def build_snapshot(
    session: Session, project: Project, as_of: date, seed: int, runs: int = DEFAULT_RUNS
) -> RiskSnapshot:
    tasks = load_tasks(session, project.id)
    rows = session.scalars(select(Task).where(Task.project_id == project.id)).all()
    current = session.execute(
        select(Assignment.task_id, Assignment.member_id)
        .join(Task, Task.id == Assignment.task_id)
        .where(Task.project_id == project.id, Assignment.is_current)
    )
    plan = build_schedule(session, project)
    return RiskSnapshot(
        as_of=as_of,
        project_start=project.start_date,
        tasks=tuple(tasks),
        task_state={t.id: TaskState(t.title, t.status.value, t.percent_complete) for t in rows},
        members=tuple(load_members(session)),
        member_names=dict(session.execute(select(Member.id, Member.name)).all()),
        assignments={row.task_id: row.member_id for row in current},
        cpm=run_cpm(tasks),
        schedule=plan,
        forecast=build_forecast(session, project, runs, seed, tasks) if tasks else None,
        evm=build_evm(session, project, as_of, plan) if tasks else None,
    )


def _state(risk: Risk) -> dict[str, Any]:
    return {
        "status": risk.status.value,
        "probability": risk.probability,
        "impact": risk.impact,
        "evidence": risk.evidence,
    }


def _audit(session: Session, risk: Risk, action: str, before: Any, reason: str) -> None:
    session.add(
        AuditLog(
            actor=ACTOR,
            action=action,
            entity="risk",
            entity_id=risk.id,
            before=before,
            after=_state(risk),
            reason=reason,
        )
    )


def _apply(risk: Risk, finding: RiskFinding) -> bool:
    """Copy the finding onto the row; True if anything visible changed."""
    new = {
        "category": RiskCategory(finding.category),
        "probability": finding.probability,
        "impact": finding.impact,
        "title": finding.title,
        "evidence": finding.evidence,
    }
    changed = any(getattr(risk, k) != v for k, v in new.items())
    for key, value in new.items():
        setattr(risk, key, value)
    return changed


def refresh_risks(
    session: Session,
    project_id: int,
    as_of: date,
    seed: int,
    config: RiskConfig | None = None,
    runs: int = DEFAULT_RUNS,
) -> RiskRefreshResult:
    project = get_project(session, project_id)
    findings = detect_risks(build_snapshot(session, project, as_of, seed, runs), config)
    existing = {
        (r.rule_key, r.subject_ref): r
        for r in session.scalars(select(Risk).where(Risk.project_id == project_id))
    }

    opened: list[Risk] = []
    reopened: list[tuple[Risk, dict[str, Any]]] = []
    updated: list[Risk] = []
    for finding in findings:
        risk = existing.pop((finding.rule_key, finding.subject_ref), None)
        if risk is None:
            risk = Risk(
                project_id=project_id,
                rule_key=finding.rule_key,
                subject_ref=finding.subject_ref,
                status=RiskStatus.OPEN,
            )
            _apply(risk, finding)
            session.add(risk)
            opened.append(risk)
        elif risk.status == RiskStatus.CLOSED:
            before = _state(risk)
            _apply(risk, finding)
            risk.status = RiskStatus.OPEN
            reopened.append((risk, before))
        elif _apply(risk, finding):
            updated.append(risk)  # open/mitigating keeps its status (PM-owned)

    closed: list[tuple[Risk, dict[str, Any]]] = []
    for risk in existing.values():  # rule no longer fires
        if risk.status != RiskStatus.CLOSED:
            before = _state(risk)
            risk.status = RiskStatus.CLOSED
            closed.append((risk, before))

    session.flush()  # ids for new rows, needed by audit_log
    for risk in opened:
        _audit(session, risk, "risk_opened", None, risk.title)
    for risk, before in reopened:
        _audit(session, risk, "risk_reopened", before, risk.title)
    for risk, before in closed:
        _audit(session, risk, "risk_closed", before, "Rule no longer fires")

    open_total = sum(
        1
        for r in session.scalars(select(Risk).where(Risk.project_id == project_id))
        if r.status != RiskStatus.CLOSED
    )
    result = RiskRefreshResult(
        as_of=as_of,
        opened=[r.id for r in opened],
        reopened=[r.id for r, _ in reopened],
        updated=[r.id for r in updated],
        closed=[r.id for r, _ in closed],
        open_total=open_total,
    )
    commit(session)
    return result


def list_risks(
    session: Session, project_id: int, page: PageParams, include_closed: bool = False
) -> tuple[list[Risk], int]:
    get_project(session, project_id)
    stmt = select(Risk).where(Risk.project_id == project_id)
    if not include_closed:
        stmt = stmt.where(Risk.status != RiskStatus.CLOSED)
    stmt = stmt.order_by((Risk.probability * Risk.impact).desc(), Risk.id)
    return paginate(session, stmt, page)
