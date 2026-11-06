"""Assignment strategy evaluation for the report (plan.md section 6). No DB, no engine changes.

Scenarios: the demo seed team/project plus 3 synthetic teams (fixed seeds).
Strategies: random and round-robin (both only among eligible members), greedy, optimal.
Every strategy is scored with the same engine formula, in the same task order, with load
updated after each pick, so totals are comparable. Per strategy we also run the resource
scheduler for the makespan, and a resource-aware P(on time): Beta-PERT durations sampled
with the Monte Carlo engine, each sample scheduled with that strategy's assignments.

Run from apps/api:  uv run python -m scripts.evaluate   (writes docs/evaluation.md)
"""

import math
import random
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np

from app import seed as demo
from app.engines import calendar
from app.engines.assignment import (
    Load,
    is_eligible,
    recommend_greedy,
    recommend_optimal,
    score,
)
from app.engines.cpm import cpm, topo_sort
from app.engines.estimation import path_pert, pert
from app.engines.montecarlo import forecast, sample_durations
from app.engines.scheduler import schedule
from app.engines.types import MemberInput, RequiredSkill, TaskInput

START = date(2026, 11, 2)  # a Monday; fixed so the report is reproducible
SEED = 42
SIM_RUNS = 300  # resource-aware simulation runs per strategy
OUT = Path(__file__).resolve().parents[3] / "docs" / "evaluation.md"
STRATEGIES = ("random", "round-robin", "greedy", "optimal")


@dataclass(frozen=True)
class Scenario:
    name: str
    tasks: list[TaskInput]
    members: list[MemberInput]
    deadline_days: int  # working days from START, inclusive


@dataclass(frozen=True)
class Row:
    strategy: str
    total: float
    mean: float
    util_std: float
    unassigned: int
    makespan_days: int
    p_on_time: float


# -- scenarios ----------------------------------------------------------------------------


def demo_scenario() -> Scenario:
    tasks = [
        TaskInput(
            id=i,
            o=t.o,
            m=t.m,
            p=t.p,
            priority=t.priority,
            required_skills=tuple(
                RequiredSkill(str(s["skill"]), int(s["level"]), bool(s["must"]))
                for s in demo.parse_skills(t.skills)
            ),
            predecessors=tuple(p for p, s in demo.DEPENDENCIES if s == i),
        )
        for i, t in enumerate(demo.TASKS, start=1)
    ]
    members = [
        MemberInput(id=i, skills=dict(skills), hours_per_week=hours)
        for i, (_, _, hours, skills) in enumerate(demo.MEMBERS, start=1)
    ]
    return Scenario(
        "Demo seed (Campus Food-Ordering App)", tasks, members, demo.DEADLINE_WORKING_DAYS
    )


def synthetic_scenario(k: int) -> Scenario:
    rng = random.Random(SEED + k)
    skills = list(demo.SKILLS)
    members = []
    for i in range(1, rng.randint(6, 10) + 1):
        known = rng.sample(skills, rng.randint(3, 6))
        members.append(
            MemberInput(
                id=i,
                skills={s: rng.randint(1, 5) for s in known},
                hours_per_week=rng.choice((20, 30, 40, 40)),
            )
        )
    # Only skills the team has, at most one level above its best person, so tasks are staffable
    # (eligibility allows required - 1) and strategies are compared on the same tasks.
    best: dict[str, int] = {}
    for m in members:
        for skill, level in m.skills.items():
            best[skill] = max(best.get(skill, 0), level)
    tasks = []
    for i in range(1, rng.randint(20, 40) + 1):
        needed = rng.sample(sorted(best), rng.randint(1, 2))
        m = rng.randint(6, 30)
        preds = rng.sample(range(1, i), min(i - 1, rng.choice((0, 1, 1, 2)))) if i > 1 else []
        tasks.append(
            TaskInput(
                id=i,
                o=max(2, m - rng.randint(2, 8)),
                m=m,
                p=m + rng.randint(4, 20),
                priority=rng.randint(1, 5),
                required_skills=tuple(
                    RequiredSkill(s, rng.randint(2, min(5, best[s] + 1)), must=(n == 0))
                    for n, s in enumerate(needed)
                ),
                predecessors=tuple(sorted(preds)),
            )
        )
    # Deadline: the larger of the critical path and total effort at 50% of team capacity (skill
    # bottlenecks keep real utilisation well below 100%), plus 20%: tight but feasible.
    cpm_days = cpm(tasks).project_duration / calendar.HOURS_PER_DAY
    team_daily = sum(m.hours_per_week for m in members) / calendar.WORK_DAYS_PER_WEEK
    effort_days = sum(pert(t).te for t in tasks) / (0.5 * team_daily)
    deadline = math.ceil(max(cpm_days, effort_days) * 1.2)
    return Scenario(f"Synthetic team {k} (seed {SEED + k})", tasks, members, deadline)


