"""Monte Carlo engine tests."""

import time

import numpy as np
import pytest

from app.engines.cpm import CycleError, cpm
from app.engines.montecarlo import forecast, sample_durations
from app.engines.types import TaskInput


def _t(id: int, o: float, m: float, p: float, *preds: int) -> TaskInput:
    return TaskInput(id=id, o=o, m=m, p=p, predecessors=preds)


# Same 7-task network as the CPM tests (o = m = p), durations in hours.
NETWORK = [
    _t(1, 3, 3, 3),
    _t(2, 4, 4, 4),
    _t(3, 2, 2, 2, 1),
    _t(4, 5, 5, 5, 1),
    _t(5, 3, 3, 3, 2, 3),
    _t(6, 2, 2, 2, 4, 5, 7),
    _t(7, 1, 1, 1, 2),
]


def test_degenerate_estimates_equal_cpm_exactly() -> None:
    result = forecast(NETWORK, deadline_hours=10, runs=200)
    assert result.p50 == result.p95 == result.mean == cpm(NETWORK).project_duration == 10
    assert result.p_on_time == 1.0
    # Critical tasks are critical in every run; B (slack 1) and G (slack 3) never are.
    assert result.criticality == {1: 1.0, 2: 0.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 0.0}


def test_same_seed_same_result_different_seed_differs() -> None:
    tasks = [_t(1, 2, 4, 12), _t(2, 4, 6, 20, 1)]
    a = forecast(tasks, deadline_hours=12, seed=7)
    b = forecast(tasks, deadline_hours=12, seed=7)
    c = forecast(tasks, deadline_hours=12, seed=8)
    assert a == b
    assert a.p50 != c.p50


def test_single_path_has_criticality_one() -> None:
    chain = [_t(1, 1, 2, 6), _t(2, 2, 3, 9, 1), _t(3, 1, 5, 8, 2)]
    assert forecast(chain).criticality == {1: 1.0, 2: 1.0, 3: 1.0}


def test_beta_pert_mean_matches_pert_te() -> None:
    # o=2, m=4, p=12 -> te = 5. 200k samples: standard error ~0.003.
    draws = sample_durations([_t(1, 2, 4, 12)], 200_000, np.random.default_rng(0))
    assert draws.mean() == pytest.approx(5.0, abs=0.02)
    assert draws.min() >= 2 and draws.max() <= 12


def test_percentiles_histogram_and_cdf_shapes() -> None:
    result = forecast([_t(1, 2, 4, 12), _t(2, 4, 6, 20, 1)], deadline_hours=11)
    assert result.p50 <= result.p80 <= result.p95
    assert len(result.histogram) == 30
    assert sum(count for _, count in result.histogram) == result.runs == 5000
    assert len(result.cdf) == 50
    assert result.cdf[-1][1] == 1.0
    assert all(a[1] <= b[1] for a, b in zip(result.cdf, result.cdf[1:], strict=False))
    # te along the chain is 5 + 8 = 13, so finishing by 11 h is unlikely but possible.
    assert result.p_on_time is not None and 0 < result.p_on_time < 0.5


def test_parallel_branches_share_criticality() -> None:
    # Two identical independent branches: each is critical in about half the runs.
    result = forecast([_t(1, 1, 5, 9), _t(2, 1, 5, 9)], runs=4000, seed=1)
    assert result.criticality[1] == pytest.approx(0.5, abs=0.05)
    assert result.criticality[1] + result.criticality[2] == pytest.approx(1.0)


def test_no_deadline_and_empty_network() -> None:
    assert forecast([_t(1, 1, 1, 1)]).p_on_time is None
    empty = forecast([], deadline_hours=0, runs=10)
    assert (empty.p50, empty.p_on_time, empty.criticality) == (0, 1.0, {})


def test_cycle_and_bad_runs_raise() -> None:
    with pytest.raises(CycleError):
        forecast([_t(1, 1, 1, 1, 2), _t(2, 1, 1, 1, 1)])
    with pytest.raises(ValueError):
        forecast([_t(1, 1, 1, 1)], runs=0)


def test_fifty_tasks_five_thousand_runs_is_fast() -> None:
    rng = np.random.default_rng(3)
    tasks = []
    for i in range(1, 51):
        preds = tuple(
            int(p) for p in rng.choice(np.arange(1, i), size=min(i - 1, 2), replace=False)
        )
        o = float(rng.integers(2, 10))
        tasks.append(_t(i, o, o + 4, o + 12, *preds))
    started = time.perf_counter()
    forecast(tasks, deadline_hours=200, runs=5000)
    assert time.perf_counter() - started < 3.0  # target < 1 s; loose for slow CI
