"""Deterministic demo data for "Campus Food-Ordering App". Run with `make seed`.

WARNING: seeding wipes every OrchestrAI table in the database at DATABASE_URL, then recreates
the demo data. Same `seed` value and same `as_of` date always give identical rows and ids.

README: knobs that move the demo numbers (tune these, not the engines)
- P(on time): DEADLINE_WORKING_DAYS. Each working day is 8 h on the Monte Carlo clock.
- Spread of the forecast: the o/m/p hours in TASKS, mainly on the critical path, which is
  T-001 > T-002 > T-010 > T-011 > T-012 > T-013 > T-015 > T-021 > T-023 > T-025.
- SPI: percent_complete in TASKS and DAYS_ELAPSED. Keep TARGET_SPI equal to what the engine reports.
- CPI: actual_hours in TASKS.
- How much leave hurts: who owns T-011 and T-012, and how few members have payments >= 3.
- Snapshot wobble only: SIM_SEED. It never changes the final EV or AC.
"""

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from random import Random

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session_factory
from app.models import (
    Assignment,
    AssignmentSource,
    Availability,
    AvailabilityKind,
    Base,
    Dependency,
    Epic,
    Member,
    MemberSkill,
    Project,
    Skill,
    Snapshot,
    Task,
    TaskStatus,
)
from app.services.risk_service import refresh_risks

CENTS = Decimal("0.01")
HOURS_PER_DAY = 8.0  # one project day of effort, matching the engines' working calendar
DAYS_ELAPSED = 15  # working days between project start and today: 3 weeks
SNAPSHOT_DAYS = 10  # 2 weeks of working-day snapshots, ending today
# Tuned so the resource-adjusted forecast (services/scenario.py, as on every page) gives about
# 80% P(on time); the plan.md demo then reads 82% -> 11% (one week of leave) -> 58% approved.
DEADLINE_WORKING_DAYS = 34
TARGET_SPI = Decimal("0.94")  # sets stored PV; matches the EVM engine on this data
HOURLY_RATE = Decimal("850.00")
BUDGET = Decimal("520000.00")
SCORE_WEIGHTS = (0.60, 0.25, 0.15)  # skill, capacity, balance: plan.md section 3

SKILLS = (
    "react",
    "typescript",
    "nodejs",
    "python",
    "fastapi",
    "postgres",
    "mongodb",
    "docker",
    "devops",
    "testing",
    "ui-design",
    "android",
    "payments",
    "security",
)

# Demo story roles from plan.md section 4:
#   "Bob"   = Aarav Mehta: strongest backend and the only payments 4, so his leave hurts.
#   "Eva"   = Diya Nair: the runner-up who can take over backend work.
#   "Alice" = Kabir Singh: a weaker third candidate.
MEMBERS: tuple[tuple[str, str, float, dict[str, int]], ...] = (
    (
        "Aarav Mehta",
        "Backend lead",
        40,
        {"fastapi": 5, "postgres": 4, "python": 4, "payments": 4, "security": 3, "docker": 2},
    ),
    (
        "Diya Nair",
        "Full-stack engineer",
        40,
        {"fastapi": 4, "postgres": 3, "react": 3, "typescript": 3, "payments": 3},
    ),
    (
        "Kabir Singh",
        "Backend engineer",
        36,
        {"nodejs": 4, "fastapi": 3, "python": 3, "mongodb": 3, "postgres": 2},
    ),
    ("Meera Iyer", "Frontend lead", 40, {"react": 5, "typescript": 4, "ui-design": 3}),
    (
        "Rohan Gupta",
        "Frontend engineer",
        32,
        {"ui-design": 4, "react": 3, "typescript": 3, "android": 2},
    ),
    (
        "Sneha Kulkarni",
        "QA engineer",
        30,
        {"testing": 5, "python": 3, "typescript": 2, "security": 2},
    ),
    (
        "Arjun Rao",
        "DevOps engineer",
        36,
        {"docker": 5, "devops": 5, "postgres": 3, "security": 4, "fastapi": 2},
    ),
    (
        "Ishita Sharma",
        "Android engineer (part-time)",
        20,
        {"android": 4, "react": 2, "payments": 2},
    ),
)

EPICS = ("Auth", "Menu & Catalogue", "Ordering & Payments", "Vendor Dashboard", "Release")


@dataclass(frozen=True)
class TaskSeed:
    epic: int  # index into EPICS
    title: str
    o: float
    m: float
    p: float
    priority: int
    skills: str  # "react:3!" means react level 3, must-have
    status: TaskStatus = TaskStatus.TODO
    percent: float = 0
    actual: float = 0
    owner: str | None = None  # member name
    fit: tuple[float, float] | None = None  # capacity_fit and balance of the stored assignment


