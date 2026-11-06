"""Working calendar shared by the engines: Mon-Fri working days, 8 h per project day.

Member capacity per working day = hours_per_week / 5, or 0 on a leave day.
"""

import math
from datetime import date, timedelta

from app.engines.types import MemberInput

HOURS_PER_DAY = 8.0  # one project "day" of effort, used to turn CPM hours into dates
WORK_DAYS_PER_WEEK = 5


def is_working_day(d: date) -> bool:
    return d.weekday() < WORK_DAYS_PER_WEEK


def next_working_day(d: date) -> date:
    while not is_working_day(d):
        d += timedelta(days=1)
    return d


def add_working_days(start: date, n: int) -> date:
    """The working day `n` working days after `start` (n=0 -> start itself, moved off weekends)."""
    d = next_working_day(start)
    for _ in range(n):
        d = next_working_day(d + timedelta(days=1))
    return d


def working_days(start: date, end: date) -> list[date]:
    """Working days in the inclusive range."""
    return [
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if is_working_day(start + timedelta(days=i))
    ]


def working_days_between(start: date, end: date) -> int:
    """Number of working days in [start, end)."""
    return len(working_days(start, end - timedelta(days=1))) if end > start else 0


def on_leave(member: MemberInput, d: date) -> bool:
    return any(r.start <= d <= r.end for r in member.leave)


def daily_capacity(member: MemberInput, d: date) -> float:
    if not is_working_day(d) or on_leave(member, d):
        return 0.0
    return member.hours_per_week / WORK_DAYS_PER_WEEK


def capacity(member: MemberInput, start: date, end: date) -> float:
    """Member hours available in the inclusive date range."""
    return sum(daily_capacity(member, d) for d in working_days(start, end))


def hours_to_window(project_start: date, es: float, ef: float) -> tuple[date, date]:
    """Map a CPM [ES, EF) in hours to an inclusive working-day window."""
    first = math.floor(es / HOURS_PER_DAY + 1e-9)
    last = max(first, math.ceil(ef / HOURS_PER_DAY - 1e-9) - 1)
    return add_working_days(project_start, first), add_working_days(project_start, last)