# -- strategies ---------------------------------------------------------------------------


def _windows(sc: Scenario) -> dict[int, tuple[date, date]]:
    return {r.task_id: calendar.hours_to_window(START, r.es, r.ef) for r in cpm(sc.tasks).tasks}


def _baseline(sc: Scenario, strategy: str) -> dict[int, int | None]:
    """Random / round-robin picks among eligible members, in topological order."""
    windows = _windows(sc)
    by_id = {t.id: t for t in sc.tasks}
    rng = random.Random(SEED)
    cursor = 0
    picks: dict[int, int | None] = {}
    for i in topo_sort(sc.tasks):
        ok = [m for m in sc.members if is_eligible(by_id[i], m, windows[i])[0]]
        if not ok:
            picks[i] = None
        elif strategy == "random":
            picks[i] = rng.choice(ok).id
        else:  # round-robin: next member in team order who is eligible
            ids = [m.id for m in sc.members]
            for step in range(len(ids)):
                candidate = ids[(cursor + step) % len(ids)]
                if any(m.id == candidate for m in ok):
                    picks[i] = candidate
                    cursor = (cursor + step + 1) % len(ids)
                    break
    return picks


def _assignments(sc: Scenario, strategy: str) -> dict[int, int | None]:
    if strategy in ("random", "round-robin"):
        return _baseline(sc, strategy)
    engine = recommend_greedy if strategy == "greedy" else recommend_optimal
    plan = engine(sc.tasks, sc.members, _windows(sc))
    return {r.task_id: r.member_id for r in plan.recommendations}


def _score_plan(sc: Scenario, picks: dict[int, int | None]) -> tuple[float, int, float]:
    """Re-score any assignment with the engine formula, same order and load updates for all."""
    windows = _windows(sc)
    by_id = {t.id: t for t in sc.tasks}
    members = {m.id: m for m in sc.members}
    load = Load((min(s for s, _ in windows.values()), max(e for _, e in windows.values())))
    total, unassigned = 0.0, 0
    for i in topo_sort(sc.tasks):
        member_id = picks.get(i)
        if member_id is None:
            unassigned += 1
            continue
        hours = pert(by_id[i]).te
        total += score(by_id[i], members[member_id], windows[i], hours, load, sc.members).total
        load.add(member_id, windows[i], hours)
    utils = [load.utilisation(m) for m in sc.members]
    return total, unassigned, statistics.pstdev(u for u in utils if math.isfinite(u))


def _deadline(sc: Scenario) -> date:
    return calendar.add_working_days(START, sc.deadline_days - 1)


def _resource_p_on_time(sc: Scenario, picks: dict[int, int | None]) -> float:
    rng = np.random.default_rng(SEED)
    draws = sample_durations(sc.tasks, SIM_RUNS, rng)
    deadline = _deadline(sc)
    ids = [t.id for t in sc.tasks]
    on_time = 0
    for run in draws:
        durations = dict(zip(ids, (float(d) for d in run), strict=True))
        if schedule(sc.tasks, picks, sc.members, START, durations).finish <= deadline:
            on_time += 1
    return on_time / SIM_RUNS


def evaluate(sc: Scenario, strategy: str) -> Row:
    picks = _assignments(sc, strategy)
    total, unassigned, util_std = _score_plan(sc, picks)
    finish = schedule(sc.tasks, picks, sc.members, START).finish
    assigned = len(sc.tasks) - unassigned
    return Row(
        strategy=strategy,
        total=total,
        mean=total / assigned if assigned else 0.0,
        util_std=util_std,
        unassigned=unassigned,
        makespan_days=len(calendar.working_days(START, finish)),
        p_on_time=_resource_p_on_time(sc, picks),
    )


# -- report -------------------------------------------------------------------------------


def strategy_table(rows: list[Row]) -> str:
    lines = [
        "| Strategy | Total score | Mean score | Utilisation std-dev | Unassigned "
        "| Makespan (working days) | P(on time) |",
        "|---|--:|--:|--:|--:|--:|--:|",
    ]
    for r in rows:
        lines.append(
            f"| {r.strategy} | {r.total:.1f} | {r.mean:.1f} | {r.util_std:.3f} | {r.unassigned} "
            f"| {r.makespan_days} | {r.p_on_time:.0%} |"
        )
    return "\n".join(lines)


