"""Shared input/output contract for every engine.

Engines are pure: services build these inputs from the DB and turn the outputs into API
schemas. All hours are floats, all dates are `date`, IDs are the DB integer ids.
Result types for Steps 07-11 are placeholders that fix the field names now; each step
fills in its engine against them (and may add fields, but should not rename these).
"""

from dataclasses import dataclass, field
from datetime import date

# --------------------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RequiredSkill:
    """One skill a task needs (mirrors one item of `task.required_skills`)."""

    skill: str  # skill name from the `skill` table vocabulary
    level: int  # required level, 1-5
    must: bool = True  # must-have (eligibility gate) vs nice-to-have (only affects score)
    weight: float = 1.0  # relative weight in skill_fit; normalised by the assignment engine


@dataclass(frozen=True, slots=True)
class TaskInput:
    """A task as every engine sees it."""

    id: int
    o: float  # optimistic hours
    m: float  # most-likely hours
    p: float  # pessimistic hours
    priority: int = 3  # 1 (highest) - 5 (lowest)
    required_skills: tuple[RequiredSkill, ...] = ()
    predecessors: tuple[int, ...] = ()  # ids of tasks that must finish first (FS)

    def __post_init__(self) -> None:
        if not 0 <= self.o <= self.m <= self.p:
            raise ValueError(
                f"task {self.id}: need 0 <= o <= m <= p, got {self.o}/{self.m}/{self.p}"
            )


@dataclass(frozen=True, slots=True)
class LeaveRange:
    """Inclusive date range when a member has zero capacity."""

    start: date
    end: date


@dataclass(frozen=True, slots=True)
class MemberInput:
    """A team member as every engine sees it."""

    id: int
    skills: dict[str, int]  # skill name -> level 1-5
    hours_per_week: float  # normal working capacity
    leave: tuple[LeaveRange, ...] = ()


# --------------------------------------------------------------------------------------
# Step 06 — estimation
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PertEstimate:
    """Three-point (beta) estimate for one task."""

    task_id: int
    te: float  # expected hours, (o + 4m + p) / 6
    variance: float  # ((p - o) / 6) ** 2
    std: float  # sqrt(variance)


@dataclass(frozen=True, slots=True)
class PathPert:
    """PERT totals along a chain of tasks (normally the critical path)."""

    task_ids: tuple[int, ...]
    te: float  # sum of te along the path, hours
    std: float  # sqrt of summed variances, hours
    target: float | None = None  # T in hours, if a probability was asked for
    probability: float | None = None  # P(path finishes <= target), normal approximation


@dataclass(frozen=True, slots=True)
class CocomoResult:
    """COCOMO II post-architecture estimate."""

    ksloc: float  # size used, thousands of source lines
    exponent: float  # E = B + 0.01 * sum(scale factors)
    effort_pm: float  # person-months, A * KSLOC^E * prod(EM)
    tdev_months: float  # schedule, C * PM^F with F = D + 0.2 * (E - B)
    avg_staff: float  # effort_pm / tdev_months


# --------------------------------------------------------------------------------------
# Steps 07-11 — placeholders (field names fixed now, engines come later)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CPMTask:
    task_id: int
    duration: float  # hours (te)
    es: float  # earliest start, hours from project start
    ef: float  # earliest finish
    ls: float  # latest start
    lf: float  # latest finish
    total_slack: float  # ls - es
    free_slack: float  # min(ES of successors) - ef
    critical: bool  # total_slack == 0


@dataclass(frozen=True, slots=True)
class CPMResult:
    tasks: tuple[CPMTask, ...]
    project_duration: float  # hours
    critical_paths: tuple[tuple[int, ...], ...]  # every zero-slack chain, start -> end


@dataclass(frozen=True, slots=True)
class ScheduledTask:
    task_id: int
    member_id: int | None
    start: date
    end: date


@dataclass(frozen=True, slots=True)
class MemberWeekLoad:
    member_id: int
    week_start: date  # Monday
    hours: float
    capacity: float


@dataclass(frozen=True, slots=True)
class ScheduleResult:
    tasks: tuple[ScheduledTask, ...]
    loads: tuple[MemberWeekLoad, ...]
    finish: date


@dataclass(frozen=True, slots=True)
class ForecastResult:
    runs: int
    seed: int
    p_on_time: float  # P(finish <= deadline)
    p50: float  # hours from project start
    p80: float
    p95: float
    histogram: tuple[tuple[float, int], ...]  # (bin start hours, count)
    cdf: tuple[tuple[float, float], ...]  # (hours, cumulative probability)
    criticality: dict[int, float] = field(default_factory=dict)  # task id -> share of runs critical


@dataclass(frozen=True, slots=True)
class EVMPoint:
    on: date
    pv: float  # hours of planned value (convert to money in the service)
    ev: float
    ac: float


@dataclass(frozen=True, slots=True)
class EVMResult:
    bac: float
    pv: float
    ev: float
    ac: float
    sv: float  # ev - pv
    cv: float  # ev - ac
    spi: float  # ev / pv
    cpi: float  # ev / ac
    eac: float  # bac / cpi
    etc: float  # eac - ac
    vac: float  # bac - eac
    tcpi: float  # (bac - ev) / (bac - ac)
    series: tuple[EVMPoint, ...] = ()
