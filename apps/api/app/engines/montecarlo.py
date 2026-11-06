"""Monte Carlo completion forecast over the dependency network. Pure, NumPy, seeded.

Each task's duration is drawn from Beta-PERT(o, m, p):
    alpha = 1 + 4 (m - o) / (p - o),  beta = 1 + 4 (p - m) / (p - o),
    d = o + (p - o) * Beta(alpha, beta)          (mean = (o + 4m + p) / 6, as in PERT)
Then a forward pass per run (loop over tasks in topological order, vectorised over runs)
gives the project finish; a backward pass marks the tasks with zero slack in that run,
which gives each task's criticality index (share of runs where it is on a longest path).
Times are hours of effort-days from project start, the same scale as CPM.
"""

import numpy as np

from app.engines.cpm import topo_sort
from app.engines.types import ForecastResult, TaskInput

DEFAULT_RUNS = 5000
HIST_BINS = 30
CDF_POINTS = 50
_EPS = 1e-9


def sample_durations(tasks: list[TaskInput], runs: int, rng: np.random.Generator) -> np.ndarray:
    """Beta-PERT samples, shape (runs, len(tasks)); o == p gives the constant o."""
    o = np.array([t.o for t in tasks], dtype=float)
    m = np.array([t.m for t in tasks], dtype=float)
    p = np.array([t.p for t in tasks], dtype=float)
    span = p - o
    safe = np.where(span > 0, span, 1.0)
    alpha = 1 + 4 * (m - o) / safe
    beta = 1 + 4 * (p - m) / safe
    draws = rng.beta(alpha, beta, size=(runs, len(tasks)))
    return o + np.where(span > 0, span, 0.0) * draws


def forecast(
    tasks: list[TaskInput],
    deadline_hours: float | None = None,
    runs: int = DEFAULT_RUNS,
    seed: int = 42,
) -> ForecastResult:
    if runs < 1:
        raise ValueError("runs must be >= 1")
    order = topo_sort(tasks)  # raises CycleError
    col = {t.id: k for k, t in enumerate(tasks)}
    by_id = {t.id: t for t in tasks}
    succ: dict[int, list[int]] = {t.id: [] for t in tasks}
    for t in tasks:
        for pred in set(t.predecessors):
            succ[pred].append(t.id)

    rng = np.random.default_rng(seed)
    dur = sample_durations(tasks, runs, rng)

    ef = np.zeros_like(dur)
    for i in order:
        k = col[i]
        start = np.zeros(runs)
        for pred in by_id[i].predecessors:
            np.maximum(start, ef[:, col[pred]], out=start)
        ef[:, k] = start + dur[:, k]
    finish = ef.max(axis=1) if tasks else np.zeros(runs)

    ls = np.zeros_like(dur)
    for i in reversed(order):
        k = col[i]
        lf = finish.copy()
        for s in succ[i]:
            np.minimum(lf, ls[:, col[s]], out=lf)
        ls[:, k] = lf - dur[:, k]
    critical = np.abs(ls - (ef - dur)) < _EPS  # total slack == 0, per run and task

    counts, edges = np.histogram(finish, bins=HIST_BINS)
    xs = np.linspace(finish.min(), finish.max(), CDF_POINTS)
    ordered = np.sort(finish)
    cdf = np.searchsorted(ordered, xs, side="right") / runs
    p50, p80, p95 = np.percentile(finish, [50, 80, 95])

    return ForecastResult(
        runs=runs,
        seed=seed,
        deadline_hours=deadline_hours,
        p_on_time=None if deadline_hours is None else float(np.mean(finish <= deadline_hours)),
        mean=float(finish.mean()),
        p50=float(p50),
        p80=float(p80),
        p95=float(p95),
        histogram=tuple((float(e), int(c)) for e, c in zip(edges[:-1], counts, strict=True)),
        cdf=tuple((float(x), float(y)) for x, y in zip(xs, cdf, strict=True)),
        criticality={t.id: float(critical[:, col[t.id]].mean()) for t in tasks},
    )
