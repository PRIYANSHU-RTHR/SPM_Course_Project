"""EVM for a project: baseline from the current schedule, progress from tasks and snapshots."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.evm import ZERO, earned_value, evm, hours_cost, money, planned_value
from app.engines.types import BaselineTask
from app.models import Snapshot, Task
from app.schemas.evm import EvmPointOut, ProjectEvm
from app.services.inputs import get_project
from app.services.schedule import build_schedule


def project_evm(session: Session, project_id: int, as_of: date) -> ProjectEvm:
    project = get_project(session, project_id)
    rate = project.hourly_rate
    # shortcut: baseline = today's schedule, recomputed per request; persisting a frozen
    # baseline needs a table (schema change), so re-planning currently moves PV too.
    plan = build_schedule(session, project)
    baseline = [
        BaselineTask(t.task_id, t.start, t.end, hours_cost(t.hours, rate)) for t in plan.tasks
    ]
    bac = money(sum((b.budget for b in baseline), ZERO))

    budget_of = {b.task_id: b.budget for b in baseline}
    rows = session.scalars(select(Task).where(Task.project_id == project_id)).all()
    ev = earned_value([budget_of[t.id] for t in rows], [t.percent_complete for t in rows])
    ac = money(sum((hours_cost(t.actual_hours, rate) for t in rows), ZERO))
    result = evm(bac, planned_value(baseline, as_of), ev, ac)

    snaps = session.scalars(
        select(Snapshot).where(Snapshot.project_id == project_id).order_by(Snapshot.date)
    ).all()
    planned = []
    day = project.start_date + timedelta(days=(4 - project.start_date.weekday()) % 7)  # Friday
    while day < plan.finish + timedelta(days=7):
        planned.append(EvmPointOut(on=day, pv=planned_value(baseline, day), ev=None, ac=None))
        day += timedelta(days=7)

    return ProjectEvm(
        project_id=project_id,
        as_of=as_of,
        budget=project.budget,
        bac=result.bac,
        pv=result.pv,
        ev=result.ev,
        ac=result.ac,
        sv=result.sv,
        cv=result.cv,
        spi=result.spi,
        cpi=result.cpi,
        eac=result.eac,
        etc=result.etc,
        vac=result.vac,
        tcpi=result.tcpi,
        notes=result.notes,
        snapshots=[
            EvmPointOut(on=s.date, pv=planned_value(baseline, s.date), ev=s.ev, ac=s.ac)
            for s in snaps
        ],
        planned=planned,
    )
