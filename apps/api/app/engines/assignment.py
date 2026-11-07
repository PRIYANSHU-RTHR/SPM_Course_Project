"""Explainable task -> member assignment (plan.md section 3). Pure.

score        = 100 * (0.60 * skill_fit + 0.25 * capacity_fit + 0.15 * balance)
skill_fit    = sum_s w_s * min(level_member_s / level_required_s, 1)   (w normalised)
capacity_fit = clamp(free_hours_in_task_window / task_hours, 0, 1)
balance      = 1 - utilisation / max_team_utilisation   (1 when nobody has work yet)
eligible     = every "must" skill at >= required - 1 AND on leave <= 50% of the window

Greedy assigns tasks one at a time (topological level, then priority, then id), updating
load after each. Optimal solves each topological level ("wave") as a task x member
assignment problem with the Hungarian method (scipy linear_sum_assignment), one task per
member per round, repeating rounds until the wave is placed, then carries load forward.
"""

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.engines import calendar
from app.engines.cpm import topo_sort
from app.engines.estimation import pert
from app.engines.types import (
    AssignmentPlan,
    Candidate,
    MemberInput,
    ScoreBreakdown,
    SkillMatch,
    TaskInput,
    TaskRecommendation,
)

Window = tuple[date, date]  # inclusive working-day range a task is expected to run in
INELIGIBLE_COST = 1e6
TOP_N = 3


@dataclass(frozen=True, slots=True)
class AssignmentWeights:
    skill: float = 0.60
    capacity: float = 0.25
    balance: float = 0.15


@dataclass
class Load:
    """Mutable planning state: hours each member has been given, with their windows."""

    horizon: Window
    committed: dict[int, list[tuple[Window, float]]] = field(default_factory=dict)

    def copy(self) -> "Load":
        return Load(self.horizon, {k: list(v) for k, v in self.committed.items()})

    def add(self, member_id: int, window: Window, hours: float) -> None:
        self.committed.setdefault(member_id, []).append((window, hours))

    def hours_in(self, member_id: int, window: Window) -> float:
        """Committed hours overlapping `window`, spread evenly over each task's working days."""
        total = 0.0
        for (start, end), hours in self.committed.get(member_id, []):
            days = len(calendar.working_days(start, end))
            lo, hi = max(start, window[0]), min(end, window[1])
            if days and lo <= hi:
                total += hours * len(calendar.working_days(lo, hi)) / days
        return total

    def utilisation(self, member: MemberInput) -> float:
        hours = sum(h for _, h in self.committed.get(member.id, []))
        cap = calendar.capacity(member, *self.horizon)
        if cap > 0:
            return hours / cap
        return 0.0 if hours == 0 else math.inf


def is_eligible(task: TaskInput, member: MemberInput, window: Window) -> tuple[bool, str | None]:
    for req in task.required_skills:
        has = member.skills.get(req.skill, 0)
        if req.must and has < req.level - 1:
            return False, f"{req.skill}: level {has}, needs at least {req.level - 1}"
    days = calendar.working_days(*window)
    leave = sum(1 for d in days if calendar.on_leave(member, d))
    if days and leave > len(days) / 2:
        return False, f"on leave {leave} of {len(days)} working days"
    return True, None


def score(
    task: TaskInput,
    member: MemberInput,
    window: Window,
    hours: float,
    load: Load,
    team: Sequence[MemberInput],
    weights: AssignmentWeights | None = None,
) -> ScoreBreakdown:
    w = weights or AssignmentWeights()

    total_weight = sum(r.weight for r in task.required_skills) or 1.0
    matches = tuple(
        SkillMatch(
            skill=r.skill,
            required=r.level,
            has=member.skills.get(r.skill, 0),
            weight=r.weight / total_weight,
            fit=min(member.skills.get(r.skill, 0) / r.level, 1.0),
        )
        for r in task.required_skills
    )
    skill_fit = sum(m.weight * m.fit for m in matches) if matches else 1.0

    free = calendar.capacity(member, *window) - load.hours_in(member.id, window)
    capacity_fit = 1.0 if hours <= 0 else min(max(free / hours, 0.0), 1.0)

    util = load.utilisation(member)
    max_util = max(load.utilisation(m) for m in team)
    balance = 1.0 if max_util == 0 else 1.0 - util / max_util
    if math.isinf(max_util):
        balance = 0.0 if math.isinf(util) else 1.0

    parts = (100 * w.skill * skill_fit, 100 * w.capacity * capacity_fit, 100 * w.balance * balance)
    return ScoreBreakdown(
        total=sum(parts),
        skill_fit=skill_fit,
        capacity_fit=capacity_fit,
        balance=balance,
        skill_part=parts[0],
        capacity_part=parts[1],
        balance_part=parts[2],
        free_hours=max(free, 0.0),
        utilisation=util,
        skills=matches,
    )


def _levels(tasks: Sequence[TaskInput]) -> dict[int, int]:
    by_id = {t.id: t for t in tasks}
    level: dict[int, int] = {}
    for i in topo_sort(tasks):
        level[i] = max((level[p] + 1 for p in by_id[i].predecessors), default=0)
    return level


def _horizon(windows: Mapping[int, Window]) -> Window:
    return min(s for s, _ in windows.values()), max(e for _, e in windows.values())


