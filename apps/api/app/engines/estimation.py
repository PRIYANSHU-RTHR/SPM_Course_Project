"""PERT three-point and COCOMO II post-architecture estimation. Pure functions, no I/O.

References
- PERT: Malcolm et al. (1959); formulas as in Pressman, *Software Engineering*, ch. on
  project scheduling: te = (o + 4m + p) / 6, sigma = (p - o) / 6.
- COCOMO II.2000: Boehm et al., *Software Cost Estimation with COCOMO II* (2000), and the
  COCOMO II Model Definition Manual v2000: A=2.94, B=0.91, C=3.67, D=0.28.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from app.engines.types import CocomoResult, PathPert, PertEstimate, TaskInput

# COCOMO II.2000 nominal scale-factor ratings (Model Definition Manual, Table 10).
NOMINAL_SCALE_FACTORS: Mapping[str, float] = MappingProxyType(
    {"PREC": 3.72, "FLEX": 3.04, "RESL": 4.24, "TEAM": 3.29, "PMAT": 4.68}
)

# Person-month in COCOMO II = 152 working hours.
HOURS_PER_PM = 152.0
# shortcut: one fixed productivity for KSLOC-from-hours; calibrate per team once real data exists.
DEFAULT_LOC_PER_HOUR = 10.0


@dataclass(frozen=True, slots=True)
class CocomoParams:
    a: float = 2.94
    b: float = 0.91
    c: float = 3.67
    d: float = 0.28
    scale_factors: Mapping[str, float] = field(default_factory=lambda: NOMINAL_SCALE_FACTORS)
    # Post-architecture effort multipliers; empty = all nominal (1.0).
    effort_multipliers: Mapping[str, float] = field(default_factory=dict)


def pert(task: TaskInput) -> PertEstimate:
    te = (task.o + 4 * task.m + task.p) / 6
    std = (task.p - task.o) / 6
    return PertEstimate(task_id=task.id, te=te, variance=std**2, std=std)


def normal_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def path_pert(tasks: Iterable[TaskInput], target: float | None = None) -> PathPert:
    """Sum te and variance along a path; optionally P(finish <= target) via the normal approx."""
    estimates = [pert(t) for t in tasks]
    te = sum(e.te for e in estimates)
    std = math.sqrt(sum(e.variance for e in estimates))
    probability = None
    if target is not None:
        if std == 0:
            probability = 1.0 if target >= te else 0.0
        else:
            probability = normal_cdf((target - te) / std)
    return PathPert(
        task_ids=tuple(e.task_id for e in estimates),
        te=te,
        std=std,
        target=target,
        probability=probability,
    )


def cocomo2(ksloc: float, params: CocomoParams | None = None) -> CocomoResult:
    if ksloc <= 0:
        raise ValueError(f"ksloc must be > 0, got {ksloc}")
    p = params or CocomoParams()
    exponent = p.b + 0.01 * sum(p.scale_factors.values())
    effort = p.a * ksloc**exponent * math.prod(p.effort_multipliers.values())
    f = p.d + 0.2 * (exponent - p.b)
    tdev = p.c * effort**f
    return CocomoResult(
        ksloc=ksloc,
        exponent=exponent,
        effort_pm=effort,
        tdev_months=tdev,
        avg_staff=effort / tdev,
    )


def ksloc_from_hours(hours: float, loc_per_hour: float = DEFAULT_LOC_PER_HOUR) -> float:
    """Size proxy for COCOMO when only effort hours exist.

    Assumption: delivered code scales linearly with effort at `loc_per_hour`
    (default 10 LOC/h ~= 1,520 LOC per person-month, mid-range for business web apps).
    This is circular by nature (hours -> size -> effort), so the COCOMO figure is a
    top-down cross-check of the bottom-up PERT total, not an independent estimate.
    """
    if hours < 0 or loc_per_hour <= 0:
        raise ValueError("hours must be >= 0 and loc_per_hour > 0")
    return hours * loc_per_hour / 1000
