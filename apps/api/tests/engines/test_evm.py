"""EVM engine tests.

Worked example uses the standard PMBOK Guide formulas with numbers checked by hand:
BAC 10,000, PV 5,000, EV 4,000, AC 4,500
-> SV -1,000, CV -500, SPI 0.8, CPI 0.8889, EAC 11,250, ETC 6,750, VAC -1,250, TCPI 1.0909.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.engines.evm import earned_value, evm, hours_cost, planned_value
from app.engines.types import BaselineTask

D = Decimal
MON, TUE, WED, THU, FRI = (date(2026, 11, d) for d in range(9, 14))


def test_textbook_example() -> None:
    r = evm(bac=D("10000"), pv=D("5000"), ev=D("4000"), ac=D("4500"))
    assert (r.sv, r.cv) == (D("-1000.00"), D("-500.00"))
    assert r.spi == pytest.approx(0.8)
    assert r.cpi == pytest.approx(0.8889, abs=1e-4)
    assert (r.eac, r.etc, r.vac) == (D("11250.00"), D("6750.00"), D("-1250.00"))
    assert r.tcpi == pytest.approx(1.0909, abs=1e-4)
    assert r.notes == {}


def test_no_progress_yet() -> None:
    r = evm(bac=D("10000"), pv=D("0"), ev=D("0"), ac=D("0"))
    assert (r.spi, r.cpi, r.eac, r.etc, r.vac) == (None, None, None, None, None)
    assert r.tcpi == pytest.approx(1.0)
    assert r.notes["spi"] == "no planned value yet (PV = 0)"
    assert r.notes["eac"] == "CPI undefined"


def test_cost_spent_but_nothing_earned() -> None:
    r = evm(bac=D("10000"), pv=D("2000"), ev=D("0"), ac=D("1000"))
    assert r.cpi == 0
    assert r.eac is None
    assert "EV = 0" in r.notes["eac"]


def test_finished_project() -> None:
    # Done on budget: everything earned and spent; TCPI is undefined (nothing left to spend).
    r = evm(bac=D("10000"), pv=D("10000"), ev=D("10000"), ac=D("10000"))
    assert (r.spi, r.cpi) == (1.0, 1.0)
    assert (r.eac, r.vac) == (D("10000.00"), D("0.00"))
    assert r.tcpi is None and "BAC = AC" in r.notes["tcpi"]
    # Done over budget: TCPI = 0 / negative remaining budget = -0.0.
    over = evm(bac=D("10000"), pv=D("10000"), ev=D("10000"), ac=D("12500"))
    assert over.eac == D("12500.00")
    assert over.tcpi == 0


def test_planned_value_spreads_cost_over_working_days() -> None:
    # 5,000 over Mon-Fri = 1,000 a day; 3,000 over Thu-Mon (Thu, Fri, Mon) = 1,000 a day.
    baseline = [
        BaselineTask(1, MON, FRI, D("5000")),
        BaselineTask(2, THU, date(2026, 11, 16), D("3000")),
    ]
    assert planned_value(baseline, date(2026, 11, 8)) == D("0.00")
    assert planned_value(baseline, WED) == D("3000.00")
    assert planned_value(baseline, FRI) == D("7000.00")
    assert planned_value(baseline, date(2026, 11, 15)) == D("7000.00")  # Sunday
    assert planned_value(baseline, date(2026, 11, 30)) == D("8000.00")


def test_planned_value_rounds_to_paise() -> None:
    assert planned_value([BaselineTask(1, MON, WED, D("100"))], MON) == D("33.33")


def test_earned_value_and_hours_cost() -> None:
    assert earned_value([D("1000"), D("3000")], [50, 10]) == D("800.00")
    assert hours_cost(0.1, D("800")) == D("80.00")
    assert hours_cost(7.5, D("1250.50")) == D("9378.75")


def test_planned_value_of_a_zero_length_task_counts_in_full_from_its_start() -> None:
    # A milestone placed on a weekend has no working days: all of its value is planned at
    # its start, none before.
    sat, sun = date(2026, 11, 14), date(2026, 11, 15)
    milestone = [BaselineTask(1, sat, sun, D("500"))]
    assert planned_value(milestone, FRI) == D("0.00")
    assert planned_value(milestone, sat) == D("500.00")
    assert planned_value(milestone, date(2026, 11, 20)) == D("500.00")