DONE = TaskStatus.DONE
STARTED = TaskStatus.IN_PROGRESS
BLOCKED = TaskStatus.BLOCKED
AARAV, DIYA, KABIR, MEERA, ROHAN, ARJUN = (
    "Aarav Mehta", "Diya Nair", "Kabir Singh", "Meera Iyer", "Rohan Gupta", "Arjun Rao",
)  # fmt: skip

# Order sets the ids: the first row is T-001. T-012 is blocked, not started, but already owned:
# that is why Aarav's leave delays the critical path.
# fmt: off
TASKS: tuple[TaskSeed, ...] = (
    TaskSeed(0, "Define auth flows and session model",      12, 18, 28, 2, "security:3!,fastapi:2",  DONE,    100, 18, AARAV, (0.9, 0.6)),
    TaskSeed(0, "Student sign-up with campus email OTP",    20, 28, 40, 1, "fastapi:3!,postgres:2",  DONE,    100, 28, DIYA,  (0.85, 0.7)),
    TaskSeed(0, "Role-based access for vendors and admins", 10, 16, 24, 2, "fastapi:3!,security:3",  DONE,    100, 16, KABIR, (0.8, 0.5)),
    TaskSeed(0, "Login and profile screens",                12, 18, 28, 2, "react:3!,typescript:2",  DONE,    100, 18, MEERA, (0.95, 0.8)),
    TaskSeed(1, "Menu and catalogue schema",                10, 16, 24, 1, "postgres:3!,fastapi:2",  DONE,    100, 15, DIYA,  (0.9, 0.65)),
    TaskSeed(1, "Catalogue CRUD API",                       18, 26, 38, 1, "fastapi:3!",             DONE,    100, 26, KABIR, (0.75, 0.6)),
    TaskSeed(1, "Menu image upload and storage",             8, 14, 24, 3, "fastapi:2!,devops:2",    DONE,    100, 13, ARJUN, (0.8, 0.75)),
    TaskSeed(1, "Search and dietary filters",               12, 20, 32, 3, "postgres:3!,fastapi:3",  DONE,    100, 19, DIYA,  (0.7, 0.55)),
    TaskSeed(1, "Menu browsing screens",                    16, 24, 36, 2, "react:3!,ui-design:2",   DONE,    100, 23, ROHAN, (0.85, 0.7)),
    TaskSeed(2, "Order state machine",                      18, 26, 38, 1, "fastapi:4!,postgres:3",  DONE,    100, 26, AARAV, (0.7, 0.4)),
    TaskSeed(2, "Cart and checkout API",                    24, 32, 40, 1, "fastapi:4!",             STARTED,  90, 28, AARAV, (0.65, 0.35)),
    TaskSeed(2, "Payment gateway integration",              24, 34, 48, 1, "payments:4!,security:3", BLOCKED,   0,  0, AARAV, (0.6, 0.35)),
    TaskSeed(2, "Payment webhooks and retries",             14, 22, 34, 1, "payments:3!,fastapi:3"),
    TaskSeed(2, "Cart and checkout screens",                18, 26, 38, 1, "react:3!,typescript:3"),
    TaskSeed(2, "Live order tracking",                      22, 30, 40, 2, "fastapi:3!,react:3"),
    TaskSeed(2, "Android wrapper for students",             14, 24, 38, 3, "android:3!"),
    TaskSeed(3, "Vendor order queue API",                   12, 20, 30, 2, "fastapi:3!",             DONE,    100, 19, KABIR, (0.75, 0.6)),
    TaskSeed(3, "Vendor dashboard screens",                 20, 28, 40, 2, "react:3!,ui-design:3",   STARTED,  60, 16, MEERA, (0.8, 0.7)),
    TaskSeed(3, "Daily sales report",                        8, 12, 20, 4, "postgres:2!,react:2",    STARTED,  50,  6, DIYA,  (0.8, 0.6)),
    TaskSeed(3, "Stock and availability toggles",            6, 10, 16, 3, "fastapi:2!,react:2",     DONE,    100, 10, KABIR, (0.85, 0.6)),
    TaskSeed(4, "End-to-end test suite",                    20, 33, 44, 2, "testing:3!"),
    TaskSeed(4, "Load test at lunch peak",                   8, 14, 24, 3, "testing:3!,devops:2"),
    TaskSeed(4, "Security review",                          10, 16, 24, 2, "security:4!"),
    TaskSeed(4, "CI/CD and staging",                        10, 16, 26, 2, "docker:3!,devops:3",     DONE,    100, 15, ARJUN, (0.9, 0.7)),
    TaskSeed(4, "Production rollout",                        6, 10, 16, 1, "devops:3!,docker:3"),
)
# fmt: on

