"""Estimation engine tests. Expected numbers worked by hand (see comments)."""

import math

import pytest

from app.engines.estimation import (
    NOMINAL_SCALE_FACTORS,
    CocomoParams,
    cocomo2,
    ksloc_from_hours,
    path_pert,
    pert,
)
from app.engines.types import TaskInput


def _t(id: int, o: float, m: float, p: float) -> TaskInput:
    return TaskInput(id=id, o=o, m=m, p=p)


def test_pert_textbook_values() -> None:
    # o=2, m=4, p=12: te = (2 + 16 + 12) / 6 = 5; sigma = 10 / 6
    e = pert(_t(1, 2, 4, 12))
    assert e.te == pytest.approx(5.0)
    assert e.std == pytest.approx(10 / 6)
    assert e.variance == pytest.approx(100 / 36)


def test_pert_point_estimate_has_zero_variance() -> None:
    e = pert(_t(1, 8, 8, 8))
    assert (e.te, e.variance) == (8.0, 0.0)


def test_task_rejects_bad_three_point_order() -> None:
    with pytest.raises(ValueError):
        _t(1, 5, 4, 6)
    with pytest.raises(ValueError):
        _t(1, -1, 2, 3)


def test_path_sums_te_and_variance() -> None:
    # A: te 5, var 100/36; B (4,6,8): te 6, var 4/9 -> te 11, sigma sqrt(116/36)
    path = path_pert([_t(1, 2, 4, 12), _t(2, 4, 6, 8)])
    assert path.task_ids == (1, 2)
    assert path.te == pytest.approx(11.0)
    assert path.std == pytest.approx(math.sqrt(116 / 36))
    assert path.probability is None


def test_path_probability_normal_approx() -> None:
    # o=0, m=6, p=12: te 6, sigma 2. T=8 -> z=1 -> 0.8413 (standard normal table).
    task = [_t(1, 0, 6, 12)]
    assert path_pert(task, target=8).probability == pytest.approx(0.8413, abs=1e-4)
    assert path_pert(task, target=6).probability == pytest.approx(0.5)
    assert path_pert(task, target=4).probability == pytest.approx(0.1587, abs=1e-4)


def test_path_probability_without_uncertainty_is_step() -> None:
    task = [_t(1, 5, 5, 5)]
    assert path_pert(task, target=5).probability == 1.0
    assert path_pert(task, target=4.9).probability == 0.0


def test_empty_path() -> None:
    path = path_pert([])
    assert (path.te, path.std, path.task_ids) == (0.0, 0.0, ())


def test_cocomo_reduces_to_constants_with_no_scale_factors() -> None:
    # SF sum 0 -> E = B = 0.91; 1 KSLOC -> PM = A = 2.94
    # F = D = 0.28; TDEV = 3.67 * 2.94^0.28 = 3.67 * 1.35248 = 4.9636
    r = cocomo2(1.0, CocomoParams(scale_factors={}))
    assert r.exponent == pytest.approx(0.91)
    assert r.effort_pm == pytest.approx(2.94)
    assert r.tdev_months == pytest.approx(4.9636, abs=1e-3)
    assert r.avg_staff == pytest.approx(2.94 / 4.9636, abs=1e-3)


def test_cocomo_nominal_100_ksloc() -> None:
    # COCOMO II.2000 nominal (Boehm et al. 2000): SF sum = 18.97 -> E = 1.0997.
    # PM = 2.94 * 100^1.0997 = 2.94 * 158.27 = 465.3
    # F = 0.28 + 0.2 * 0.1897 = 0.31794; TDEV = 3.67 * 465.3^0.31794 = 25.87 months
    assert sum(NOMINAL_SCALE_FACTORS.values()) == pytest.approx(18.97)
    r = cocomo2(100.0)
    assert r.exponent == pytest.approx(1.0997)
    assert r.effort_pm == pytest.approx(465.3, rel=1e-3)
    assert r.tdev_months == pytest.approx(25.87, rel=1e-3)
    assert r.avg_staff == pytest.approx(465.3 / 25.87, rel=2e-3)


def test_cocomo_effort_multipliers_scale_effort() -> None:
    base = cocomo2(10.0)
    harder = cocomo2(10.0, CocomoParams(effort_multipliers={"RELY": 1.10, "CPLX": 1.17}))
    assert harder.effort_pm == pytest.approx(base.effort_pm * 1.287)


def test_cocomo_rejects_non_positive_size() -> None:
    with pytest.raises(ValueError):
        cocomo2(0)


def test_ksloc_from_hours() -> None:
    # 1,520 h at 10 LOC/h = 15,200 LOC
    assert ksloc_from_hours(1520) == pytest.approx(15.2)
    assert ksloc_from_hours(100, loc_per_hour=20) == pytest.approx(2.0)
    with pytest.raises(ValueError):
        ksloc_from_hours(10, loc_per_hour=0)
