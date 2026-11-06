"""Rule-based risk detection (PURE: no DB, no I/O, no LLM).

Input is a `RiskSnapshot` of engine results; output is a list of `RiskFinding`s. Each rule from
plan.md Step 12 is one small function. Thresholds and the probability/impact mappings live in
`RiskConfig`; every mapping is an explicit band table, so no score is hidden in rule code.

Band tables:
- `AtLeast` bands are checked top-down: the first `(bound, score)` with `value >= bound` wins.
- `Below` bands are checked top-down: the first `(bound, score)` with `value < bound` wins.
A value past the last band gets the last band's score. Each rule only fires once its threshold
is crossed, so in practice the value always lands inside a band.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from app.engines import calendar
from app.engines.assignment import is_eligible
from app.engines.types import (
    CPMResult,
    EVMResult,
    ForecastResult,
    MemberInput,
    ScheduleResult,
    TaskInput,
)

Category = Literal["schedule", "resource", "cost", "skill", "technical"]
Evidence = dict[str, float | int | str | None]
AtLeast = tuple[tuple[float, int], ...]
Below = tuple[tuple[float, int], ...]

DONE = "done"


# --------------------------------------------------------------------------------------
# Config: thresholds + probability / impact tables
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RiskConfig:
    # member_overload: a member is booked above capacity in at least one week.
    overload_utilisation: float = 1.0  # fires when hours / capacity > this
    overload_probability_by_weeks: AtLeast = ((3, 5), (2, 4), (1, 3))  # weeks over
    overload_impact_by_peak: AtLeast = ((1.5, 5), (1.25, 4), (1.0, 3))  # peak utilisation

    # bus_factor: a critical task only `bus_factor_max_people` (or fewer, but > 0) can do.
    bus_factor_max_people: int = 1
    # P(the single owner becomes a problem) grows with how often the task is critical.
    bus_factor_probability_by_criticality: AtLeast = ((0.8, 4), (0.5, 3), (0.0, 2))
    bus_factor_impact_by_hours: AtLeast = ((40.0, 5), (16.0, 4), (0.0, 3))  # task te hours

    # spi_low / cpi_low: only judged once PV >= this share of BAC (early ratios are noise).
    evm_min_pv_share: float = 0.05
    spi_threshold: float = 0.9  # fires when SPI < this
    spi_probability: Below = ((0.80, 5), (0.85, 4), (0.90, 3))  # by SPI
    spi_impact_by_sv_share: AtLeast = ((0.10, 5), (0.05, 4), (0.0, 3))  # -SV / BAC
    cpi_threshold: float = 0.9  # fires when CPI < this
    cpi_probability: Below = ((0.80, 5), (0.85, 4), (0.90, 3))  # by CPI
    cpi_impact_by_overrun: AtLeast = ((0.20, 5), (0.10, 4), (0.0, 3))  # (EAC - BAC) / BAC

    # low_on_time_probability: Monte Carlo P(finish <= deadline) is low.
    p_on_time_threshold: float = 0.60  # fires when P(on time) < this
    p_on_time_probability: Below = ((0.30, 5), (0.45, 4), (0.60, 3))  # by P(on time)
    p_on_time_impact_by_p80_overrun: AtLeast = ((0.15, 5), (0.05, 4), (0.0, 3))  # P80 vs deadline

    # late_predecessor: an unfinished predecessor's planned end is already in the past.
    late_grace_days: int = 0  # fires when working days late > this
    late_probability_by_days: AtLeast = ((5, 5), (3, 4), (1, 3))  # working days late

    # skill_gap: nobody is eligible for a task (assignment engine's eligibility rule).
    skill_gap_probability: int = 5  # certain: as of today nobody can take it

    # Shared impact table for task-level rules: less slack -> bigger impact.
    impact_by_total_slack_hours: Below = ((0.001, 5), (16.0, 4), (math.inf, 3))


def score_at_least(value: float, bands: AtLeast) -> int:
    for bound, score in bands:
        if value >= bound:
            return score
    return bands[-1][1]


def score_below(value: float, bands: Below) -> int:
    for bound, score in bands:
        if value < bound:
            return score
    return bands[-1][1]


# --------------------------------------------------------------------------------------
# Input / output
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TaskState:
    """Progress and display data the engines' `TaskInput` doesn't carry."""

    title: str
    status: str = "todo"  # todo | in_progress | blocked | done
    percent_complete: float = 0.0


@dataclass(frozen=True, slots=True)
class RiskSnapshot:
    as_of: date
    project_start: date
    tasks: tuple[TaskInput, ...]
    task_state: Mapping[int, TaskState]
    members: tuple[MemberInput, ...]
    member_names: Mapping[int, str]
    assignments: Mapping[int, int | None]  # task id -> current member id
    cpm: CPMResult
    schedule: ScheduleResult | None = None
    forecast: ForecastResult | None = None
    evm: EVMResult | None = None


@dataclass(frozen=True, slots=True)
class RiskFinding:
    rule_key: str
    subject_ref: str  # "project", "task:12", "member:3"
    category: Category
    probability: int  # 1-5
    impact: int  # 1-5
    title: str
    evidence: Evidence = field(default_factory=dict)

    @property
    def score(self) -> int:
        return self.probability * self.impact


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def task_ref(task_id: int) -> str:
    return f"task:{task_id}"


def member_ref(member_id: int) -> str:
    return f"member:{member_id}"


def _label(snap: RiskSnapshot, task_id: int) -> str:
    state = snap.task_state.get(task_id)
    return f"T-{task_id:03d} {state.title}" if state else f"T-{task_id:03d}"


def _member(snap: RiskSnapshot, member_id: int) -> str:
    return snap.member_names.get(member_id, f"Member {member_id}")


def _open(snap: RiskSnapshot, task_id: int) -> bool:
    state = snap.task_state.get(task_id)
    return state is None or state.status != DONE


def _r(value: float) -> float:
    return round(value, 4)


def _window(snap: RiskSnapshot, task_id: int) -> tuple[date, date]:
    """Scheduled window if there is a schedule, else the CPM early window."""
    if snap.schedule is not None:
        for placed in snap.schedule.tasks:
            if placed.task_id == task_id:
                return placed.start, placed.end
    row = next(r for r in snap.cpm.tasks if r.task_id == task_id)
    return calendar.hours_to_window(snap.project_start, row.es, row.ef)


def _eligible(snap: RiskSnapshot, task: TaskInput) -> list[int]:
    window = _window(snap, task.id)
    return [m.id for m in snap.members if is_eligible(task, m, window)[0]]


# --------------------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------------------


def member_overload(snap: RiskSnapshot, cfg: RiskConfig) -> list[RiskFinding]:
    if snap.schedule is None:
        return []
    weeks: dict[int, list[tuple[date, float, float, float]]] = {}
    for w in snap.schedule.loads:
        util = w.hours / w.capacity if w.capacity > 0 else (math.inf if w.hours > 0 else 0.0)
        if util > cfg.overload_utilisation:
            weeks.setdefault(w.member_id, []).append((w.week_start, util, w.hours, w.capacity))

    findings = []
    for member_id, over in sorted(weeks.items()):
        week, peak, hours, cap = max(over, key=lambda x: x[1])
        peak_shown = "no capacity" if math.isinf(peak) else f"peak {peak:.0%}"
        findings.append(
            RiskFinding(
                rule_key="member_overload",
                subject_ref=member_ref(member_id),
                category="resource",
                probability=score_at_least(len(over), cfg.overload_probability_by_weeks),
                impact=score_at_least(peak, cfg.overload_impact_by_peak),
                title=(
                    f"{_member(snap, member_id)} is over capacity in {len(over)} week(s), "
                    f"{peak_shown}"
                ),
                evidence={
                    "weeks_over": len(over),
                    "peak_utilisation": None if math.isinf(peak) else _r(peak),
                    "peak_week_start": week.isoformat(),
                    "peak_hours": _r(hours),
                    "peak_capacity": _r(cap),
                    "threshold": cfg.overload_utilisation,
                },
            )
        )
    return findings


def bus_factor(snap: RiskSnapshot, cfg: RiskConfig) -> list[RiskFinding]:
    critical = {r.task_id: r for r in snap.cpm.tasks if r.critical}
    findings = []
    for task in snap.tasks:
        if task.id not in critical or not _open(snap, task.id) or not task.required_skills:
            continue
        people = _eligible(snap, task)
        if not 0 < len(people) <= cfg.bus_factor_max_people:
            continue  # 0 eligible is a skill gap, not a bus factor
        crit_index = snap.forecast.criticality.get(task.id, 1.0) if snap.forecast else 1.0
        hours = critical[task.id].duration
        names = ", ".join(_member(snap, m) for m in people)
        findings.append(
            RiskFinding(
                rule_key="bus_factor",
                subject_ref=task_ref(task.id),
                category="resource",
                probability=score_at_least(crit_index, cfg.bus_factor_probability_by_criticality),
                impact=score_at_least(hours, cfg.bus_factor_impact_by_hours),
                title=f"{_label(snap, task.id)}: only {names} can do this critical task",
                evidence={
                    "eligible_members": len(people),
                    "criticality_index": _r(crit_index),
                    "task_hours": _r(hours),
                    "max_people": cfg.bus_factor_max_people,
                },
            )
        )
    return findings


def _evm_judgeable(evm: EVMResult | None, cfg: RiskConfig) -> EVMResult | None:
    if evm is None or not evm.bac or evm.pv / evm.bac < Decimal(str(cfg.evm_min_pv_share)):
        return None
    return evm


def spi_low(snap: RiskSnapshot, cfg: RiskConfig) -> list[RiskFinding]:
    evm = _evm_judgeable(snap.evm, cfg)
    if evm is None or evm.spi is None or evm.spi >= cfg.spi_threshold:
        return []
    sv_share = float(-evm.sv / evm.bac) if evm.bac else 0.0
    return [
        RiskFinding(
            rule_key="spi_low",
            subject_ref="project",
            category="schedule",
            probability=score_below(evm.spi, cfg.spi_probability),
            impact=score_at_least(sv_share, cfg.spi_impact_by_sv_share),
            title=f"SPI {evm.spi:.2f} is below {cfg.spi_threshold:.2f}: work is behind plan",
            evidence={
                "spi": _r(evm.spi),
                "threshold": cfg.spi_threshold,
                "pv": str(evm.pv),
                "ev": str(evm.ev),
                "sv": str(evm.sv),
                "bac": str(evm.bac),
            },
        )
    ]


def cpi_low(snap: RiskSnapshot, cfg: RiskConfig) -> list[RiskFinding]:
    evm = _evm_judgeable(snap.evm, cfg)
    if evm is None or evm.cpi is None or evm.cpi >= cfg.cpi_threshold:
        return []
    overrun = float((evm.eac - evm.bac) / evm.bac) if evm.eac is not None and evm.bac else 0.0
    return [
        RiskFinding(
            rule_key="cpi_low",
            subject_ref="project",
            category="cost",
            probability=score_below(evm.cpi, cfg.cpi_probability),
            impact=score_at_least(overrun, cfg.cpi_impact_by_overrun),
            title=(
                f"CPI {evm.cpi:.2f} is below {cfg.cpi_threshold:.2f}: work costs more than planned"
            ),
            evidence={
                "cpi": _r(evm.cpi),
                "threshold": cfg.cpi_threshold,
                "ev": str(evm.ev),
                "ac": str(evm.ac),
                "eac": None if evm.eac is None else str(evm.eac),
                "bac": str(evm.bac),
            },
        )
    ]


def low_on_time_probability(snap: RiskSnapshot, cfg: RiskConfig) -> list[RiskFinding]:
    fc = snap.forecast
    if fc is None or fc.p_on_time is None or fc.p_on_time >= cfg.p_on_time_threshold:
        return []
    deadline = fc.deadline_hours or 0.0
    overrun = (fc.p80 - deadline) / deadline if deadline > 0 else 0.0
    return [
        RiskFinding(
            rule_key="low_on_time_probability",
            subject_ref="project",
            category="schedule",
            probability=score_below(fc.p_on_time, cfg.p_on_time_probability),
            impact=score_at_least(overrun, cfg.p_on_time_impact_by_p80_overrun),
            title=(f"P(on time) is {fc.p_on_time:.0%}, below {cfg.p_on_time_threshold:.0%}"),
            evidence={
                "p_on_time": _r(fc.p_on_time),
                "threshold": cfg.p_on_time_threshold,
                "deadline_hours": _r(deadline),
                "p50_hours": _r(fc.p50),
                "p80_hours": _r(fc.p80),
                "runs": fc.runs,
            },
        )
    ]


def late_predecessor(snap: RiskSnapshot, cfg: RiskConfig) -> list[RiskFinding]:
    if snap.schedule is None:
        return []
    end_of = {t.task_id: t.end for t in snap.schedule.tasks}
    slack = {r.task_id: r.total_slack for r in snap.cpm.tasks}
    findings = []
    for task in snap.tasks:
        if not _open(snap, task.id):
            continue
        late: list[tuple[int, int, date]] = []  # (days late, pred id, planned end)
        for pred in task.predecessors:
            end = end_of.get(pred)
            if end is None or not _open(snap, pred):
                continue
            days = calendar.working_days_between(
                end + timedelta(days=1), snap.as_of + timedelta(days=1)
            )
            if days > cfg.late_grace_days:
                late.append((days, pred, end))
        if not late:
            continue
        days, pred, end = max(late)
        findings.append(
            RiskFinding(
                rule_key="late_predecessor",
                subject_ref=task_ref(task.id),
                category="schedule",
                probability=score_at_least(days, cfg.late_probability_by_days),
                impact=score_below(slack.get(task.id, 0.0), cfg.impact_by_total_slack_hours),
                title=(
                    f"{_label(snap, task.id)} is blocked by {_label(snap, pred)}, "
                    f"{days} working day(s) late"
                ),
                evidence={
                    "predecessor_id": pred,
                    "predecessor_planned_end": end.isoformat(),
                    "working_days_late": days,
                    "late_predecessors": len(late),
                    "total_slack_hours": _r(slack.get(task.id, 0.0)),
                    "as_of": snap.as_of.isoformat(),
                },
            )
        )
    return findings


def skill_gap(snap: RiskSnapshot, cfg: RiskConfig) -> list[RiskFinding]:
    slack = {r.task_id: r.total_slack for r in snap.cpm.tasks}
    findings = []
    for task in snap.tasks:
        if not _open(snap, task.id) or _eligible(snap, task):
            continue
        musts = [s for s in task.required_skills if s.must]
        findings.append(
            RiskFinding(
                rule_key="skill_gap",
                subject_ref=task_ref(task.id),
                category="skill",
                probability=cfg.skill_gap_probability,
                impact=score_below(slack.get(task.id, 0.0), cfg.impact_by_total_slack_hours),
                title=f"No eligible member for {_label(snap, task.id)}",
                evidence={
                    "eligible_members": 0,
                    "team_size": len(snap.members),
                    "must_skills": ", ".join(f"{s.skill}>={s.level}" for s in musts),
                    "total_slack_hours": _r(slack.get(task.id, 0.0)),
                },
            )
        )
    return findings


Rule = Callable[[RiskSnapshot, RiskConfig], list[RiskFinding]]

RULES: tuple[Rule, ...] = (
    member_overload,
    bus_factor,
    spi_low,
    cpi_low,
    low_on_time_probability,
    late_predecessor,
    skill_gap,
)


def detect_risks(snap: RiskSnapshot, config: RiskConfig | None = None) -> list[RiskFinding]:
    """Run every rule; highest P x I first, ties broken by rule and subject (deterministic)."""
    cfg = config or RiskConfig()
    findings = [f for rule in RULES for f in rule(snap, cfg)]
    return sorted(findings, key=lambda f: (-f.score, f.rule_key, f.subject_ref))