# Finish-to-start edges as 1-based task ids (T-001 is 1).
DEPENDENCIES: tuple[tuple[int, int], ...] = (
    (1, 2),
    (1, 3),
    (2, 4),
    (5, 6),
    (6, 7),
    (6, 8),
    (6, 9),
    (2, 10),
    (5, 10),
    (10, 11),
    (11, 12),
    (12, 13),
    (11, 14),
    (13, 15),
    (14, 15),
    (14, 16),
    (10, 17),
    (17, 18),
    (17, 19),
    (6, 20),
    (15, 21),
    (18, 21),
    (16, 21),
    (21, 22),
    (21, 23),
    (24, 25),
    (22, 25),
    (23, 25),
)


def parse_skills(spec: str) -> list[dict[str, str | int | bool]]:
    rows: list[dict[str, str | int | bool]] = []
    for part in spec.split(","):
        skill, level = part.removesuffix("!").split(":")
        rows.append({"skill": skill, "level": int(level), "must": part.endswith("!")})
    return rows


def expected_hours(task: TaskSeed) -> float:
    return (task.o + 4 * task.m + task.p) / 6


def _cents(value: Decimal | float) -> Decimal:
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def _task_budget(task: TaskSeed) -> Decimal:
    return _cents(expected_hours(task)) * HOURLY_RATE


def _step_working_days(day: date, count: int) -> date:
    """`count` working days after `day`, or before it when negative."""
    step = 1 if count >= 0 else -1
    for _ in range(abs(count)):
        day += timedelta(days=step)
        while day.weekday() >= 5:
            day += timedelta(days=step)
    return day


def _latest_working_day(day: date) -> date:
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def planned_windows() -> tuple[list[float], list[float]]:
    """Each task's planned start and finish, in hours, rounded to whole days like the scheduler."""
    starts = [0.0] * len(TASKS)
    finishes = [0.0] * len(TASKS)
    preds: dict[int, list[int]] = {}
    for pred, succ in DEPENDENCIES:
        preds.setdefault(succ - 1, []).append(pred - 1)
    remaining = set(range(len(TASKS)))
    while remaining:
        ready = sorted(i for i in remaining if not set(preds.get(i, [])) & remaining)
        for index in ready:
            starts[index] = max((finishes[p] for p in preds.get(index, [])), default=0.0)
            days = math.ceil(expected_hours(TASKS[index]) / HOURS_PER_DAY)
            finishes[index] = starts[index] + days * HOURS_PER_DAY
            remaining.discard(index)
    return starts, finishes


def _planned_value(elapsed_days: int) -> Decimal:
    """Linear spread of each task's budget over its planned hours, at a day's end."""
    now = elapsed_days * HOURS_PER_DAY
    starts, finishes = planned_windows()
    total = Decimal(0)
    for task, start, finish in zip(TASKS, starts, finishes, strict=True):
        share = min(max((now - start) / (finish - start), 0.0), 1.0)
        total += _task_budget(task) * Decimal(str(share))
    return _cents(total)


def _progress_curve(rng: Random) -> list[float]:
    """Monotonic share of final progress on each snapshot day, ending at exactly 1."""
    opening = 1 / 3  # work earned before the first snapshot
    steps = [rng.uniform(0.7, 1.3) for _ in range(SNAPSHOT_DAYS - 1)]
    total = sum(steps)
    curve = [opening]
    for step in steps:
        curve.append(curve[-1] + (1 - opening) * step / total)
    curve[-1] = 1.0
    return curve


def _snapshots(project_id: int, today: date, rng: Random) -> list[Snapshot]:
    final_ev = sum(
        (_task_budget(t) * Decimal(str(t.percent)) / 100 for t in TASKS),
        Decimal(0),
    )
    final_ac = sum((Decimal(str(t.actual)) * HOURLY_RATE for t in TASKS), Decimal(0))
    ev_curve = _progress_curve(rng)
    ac_curve = _progress_curve(rng)
    # The forward pass gives the curve's shape; today's value is scaled to the target SPI.
    pv_scale = (final_ev / TARGET_SPI) / _planned_value(DAYS_ELAPSED)
    rows = []
    for index in range(SNAPSHOT_DAYS):
        days_before_today = SNAPSHOT_DAYS - 1 - index
        rows.append(
            Snapshot(
                project_id=project_id,
                date=_step_working_days(today, -days_before_today),
                pv=_cents(_planned_value(DAYS_ELAPSED - days_before_today) * pv_scale),
                ev=_cents(final_ev * Decimal(str(ev_curve[index]))),
                ac=_cents(final_ac * Decimal(str(ac_curve[index]))),
            )
        )
    return rows


