"""Evaluation script: deterministic scenarios and a sane strategy comparison (no DB)."""

import pytest

from scripts import evaluate


@pytest.fixture(autouse=True)
def _few_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(evaluate, "SIM_RUNS", 20)


def test_synthetic_scenarios_are_deterministic_and_fully_staffable() -> None:
    a, b = evaluate.synthetic_scenario(1), evaluate.synthetic_scenario(1)
    assert a == b
    assert evaluate.evaluate(a, "round-robin").unassigned == 0


def test_engine_strategies_beat_random_on_the_demo_seed() -> None:
    sc = evaluate.demo_scenario()
    assert len(sc.tasks) == 25 and len(sc.members) == 8
    rows = {s: evaluate.evaluate(sc, s) for s in ("random", "greedy", "optimal")}
    assert rows["greedy"].mean > rows["random"].mean
    assert rows["optimal"].mean > rows["random"].mean
    assert all(r.unassigned == 0 and 0 <= r.p_on_time <= 1 for r in rows.values())


def test_tables_render() -> None:
    sc = evaluate.demo_scenario()
    table = evaluate.strategy_table([evaluate.evaluate(sc, "greedy")])
    assert table.splitlines()[0].startswith("| Strategy | Total score")
    assert "| greedy |" in table
