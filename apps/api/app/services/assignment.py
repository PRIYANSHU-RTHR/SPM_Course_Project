"""Assignment recommendations (engine) and applying them (DB + audit log)."""

import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.assignment import compare, recommend_greedy, recommend_optimal
from app.engines.calendar import hours_to_window
from app.errors import NotFoundError
from app.models import Assignment, AuditLog, Member, Task
from app.schemas.assignment import (
    AppliedAssignment,
    ApplyRequest,
    CandidateOut,
    Comparison,
    Ineligible,
    Mode,
    RecommendationOut,
    RecommendResponse,
    ScoreOut,
)
from app.services.inputs import get_project, load_members, load_tasks, run_cpm


def recommend(session: Session, project_id: int, mode: Mode) -> RecommendResponse:
    project = get_project(session, project_id)
    tasks = load_tasks(session, project_id)
    members = load_members(session)
    # Task windows come from the CPM early schedule on the project calendar.
    windows = {
        r.task_id: hours_to_window(project.start_date, r.es, r.ef) for r in run_cpm(tasks).tasks
    }

    greedy = recommend_greedy(tasks, members, windows)
    optimal = recommend_optimal(tasks, members, windows)
    plan = optimal if mode == "optimal" else greedy

    return RecommendResponse(
        project_id=project_id,
        mode=mode,
        total_score=plan.total_score,
        utilisation_std=plan.utilisation_std,
        unassigned=plan.unassigned,
        utilisation={k: (v if math.isfinite(v) else None) for k, v in plan.utilisation.items()},
        recommendations=[
            RecommendationOut(
                task_id=r.task_id,
                window_start=windows[r.task_id][0],
                window_end=windows[r.task_id][1],
                member_id=r.member_id,
                score=ScoreOut.model_validate(r.score) if r.score else None,
                candidates=[CandidateOut.model_validate(c) for c in r.candidates],
                ineligible=[Ineligible(member_id=m, reason=why) for m, why in r.ineligible],
            )
            for r in plan.recommendations
        ],
        comparison=Comparison.model_validate(compare(greedy, optimal)),
    )


def apply(session: Session, project_id: int, request: ApplyRequest) -> list[AppliedAssignment]:
    """Make each item the task's current assignment and write one audit row per change."""
    get_project(session, project_id)
    task_ids = {i.task_id for i in request.items}
    member_ids = {i.member_id for i in request.items}
    found_tasks = set(
        session.scalars(select(Task.id).where(Task.project_id == project_id, Task.id.in_(task_ids)))
    )
    found_members = set(session.scalars(select(Member.id).where(Member.id.in_(member_ids))))
    if missing := task_ids - found_tasks:
        raise NotFoundError(
            "Tasks not found in this project", details={"task_ids": sorted(missing)}
        )
    if missing := member_ids - found_members:
        raise NotFoundError("Members not found", details={"member_ids": sorted(missing)})

    applied = []
    for item in request.items:
        current = session.scalar(
            select(Assignment).where(Assignment.task_id == item.task_id, Assignment.is_current)
        )
        previous = current.member_id if current else None
        if current:
            current.is_current = False
            session.flush()  # partial unique index: at most one current row per task
        row = Assignment(
            task_id=item.task_id,
            member_id=item.member_id,
            score_breakdown=item.score_breakdown,
            source=item.source,
            reason=item.reason,
        )
        session.add(row)
        session.flush()
        session.add(
            AuditLog(
                actor=request.actor,
                action=f"assignment.{item.source.value}",
                entity="assignment",
                entity_id=row.id,
                before={"task_id": item.task_id, "member_id": previous} if current else None,
                after={
                    "task_id": item.task_id,
                    "member_id": item.member_id,
                    "source": item.source.value,
                },
                reason=item.reason,
            )
        )
        applied.append(
            AppliedAssignment(
                assignment_id=row.id,
                task_id=item.task_id,
                member_id=item.member_id,
                previous_member_id=previous,
                source=item.source,
            )
        )
    session.commit()
    return applied
