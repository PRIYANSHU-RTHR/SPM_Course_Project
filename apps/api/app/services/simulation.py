"""Simulated clock: move a project's "today" forward and generate the progress in between.

Each working day in (old clock, new clock]:
  1. plan the remaining work from that day with the current owners (scheduler engine);
  2. every open, owned task with hours planned that day gets them:
       actual_hours     += planned * cost_factor        cost_factor ~ U(0.80, 1.02)
       percent_complete += planned * efficiency / te    efficiency  ~ U(0.85, 1.05)
     (no work on the owner's leave days; unowned tasks don't move);
  3. a snapshot (PV, EV, AC) from the EVM engine for that day.
The random draws come from `Random(f"{SIM_SEED}:{project}:{day}")`, two per task in id order,
so the result depends only on the seed and the DB state. Advancing 7 + 7 days therefore
equals advancing 14 days in one go.
"""

from datetime import date, timedelta
from random import Random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines import calendar
from app.engines.estimation import pert
from app.engines.scheduler import ScheduleError, schedule
from app.errors import ValidationFailedError
from app.models import Assignment, AuditLog, Snapshot, Task, TaskStatus
from app.schemas.reallocation import AdvanceResult
from app.services.evm import build_evm
from app.services.inputs import get_project, load_members, load_tasks, project_today, run_cpm
from app.services.risk_service import refresh_risks
from app.services.scenario import load_scenario

# Centred on the demo story (plan.md section 4): SPI about 0.92-0.95 while every task has an
# owner, CPI about 1.04 (mean efficiency 0.95 / mean cost factor 0.91).
EFFICIENCY = (0.85, 1.05)
COST_FACTOR = (0.80, 1.02)


def advance(
    session: Session, project_id: int, days: int, seed: int, actor: str = "pm"
) -> AdvanceResult:
    project = get_project(session, project_id)
    old = project_today(project)
    new = old + timedelta(days=days)
    tasks = load_tasks(session, project_id)
    te = {t.id: pert(t).te for t in tasks}
    cpm = run_cpm(tasks)
    members = {m.id: m for m in load_members(session)}
    rows = {
        t.id: t
        for t in session.scalars(
            select(Task).where(Task.project_id == project_id).order_by(Task.id)
        )
    }
    owners = dict(
        session.execute(
            select(Assignment.task_id, Assignment.member_id).where(
                Assignment.task_id.in_(rows), Assignment.is_current
            )
        ).all()
    )

    days_done: list[date] = calendar.working_days(old + timedelta(days=1), new)
    for day in days_done:
        progress = {i: t.percent_complete for i, t in rows.items()}
        try:
            plan = schedule(
                tasks,
                owners,
                list(members.values()),
                project.start_date,
                cpm_result=cpm,
                progress=progress,
                as_of=day,
            )
        except ScheduleError as exc:
            raise ValidationFailedError(str(exc)) from exc
        placed = {t.task_id: t for t in plan.tasks}
        rng = Random(f"{seed}:{project_id}:{day.isoformat()}")
        for task_id, row in rows.items():
            efficiency, cost = rng.uniform(*EFFICIENCY), rng.uniform(*COST_FACTOR)
            st = placed.get(task_id)
            member = members.get(st.member_id) if st and st.member_id is not None else None
            if (
                st is None
                or member is None
                or row.status == TaskStatus.DONE
                or not st.start <= day <= st.end
                or st.hours <= 0
                or calendar.daily_capacity(member, day) <= 0
            ):
                continue
            span = calendar.working_days(max(st.start, day), st.end)
            planned = st.hours / max(len(span), 1)
            row.actual_hours += planned * cost
            if te[task_id] > 0:
                row.percent_complete = min(
                    100.0, row.percent_complete + planned * efficiency / te[task_id] * 100
                )
            row.status = (
                TaskStatus.DONE if row.percent_complete >= 99.95 else TaskStatus.IN_PROGRESS
            )
            if row.status == TaskStatus.DONE:
                row.percent_complete = 100.0
        session.flush()

        result = build_evm(session, project, day)
        snap = session.scalar(
            select(Snapshot).where(Snapshot.project_id == project_id, Snapshot.date == day)
        )
        if snap is None:
            snap = Snapshot(project_id=project_id, date=day)
            session.add(snap)
        snap.pv, snap.ev, snap.ac = result.pv, result.ev, result.ac

    project.sim_date = new
    session.add(
        AuditLog(
            actor=actor,
            action="simulation.advance",
            entity="project",
            entity_id=project_id,
            before={"sim_date": old.isoformat()},
            after={"sim_date": new.isoformat(), "working_days": len(days_done)},
            reason=f"simulated clock advanced {days} days",
        )
    )
    session.commit()

    risks = refresh_risks(session, project_id, new, seed)
    evm = build_evm(session, project, new)
    forecast = load_scenario(session, project, new, seed).evaluate().forecast
    return AdvanceResult(
        project_id=project_id,
        from_date=old,
        to_date=new,
        working_days=len(days_done),
        snapshots=len(days_done),
        spi=evm.spi,
        cpi=evm.cpi,
        p_on_time=forecast.p_on_time if forecast else None,
        risks=risks,
    )
