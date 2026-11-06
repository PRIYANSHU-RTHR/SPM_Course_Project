"""Dependency ordering and Critical Path Method (activity-on-node, finish-to-start). Pure.

Times are hours from project start. Forward pass gives ES/EF, backward pass LS/LF;
total slack = LS - ES, free slack = min(ES of successors) - EF (project end if none).
"""

import heapq
from collections.abc import Mapping, Sequence

from app.engines.estimation import pert
from app.engines.types import CPMResult, CPMTask, TaskInput

_EPS = 1e-9


class CycleError(ValueError):
    """The dependency graph has a cycle. `cycle` is the ids in order, first id repeated last."""

    def __init__(self, cycle: list[int]) -> None:
        super().__init__("dependency cycle: " + " -> ".join(map(str, cycle)))
        self.cycle = cycle


def _successors(tasks: Sequence[TaskInput]) -> dict[int, list[int]]:
    ids = {t.id for t in tasks}
    if len(ids) != len(tasks):
        raise ValueError("duplicate task ids")
    succ: dict[int, list[int]] = {t.id: [] for t in tasks}
    for t in tasks:
        for p in t.predecessors:
            if p not in ids:
                raise ValueError(f"task {t.id}: unknown predecessor {p}")
            if t.id not in succ[p]:
                succ[p].append(t.id)
    return succ


def _find_cycle(remaining: set[int], by_id: Mapping[int, TaskInput]) -> list[int]:
    """Every node left after Kahn has a predecessor that is also left, so walking
    predecessors must repeat a node; that loop, reversed, is a cycle in dependency order."""
    node = min(remaining)
    seen: dict[int, int] = {}
    path: list[int] = []
    while node not in seen:
        seen[node] = len(path)
        path.append(node)
        node = min(p for p in by_id[node].predecessors if p in remaining)
    loop = path[seen[node] :]
    loop.reverse()
    k = loop.index(min(loop))  # start at the smallest id so the message is stable
    loop = loop[k:] + loop[:k]
    return [*loop, loop[0]]


def topo_sort(tasks: Sequence[TaskInput]) -> list[int]:
    """Kahn's algorithm; ties broken by smallest id so the order is deterministic."""
    succ = _successors(tasks)
    indegree = {t.id: len(set(t.predecessors)) for t in tasks}
    ready = [i for i, d in indegree.items() if d == 0]
    heapq.heapify(ready)
    order: list[int] = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for s in succ[node]:
            indegree[s] -= 1
            if indegree[s] == 0:
                heapq.heappush(ready, s)
    if len(order) != len(tasks):
        raise CycleError(_find_cycle(set(indegree) - set(order), {t.id: t for t in tasks}))
    return order


def cpm(tasks: Sequence[TaskInput], durations: Mapping[int, float] | None = None) -> CPMResult:
    """Run CPM. `durations` (hours) defaults to each task's PERT te."""
    order = topo_sort(tasks)
    by_id = {t.id: t for t in tasks}
    succ = _successors(tasks)
    dur = {t.id: (durations[t.id] if durations else pert(t).te) for t in tasks}

    es: dict[int, float] = {}
    ef: dict[int, float] = {}
    for i in order:
        es[i] = max((ef[p] for p in by_id[i].predecessors), default=0.0)
        ef[i] = es[i] + dur[i]
    finish = max(ef.values(), default=0.0)

    ls: dict[int, float] = {}
    lf: dict[int, float] = {}
    for i in reversed(order):
        lf[i] = min((ls[s] for s in succ[i]), default=finish)
        ls[i] = lf[i] - dur[i]

    rows = []
    for i in order:
        total = ls[i] - es[i]
        free = min((es[s] for s in succ[i]), default=finish) - ef[i]
        rows.append(
            CPMTask(
                task_id=i,
                duration=dur[i],
                es=es[i],
                ef=ef[i],
                ls=ls[i],
                lf=lf[i],
                total_slack=0.0 if abs(total) < _EPS else total,
                free_slack=0.0 if abs(free) < _EPS else free,
                critical=abs(total) < _EPS,
            )
        )

    critical = {r.task_id for r in rows if r.critical}

    # Critical paths: chains of critical tasks joined by "tight" edges (EF of pred == ES of succ),
    # from a task starting at 0 to one ending at the project finish.
    # shortcut: enumerates every path (exponential in the worst case); fine for ~100 tasks.
    def extend(path: list[int]) -> list[tuple[int, ...]]:
        last = path[-1]
        nxt = [s for s in sorted(succ[last]) if s in critical and abs(es[s] - ef[last]) < _EPS]
        if not nxt:
            return [tuple(path)] if abs(ef[last] - finish) < _EPS else []
        return [p for s in nxt for p in extend([*path, s])]

    starts = [i for i in order if i in critical and es[i] < _EPS]
    paths = tuple(p for s in sorted(starts) for p in extend([s]))

    return CPMResult(tasks=tuple(rows), project_duration=finish, critical_paths=paths)
