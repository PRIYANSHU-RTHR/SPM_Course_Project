"""Scheduler tests. Project starts Monday 2026-11-09; 40 h/week = 8 h/day."""

from datetime import date

import pytest

from app.engines.scheduler import ScheduleError, schedule
from app.engines.types import LeaveRange, MemberInput, TaskInput

MON, TUE, WED, THU, FRI = (date(2026, 11, d) for d in range(9, 14))
NEXT_MON = date(2026, 11, 16)
M1 = MemberInput(1, {}, 40)
M2 = MemberInput(2, {}, 40)


def _t(id: int, hours: float, *preds: int, priority: int = 3) -> TaskInput:
    return TaskInput(id=id, o=hours, m=hours, p=hours, priority=priority, predecessors=preds)


def _dates(result) -> dict[int, tuple[date, date]]:
    return {t.task_id: (t.start, t.end) for t in result.tasks}


def test_no_conflict_matches_cpm() -> None:
    # A 16 h (Mon-Tue) -> B 8 h (Wed); C 8 h on another member (Mon). Same as CPM early start.
    tasks = [_t(1, 16), _t(2, 8, 1), _t(3, 8)]
    result = schedule(tasks, {1: 1, 2: 1, 3: 2}, [M1, M2], MON)
    assert _dates(result) == {1: (MON, TUE), 2: (WED, WED), 3: (MON, MON)}
    assert all(t.start == t.early_start for t in result.tasks)
    assert (result.finish, result.delayed) == (WED, ())


def test_resource_conflict_delays_one_task() -> None:
    # Both 8 h tasks on M1, no dependency: A takes Monday, B slips to Tuesday.
    result = schedule([_t(1, 8), _t(2, 8)], {1: 1, 2: 1}, [M1], MON)
    assert _dates(result) == {1: (MON, MON), 2: (TUE, TUE)}
    assert result.delayed == (2,)
    assert result.tasks[1].resource_delay_days == 1


def test_priority_decides_who_goes_first() -> None:
    result = schedule([_t(1, 8), _t(2, 8, priority=1)], {1: 1, 2: 1}, [M1], MON)
    assert _dates(result) == {2: (MON, MON), 1: (TUE, TUE)}


def test_leave_pushes_work() -> None:
    m = MemberInput(1, {}, 40, (LeaveRange(TUE, TUE),))
    result = schedule([_t(1, 16)], {1: 1}, [m], MON)
    assert _dates(result) == {1: (MON, WED)}


def test_work_is_split_by_daily_capacity_and_days_are_shared() -> None:
    # 20 h/week = 4 h/day. A 10 h: Mon 4, Tue 4, Wed 2. B 2 h fits in Wed's remaining 2 h.
    half = MemberInput(1, {}, 20)
    result = schedule([_t(1, 10), _t(2, 2)], {1: 1, 2: 1}, [half], MON)
    assert _dates(result) == {1: (MON, WED), 2: (WED, WED)}


def test_weekly_load_and_utilisation() -> None:
    # 48 h from Monday: week 1 = 40 h of 40 (100%), week 2 = 8 h of 40 (20%).
    result = schedule([_t(1, 48)], {1: 1}, [M1], MON)
    loads = [(w.week_start, w.hours, w.capacity, w.utilisation) for w in result.loads]
    assert loads == [(MON, 40, 40, 1.0), (NEXT_MON, 8, 40, pytest.approx(0.2))]
    assert result.finish == NEXT_MON


def test_weekend_start_and_unassigned_task_use_project_calendar() -> None:
    result = schedule([_t(1, 12)], {}, [M1], date(2026, 11, 8))  # Sunday -> Monday
    assert _dates(result) == {1: (MON, TUE)}
    assert result.tasks[0].member_id is None


def test_zero_capacity_raises_clear_error() -> None:
    idle = MemberInput(9, {}, 0)
    with pytest.raises(ScheduleError, match="member 9 has no working capacity"):
        schedule([_t(1, 8)], {1: 9}, [idle], MON)


def test_unknown_member_raises() -> None:
    with pytest.raises(ScheduleError, match="unknown member 5"):
        schedule([_t(1, 8)], {1: 5}, [M1], MON)


def test_zero_hour_milestone() -> None:
    result = schedule([_t(1, 8), _t(2, 0, 1)], {1: 1, 2: 1}, [M1], MON)
    assert _dates(result) == {1: (MON, MON), 2: (TUE, TUE)}


def test_empty_project() -> None:
    result = schedule([], {}, [M1], MON)
    assert (result.tasks, result.finish, result.delayed) == ((), MON, ())
    assert [w.week_start for w in result.loads] == [MON]


def test_long_task_crosses_into_next_week() -> None:
    result = schedule([_t(1, 8), _t(2, 40, 1)], {1: 1, 2: 1}, [M1], MON)
    assert _dates(result)[2] == (TUE, NEXT_MON)
    assert result.finish == NEXT_MON


# --- remaining work from as_of ------------------------------------------------------------


def test_as_of_without_progress_moves_unstarted_work_to_as_of() -> None:
    result = schedule([_t(1, 8), _t(2, 8, 1)], {1: 1, 2: 1}, [M1], MON, as_of=WED)
    assert _dates(result) == {1: (WED, WED), 2: (THU, THU)}
    assert result.finish == THU


def test_as_of_before_start_is_the_baseline() -> None:
    tasks = [_t(1, 16), _t(2, 8, 1)]
    baseline = schedule(tasks, {1: 1, 2: 1}, [M1], MON)
    early = schedule(tasks, {1: 1, 2: 1}, [M1], MON, as_of=date(2026, 11, 2))
    assert _dates(early) == _dates(baseline)


def test_finished_task_keeps_its_window_and_successor_starts_as_of() -> None:
    # A planned Mon-Tue, done. B planned Wed; replanned on Thursday it runs Thursday.
    tasks = [_t(1, 16), _t(2, 8, 1)]
    result = schedule(tasks, {1: 1, 2: 1}, [M1], MON, progress={1: 100}, as_of=THU)
    assert _dates(result) == {1: (MON, TUE), 2: (THU, THU)}
    assert result.tasks[0].hours == 16  # full size is still reported


def test_task_finished_early_is_cut_off_before_as_of() -> None:
    # A planned Mon-Wed (24 h) but done by Tuesday: its bar ends Monday, B starts Tuesday.
    result = schedule(
        [_t(1, 24), _t(2, 8, 1)], {1: 1, 2: 1}, [M1], MON, progress={1: 100}, as_of=TUE
    )
    assert _dates(result) == {1: (MON, MON), 2: (TUE, TUE)}


def test_started_task_plans_only_remaining_hours_and_keeps_its_start() -> None:
    # 32 h task, 75% done on Wednesday: 8 h left -> ends Wednesday, started Monday.
    result = schedule([_t(1, 32)], {1: 1}, [M1], MON, progress={1: 75}, as_of=WED)
    assert _dates(result) == {1: (MON, WED)}
    assert [w.hours for w in result.loads if w.member_id == 1] == [8]


def test_late_task_slips_past_the_baseline() -> None:
    # 16 h task planned Mon-Tue, only 25% done on Wednesday: 12 h left -> Wed + half of Thu.
    result = schedule([_t(1, 16)], {1: 1}, [M1], MON, progress={1: 25}, as_of=WED)
    assert _dates(result) == {1: (MON, THU)}
