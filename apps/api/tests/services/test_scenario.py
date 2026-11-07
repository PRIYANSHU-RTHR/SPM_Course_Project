"""Pure helpers of the what-if layer: calendar hours and the resource-shifted forecast."""

from datetime import date

import pytest

from app.engines.montecarlo import forecast
from app.engines.types import TaskInput
from app.services.scenario import hours_through, hours_to_date, shifted_forecast

MON = date(2026, 11, 9)
TASKS = [
    TaskInput(1, o=8, m=16, p=40),
    TaskInput(2, o=4, m=8, p=12, predecessors=(1,)),
    TaskInput(3, o=8, m=8, p=24, predecessors=(1,)),
]


def test_hours_through_counts_whole_working_days() -> None:
    assert hours_through(MON, MON) == 8  # Monday itself
    assert hours_through(MON, date(2026, 11, 13)) == 40  # Mon-Fri
    assert hours_through(MON, date(2026, 11, 16)) == 48  # weekend skipped


def test_hours_to_date_is_the_day_the_hours_end_on() -> None:
    assert hours_to_date(MON, 8) == MON
    assert hours_to_date(MON, 8.5) == date(2026, 11, 10)
    assert hours_to_date(MON, 40) == date(2026, 11, 13)
    assert hours_to_date(MON, 41) == date(2026, 11, 16)


def test_zero_shift_is_the_plain_forecast() -> None:
    raw = forecast(TASKS, 40, runs=2000, seed=7)
    same = shifted_forecast(TASKS, 40, 0.0, runs=2000, seed=7)

    assert same == raw


def test_shift_moves_every_number_and_tests_the_deadline_earlier() -> None:
    raw = forecast(TASKS, 40 - 16, runs=2000, seed=7)  # same seed: identical samples
    moved = shifted_forecast(TASKS, 40, 16.0, runs=2000, seed=7)

    assert moved.p_on_time == raw.p_on_time  # P(finish + 16 <= 40) == P(finish <= 24)
    assert moved.deadline_hours == 40
    assert (moved.p50, moved.p80, moved.p95, moved.mean) == pytest.approx(
        (raw.p50 + 16, raw.p80 + 16, raw.p95 + 16, raw.mean + 16)
    )
    assert moved.histogram[0] == (raw.histogram[0][0] + 16, raw.histogram[0][1])
    assert moved.cdf[-1] == (pytest.approx(raw.cdf[-1][0] + 16), raw.cdf[-1][1])
    assert moved.criticality == raw.criticality


def test_negative_shift_raises_the_probability() -> None:
    late = shifted_forecast(TASKS, 32, 8.0, runs=2000, seed=7)
    early = shifted_forecast(TASKS, 32, -8.0, runs=2000, seed=7)

    assert late.p_on_time is not None
    assert early.p_on_time is not None
    assert early.p_on_time > late.p_on_time