def forecast_sanity(sc: Scenario) -> str:
    """Network only (no resources): Monte Carlo vs deterministic CPM and PERT sigma."""
    result = cpm(sc.tasks)
    by_id = {t.id: t for t in sc.tasks}
    path = path_pert([by_id[i] for i in result.critical_paths[0]])
    mc = forecast(sc.tasks, sc.deadline_days * calendar.HOURS_PER_DAY, runs=5000, seed=SEED)
    spread = (mc.p80 - mc.p50) / 0.8416  # normal z(0.80): sigma implied by the simulation
    return (
        f"CPM finish {result.project_duration:.1f} h; PERT along the critical path "
        f"{path.te:.1f} h +/- {path.std:.1f} h; Monte Carlo mean {mc.mean:.1f} h, "
        f"P50 {mc.p50:.1f} h, P80 {mc.p80:.1f} h (implied sigma ~ {spread:.1f} h); "
        f"network-only P(on time) {mc.p_on_time or 0:.0%}"
    )


def summary_table(results: list[tuple[Scenario, list[Row], float]]) -> str:
    lines = [
        "| Scenario | Best mean score | Shortest makespan | P(on time) network-only "
        "| P(on time) resource-aware, optimal |",
        "|---|---|---|--:|--:|",
    ]
    for sc, rows, network in results:
        top = max(rows, key=lambda r: r.mean)
        fast = min(rows, key=lambda r: (r.makespan_days, -r.mean))
        opt = next(r for r in rows if r.strategy == "optimal")
        lines.append(
            f"| {sc.name} | {top.strategy} ({top.mean:.1f}) "
            f"| {fast.strategy} ({fast.makespan_days} d) | {network:.0%} | {opt.p_on_time:.0%} |"
        )
    return "\n".join(lines)


HOW_TO_READ = """## How to read this

- The re-scored total replays tasks one by one and scores each pick against the load so far.
  That is exactly greedy's own objective, so greedy can edge out optimal on this column.
  Optimal maximises the summed score of each topological wave at once; its advantage shows
  in the makespan and the utilisation spread rather than in the re-scored total.
- Neither greedy nor optimal looks at the calendar when choosing, so makespan is a side
  effect, not a target. Making the assignment schedule-aware is the obvious next step.
- The network-only forecast (CPM + Monte Carlo) assumes every task gets a full-time person
  the moment it is ready. The resource-aware P(on time) is the more honest number; the gap
  between the two columns is the cost of limited people and skills.
- Synthetic deadlines come from a formula (critical path vs effort at 50% team capacity,
  plus 20%), not from real projects, so compare strategies within a scenario, not across."""


def render(scenarios: list[Scenario]) -> str:
    started = time.perf_counter()
    parts = [
        "# Assignment strategy evaluation",
        "",
        "Generated by `apps/api/scripts/evaluate.py` (`make evaluate`). Fixed seeds, so the "
        f"numbers are reproducible. Project start {START} (Monday), 8 h project days, Mon-Fri.",
        "",
        "- **Score**: the plan.md section 3 formula (0.60 skill, 0.25 capacity, 0.15 balance) for "
        "the chosen member, every strategy re-scored in the same task order with load updated "
        "after each pick. Random and round-robin only pick eligible members.",
        "- **Makespan**: resource-constrained schedule (Step 09) with expected (PERT) hours.",
        f"- **P(on time)**: {SIM_RUNS} Beta-PERT samples (Step 10 sampler), each run "
        "through the resource scheduler with that strategy's assignments; share finishing "
        "by the deadline. This includes resource contention, unlike the network-only forecast.",
        "",
    ]
    results = []
    for sc in scenarios:
        rows = [evaluate(sc, s) for s in STRATEGIES]
        network = forecast(sc.tasks, sc.deadline_days * calendar.HOURS_PER_DAY, 5000, SEED)
        results.append((sc, rows, network.p_on_time or 0.0))
        parts += [
            f"## {sc.name}",
            "",
            f"{len(sc.tasks)} tasks, {len(sc.members)} members, deadline {_deadline(sc)} "
            f"({sc.deadline_days} working days).",
            "",
            strategy_table(rows),
            "",
            f"Forecast sanity (network only): {forecast_sanity(sc)}.",
            "",
        ]
    parts += ["## Summary", "", summary_table(results), "", HOW_TO_READ, ""]
    parts.append(f"_Runtime {time.perf_counter() - started:.1f} s._")
    return "\n".join(parts) + "\n"


def scenarios() -> list[Scenario]:
    return [demo_scenario(), *(synthetic_scenario(k) for k in (1, 2, 3))]


def main() -> None:
    report = render(scenarios())
    OUT.write_text(report, encoding="utf-8")
    sys.stdout.write(report)


if __name__ == "__main__":
    main()