def _evaluate(
    task: TaskInput,
    members: Sequence[MemberInput],
    window: Window,
    hours: float,
    load: Load,
    weights: AssignmentWeights | None,
) -> tuple[list[Candidate], list[tuple[int, str]]]:
    """All eligible candidates best-first (ties -> lower member id), plus ineligible reasons."""
    ok: list[Candidate] = []
    rejected: list[tuple[int, str]] = []
    for m in members:
        eligible, reason = is_eligible(task, m, window)
        if eligible:
            ok.append(Candidate(m.id, score(task, m, window, hours, load, members, weights)))
        else:
            rejected.append((m.id, reason or "ineligible"))
    ok.sort(key=lambda c: (-c.score.total, c.member_id))
    return ok, rejected


def _plan(
    mode: str,
    recs: dict[int, TaskRecommendation],
    order: Sequence[int],
    members: Sequence[MemberInput],
    load: Load,
) -> AssignmentPlan:
    ordered = tuple(recs[i] for i in order)
    util = {m.id: load.utilisation(m) for m in members}
    finite = [u for u in util.values() if math.isfinite(u)]
    return AssignmentPlan(
        mode=mode,
        recommendations=ordered,
        utilisation=util,
        total_score=sum(r.score.total for r in ordered if r.score),
        utilisation_std=statistics.pstdev(finite) if finite else 0.0,
        unassigned=sum(1 for r in ordered if r.member_id is None),
    )


def _inputs(
    tasks: Sequence[TaskInput], hours: Mapping[int, float] | None
) -> tuple[dict[int, TaskInput], dict[int, float], dict[int, int], list[int]]:
    by_id = {t.id: t for t in tasks}
    h = {t.id: (hours[t.id] if hours else pert(t).te) for t in tasks}
    level = _levels(tasks)
    order = sorted(by_id, key=lambda i: (level[i], by_id[i].priority, i))
    return by_id, h, level, order


def recommend_greedy(
    tasks: Sequence[TaskInput],
    members: Sequence[MemberInput],
    windows: Mapping[int, Window],
    hours: Mapping[int, float] | None = None,
    weights: AssignmentWeights | None = None,
) -> AssignmentPlan:
    """Assign one task at a time to its best-scoring eligible member."""
    by_id, h, _, order = _inputs(tasks, hours)
    load = Load(_horizon(windows)) if windows else Load((date.min, date.min))
    recs: dict[int, TaskRecommendation] = {}
    for i in order:
        ok, rejected = _evaluate(by_id[i], members, windows[i], h[i], load, weights)
        best = ok[0] if ok else None
        if best:
            load.add(best.member_id, windows[i], h[i])
        recs[i] = TaskRecommendation(
            task_id=i,
            member_id=best.member_id if best else None,
            score=best.score if best else None,
            candidates=tuple(ok[:TOP_N]),
            ineligible=tuple(rejected),
        )
    return _plan("greedy", recs, order, members, load)


def recommend_optimal(
    tasks: Sequence[TaskInput],
    members: Sequence[MemberInput],
    windows: Mapping[int, Window],
    hours: Mapping[int, float] | None = None,
    weights: AssignmentWeights | None = None,
    base_load: Load | None = None,
) -> AssignmentPlan:
    """Per topological wave, maximise total score with the Hungarian method.

    `base_load` is work members already have (e.g. their other tasks when only a few tasks
    are re-planned); it is copied, never modified.
    """
    by_id, h, level, order = _inputs(tasks, hours)
    if base_load is not None:
        load = base_load.copy()
    else:
        load = Load(_horizon(windows)) if windows else Load((date.min, date.min))
    recs: dict[int, TaskRecommendation] = {}

    for wave in sorted(set(level.values())):
        pending = [i for i in order if level[i] == wave]
        while pending:
            evaluated = {
                i: _evaluate(by_id[i], members, windows[i], h[i], load, weights) for i in pending
            }
            for i in [i for i in pending if not evaluated[i][0]]:  # nobody eligible
                recs[i] = TaskRecommendation(i, None, None, (), tuple(evaluated[i][1]))
                pending.remove(i)
            if not pending:
                break

            col = {m.id: k for k, m in enumerate(members)}
            cost = np.full((len(pending), len(members)), INELIGIBLE_COST)
            for r, i in enumerate(pending):
                for c in evaluated[i][0]:
                    cost[r, col[c.member_id]] = 100 - c.score.total
            rows, cols = linear_sum_assignment(cost)

            placed = []
            for r, k in zip(rows, cols, strict=True):
                if cost[r, k] >= INELIGIBLE_COST:
                    continue
                i, member_id = pending[r], members[k].id
                ok, rejected = evaluated[i]
                chosen = next(c for c in ok if c.member_id == member_id)
                recs[i] = TaskRecommendation(
                    i, member_id, chosen.score, tuple(ok[:TOP_N]), tuple(rejected)
                )
                placed.append((i, member_id))
            for i, member_id in placed:  # commit after the round: one shared load state per round
                load.add(member_id, windows[i], h[i])
                pending.remove(i)

    return _plan("optimal", recs, order, members, load)


@dataclass(frozen=True, slots=True)
class PlanComparison:
    greedy_total: float
    optimal_total: float
    greedy_utilisation_std: float
    optimal_utilisation_std: float
    greedy_unassigned: int
    optimal_unassigned: int


def compare(greedy: AssignmentPlan, optimal: AssignmentPlan) -> PlanComparison:
    return PlanComparison(
        greedy_total=greedy.total_score,
        optimal_total=optimal.total_score,
        greedy_utilisation_std=greedy.utilisation_std,
        optimal_utilisation_std=optimal.utilisation_std,
        greedy_unassigned=greedy.unassigned,
        optimal_unassigned=optimal.unassigned,
    )
