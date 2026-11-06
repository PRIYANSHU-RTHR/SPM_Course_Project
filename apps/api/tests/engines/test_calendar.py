"""Working-calendar helpers (Mon-Fri, 8 h project day)."""

from datetime import date

from app.engines import calendar
from app.engines.types import LeaveRange, MemberInput

FRI, SAT, MON = date(2026, 11, 13), date(2026, 11, 14), date(2026, 11, 16)


def test_weekends_are_skipped() -> None:
    assert calendar.next_working_day(SAT) == MON
    assert calendar.add_working_days(FRI, 1) == MON
    assert calendar.add_working_days(SAT, 0) == MON
    assert len(calendar.working_days(date(2026, 11, 9), date(2026, 11, 22))) == 10
    assert calendar.working_days_between(FRI, MON) == 1


def test_capacity_respects_leave() -> None:
    member = MemberInput(1, {}, 40, (LeaveRange(MON, MON),))
    assert calendar.daily_capacity(member, MON) == 0
    assert calendar.daily_capacity(member, FRI) == 8
    assert calendar.capacity(member, FRI, date(2026, 11, 17)) == 16  # Fri + Tue


def test_hours_to_window() -> None:
    start = date(2026, 11, 9)  # Monday
    assert calendar.hours_to_window(start, 0, 8) == (start, start)
    assert calendar.hours_to_window(start, 0, 12) == (start, date(2026, 11, 10))
    assert calendar.hours_to_window(start, 36, 44) == (date(2026, 11, 13), date(2026, 11, 16))
    assert calendar.hours_to_window(start, 5, 5) == (start, start)  # zero-length task