def _score_breakdown(task: TaskSeed, member_skills: dict[str, int]) -> dict[str, float]:
    if task.fit is None:
        raise ValueError(f"{task.title} has an owner but no fit values")
    required = parse_skills(task.skills)
    fits = [min(member_skills.get(str(r["skill"]), 0) / int(r["level"]), 1.0) for r in required]
    skill_fit = round(sum(fits) / len(fits), 4)
    capacity_fit, balance = task.fit
    weights = SCORE_WEIGHTS
    score = 100 * (weights[0] * skill_fit + weights[1] * capacity_fit + weights[2] * balance)
    return {
        "score": round(score, 1),
        "skill_fit": skill_fit,
        "capacity_fit": capacity_fit,
        "balance": balance,
    }


def wipe(session: Session) -> None:
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


def seed_demo(session: Session, *, seed: int, as_of: date | None = None) -> Project:
    """Replace everything in the database with the demo project. The caller commits."""
    wipe(session)
    rng = Random(seed)
    today = _latest_working_day(as_of or datetime.now(UTC).date())
    start = _step_working_days(today, -DAYS_ELAPSED)
    deadline = _step_working_days(start, DEADLINE_WORKING_DAYS - 1)

    skills = {name: Skill(name=name) for name in SKILLS}
    session.add_all(skills.values())
    session.flush()

    members: dict[str, Member] = {}
    for name, role, hours, levels in MEMBERS:
        slug = name.split()[0].lower()
        member = Member(name=name, role=role, email=f"{slug}@orchestrai.test")
        session.add(member)
        session.flush()
        members[name] = member
        session.add_all(
            MemberSkill(member_id=member.id, skill_id=skills[skill].id, level=level)
            for skill, level in levels.items()
        )
        session.add(
            Availability(
                member_id=member.id,
                kind=AvailabilityKind.WORK,
                start_date=start,
                end_date=deadline,
                hours_per_week=hours,
            )
        )
    session.flush()

    project = Project(
        name="Campus Food-Ordering App",
        brief=(
            "Students order from campus canteens, pay online and track pickup. "
            "Vendors manage menus and a live order queue."
        ),
        start_date=start,
        deadline=deadline,
        budget=BUDGET,
        hourly_rate=HOURLY_RATE,
    )
    session.add(project)
    session.flush()

    epics = [
        Epic(project_id=project.id, title=title, position=index)
        for index, title in enumerate(EPICS)
    ]
    session.add_all(epics)
    session.flush()

    tasks = []
    for row in TASKS:
        task = Task(
            project_id=project.id,
            epic_id=epics[row.epic].id,
            title=row.title,
            optimistic_hours=row.o,
            most_likely_hours=row.m,
            pessimistic_hours=row.p,
            priority=row.priority,
            status=row.status,
            required_skills=parse_skills(row.skills),
            percent_complete=row.percent,
            actual_hours=row.actual,
        )
        session.add(task)
        session.flush()
        tasks.append(task)

    session.add_all(
        Dependency(pred_task_id=tasks[pred - 1].id, succ_task_id=tasks[succ - 1].id)
        for pred, succ in DEPENDENCIES
    )
    session.flush()

    levels_by_member = {name: levels for name, _, _, levels in MEMBERS}
    for row, task in zip(TASKS, tasks, strict=True):
        if row.owner is None:
            continue
        session.add(
            Assignment(
                task_id=task.id,
                member_id=members[row.owner].id,
                score_breakdown=_score_breakdown(row, levels_by_member[row.owner]),
                source=AssignmentSource.AI,
            )
        )
        session.flush()

    session.add_all(_snapshots(project.id, today, rng))
    session.flush()
    return project


def main() -> None:
    settings = get_settings()
    with get_session_factory()() as session:
        project = seed_demo(session, seed=settings.sim_seed)
        session.commit()
        # Risks exist only after detection runs, so the demo must not start at zero.
        refresh_risks(session, project.id, as_of=datetime.now(UTC).date(), seed=settings.sim_seed)
        session.commit()
        print(
            f"Seeded {project.name}: {len(TASKS)} tasks, {len(MEMBERS)} members, "
            f"{project.start_date} to {project.deadline}"
        )


if __name__ == "__main__":
    main()
