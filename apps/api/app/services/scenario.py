"""What-if evaluation: a project's engine inputs loaded once, re-run with other owners.

The risk register and the reallocation workflow both go through here, so "now" and
"if approved" are computed the same way, on in-memory copies, by engines only.

Resource-adjusted forecast. The Monte Carlo engine samples the dependency network only: it
does not see owners, leave or progress, so a leave or a reassignment would not move
P(on time). The resource-constrained scheduler sees all three but is deterministic. So:

    shift = finish(remaining work from `as_of`, with owners, leave and progress)
          - finish(same tasks from the project start, no owners, no progress)

both from the same scheduler, so its whole-day placement cancels out (CPM packs hours, the
scheduler starts tasks on day boundaries: on the seed project that alone is 43 h). The
forecast is evaluated against `deadline - shift`, with every percentile, histogram bin and
CDF point moved by `+shift`. The spread still comes from Beta-PERT sampling, while the level
comes from the resource-aware schedule.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from functools import cached_property

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.calendar import HOURS_PER_DAY, add_working_days, working_days_between
from app.engines.cpm import CycleError
from app.engines.montecarlo import DEFAULT_RUNS, forecast
from app.engines.risk import RiskConfig, RiskFinding, RiskSnapshot, TaskState, detect_risks
from app.engines.scheduler import ScheduleError, schedule
from app.engines.types import (
    CPMResult,
    EVMResult,
    ForecastResult,
    MemberInput,
    ScheduledTask,
    ScheduleResult,
    TaskInput,
)
from app.errors import ConflictError, ValidationFailedError
from app.models import Assignment, Member, Project, Task
from app.schemas.reallocation import ScenarioMetrics
from app.services.evm import build_evm
from app.services.inputs import load_members, load_tasks, run_cpm
from app.services.schedule import build_schedule

# -- pure helpers -----------------------------------------------------------------------------


def hours_through(start: date, day: date) -> float:
    """Working hours from `start` to the end of `day` (inclusive), as CPM hours count them."""
    return working_days_between(start, day + timedelta(days=1)) * HOURS_PER_DAY


def hours_to_date(start: date, hours: float) -> date:
    """The working day on which `hours` of CPM time (from `start`) ends."""
    return add_working_days(start, max(math.ceil(hours / HOURS_PER_DAY - 1e-9) - 1, 0))


def shifted_forecast(
    tasks: Sequence[TaskInput], deadline_hours: float, shift: float, runs: int, seed: int
) -> ForecastResult:
    """Monte Carlo forecast moved by `shift` hours (see the module docstring)."""
    try:
        raw = forecast(list(tasks), deadline_hours - shift, runs, seed)
    except CycleError as exc:
        raise ConflictError(str(exc), details={"cycle": exc.cycle}) from exc
    return replace(
        raw,
        deadline_hours=deadline_hours,
        mean=raw.mean + shift,
        p50=raw.p50 + shift,
        p80=raw.p80 + shift,
        p95=raw.p95 + shift,
        histogram=tuple((h + shift, n) for h, n in raw.histogram),
        cdf=tuple((h + shift, p) for h, p in raw.cdf),
    )


# -- scenario -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    project_id: int
    start: date
    deadline: date
    as_of: date
    seed: int
    runs: int
    tasks: tuple[TaskInput, ...]
    states: Mapping[int, TaskState]
    members: tuple[MemberInput, ...]
    names: Mapping[int, str]
    owners: Mapping[int, int | None]
    evm: EVMResult | None  # measured from the DB; owners don't change work already done

    def with_owners(self, changes: Mapping[int, int | None]) -> "Scenario":
        return replace(self, owners={**self.owners, **changes})

    def is_open(self, task_id: int) -> bool:
        return self.states[task_id].status != "done"

    def evaluate(self) -> "Outcome":
        return Outcome(self)


@dataclass(frozen=True)
class Outcome:
    """Engine results for one scenario. Computed lazily; each property runs once."""

    scenario: Scenario

    @cached_property
    def cpm(self) -> CPMResult:
        return run_cpm(list(self.scenario.tasks))

    def _schedule(self, as_of: date | None) -> ScheduleResult:
        s = self.scenario
        try:
            return schedule(
                list(s.tasks),
                s.owners,
                list(s.members),
                s.start,
                cpm_result=self.cpm,
                progress={i: st.percent_complete for i, st in s.states.items()},
                as_of=as_of,
            )
        except ScheduleError as exc:
            raise ValidationFailedError(str(exc)) from exc

    @cached_property
    def baseline(self) -> ScheduleResult:
        """Whole project from its start: what EVM and the risk rules measure against."""
        return self._schedule(None)

    @cached_property
    def plan(self) -> ScheduleResult:
        """Remaining work planned from `as_of`: the finish the project is heading for."""
        return self._schedule(self.scenario.as_of)

    @cached_property
    def placed(self) -> dict[int, ScheduledTask]:
        return {t.task_id: t for t in self.plan.tasks}

    @cached_property
    def reference(self) -> ScheduleResult:
        """The network alone on the scheduler's calendar: what the Monte Carlo engine models."""
        s = self.scenario
        return schedule(list(s.tasks), {}, [], s.start, cpm_result=self.cpm)

    @cached_property
    def shift_hours(self) -> float:
        if not self.scenario.tasks:
            return 0.0
        start = self.scenario.start
        return hours_through(start, self.plan.finish) - hours_through(start, self.reference.finish)

    @cached_property
    def forecast(self) -> ForecastResult | None:
        s = self.scenario
        if not s.tasks:
            return None
        deadline = hours_through(s.start, s.deadline)
        return shifted_forecast(s.tasks, deadline, self.shift_hours, s.runs, s.seed)

    @cached_property
    def snapshot(self) -> RiskSnapshot:
        s = self.scenario
        return RiskSnapshot(
            as_of=s.as_of,
            project_start=s.start,
            tasks=s.tasks,
            task_state=s.states,
            members=s.members,
            member_names=s.names,
            assignments=s.owners,
            cpm=self.cpm,
            schedule=self.baseline,
            forecast=self.forecast,
            evm=s.evm,
        )

    def findings(self, config: RiskConfig | None = None) -> list[RiskFinding]:
        return detect_risks(self.snapshot, config)

    def metrics(self) -> ScenarioMetrics:
        fc, start = self.forecast, self.scenario.start
        return ScenarioMetrics(
            p_on_time=fc.p_on_time if fc else None,
            p50=hours_to_date(start, fc.p50) if fc else None,
            p80=hours_to_date(start, fc.p80) if fc else None,
            p80_hours=fc.p80 if fc else None,
            finish=self.plan.finish,
            resource_shift_hours=self.shift_hours,
        )


def load_scenario(
    session: Session, project: Project, as_of: date, seed: int, runs: int = DEFAULT_RUNS
) -> Scenario:
    tasks = load_tasks(session, project.id)
    rows = session.scalars(select(Task).where(Task.project_id == project.id)).all()
    owners = session.execute(
        select(Assignment.task_id, Assignment.member_id)
        .join(Task, Task.id == Assignment.task_id)
        .where(Task.project_id == project.id, Assignment.is_current)
    )
    return Scenario(
        project_id=project.id,
        start=project.start_date,
        deadline=project.deadline,
        as_of=as_of,
        seed=seed,
        runs=runs,
        tasks=tuple(tasks),
        states={t.id: TaskState(t.title, t.status.value, t.percent_complete) for t in rows},
        members=tuple(load_members(session)),
        names=dict(session.execute(select(Member.id, Member.name)).all()),
        owners=dict(owners.all()),
        evm=build_evm(session, project, as_of, build_schedule(session, project)) if tasks else None,
    )
