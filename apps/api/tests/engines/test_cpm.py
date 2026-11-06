"""CPM engine tests.

Networks and expected values are hand-worked (forward/backward pass shown in comments),
activity-on-node with finish-to-start links as taught in Hughes & Cotterell,
Software Project Management, ch. 6.
"""

import pytest

from app.engines.cpm import CycleError, cpm, topo_sort
from app.engines.types import TaskInput


def _t(id: int, hours: float, *preds: int) -> TaskInput:
    return TaskInput(id=id, o=hours, m=hours, p=hours, predecessors=preds)


# A(3)  B(4)  C(2)<-A  D(5)<-A  E(3)<-B,C  F(2)<-D,E,G  G(1)<-B
#   forward:  A 0-3, B 0-4, C 3-5, D 3-8, E 5-8, G 4-5, F 8-10   -> duration 10
#   backward: F 8-10, D 3-8, E 5-8, G 7-8, C 3-5, B 1-5, A 0-3
#   B: total slack 1, free slack min(ES E=5, ES G=4) - EF 4 = 0
#   G: total slack 3, free slack ES F 8 - EF 5 = 3
#   critical paths: A-C-E-F and A-D-F
A, B, C, D, E, F, G = 1, 2, 3, 4, 5, 6, 7
NETWORK = [
    _t(A, 3),
    _t(B, 4),
    _t(C, 2, A),
    _t(D, 5, A),
    _t(E, 3, B, C),
    _t(F, 2, D, E, G),
    _t(G, 1, B),
]
EXPECTED = {  # id: (es, ef, ls, lf, total slack, free slack)
    A: (0, 3, 0, 3, 0, 0),
    B: (0, 4, 1, 5, 1, 0),
    C: (3, 5, 3, 5, 0, 0),
    D: (3, 8, 3, 8, 0, 0),
    E: (5, 8, 5, 8, 0, 0),
    F: (8, 10, 8, 10, 0, 0),
    G: (4, 5, 7, 8, 3, 3),
}


def test_textbook_network_passes_and_slack() -> None:
    result = cpm(NETWORK)

    assert result.project_duration == 10
    for row in result.tasks:
        got = (row.es, row.ef, row.ls, row.lf, row.total_slack, row.free_slack)
        assert got == pytest.approx(EXPECTED[row.task_id]), row.task_id
        assert row.critical == (EXPECTED[row.task_id][4] == 0)


def test_two_critical_paths_are_both_returned() -> None:
    assert cpm(NETWORK).critical_paths == ((A, C, E, F), (A, D, F))


def test_topo_order_respects_dependencies_and_is_deterministic() -> None:
    order = topo_sort(NETWORK)
    pos = {i: k for k, i in enumerate(order)}
    assert all(pos[p] < pos[t.id] for t in NETWORK for p in t.predecessors)
    assert order == topo_sort(list(reversed(NETWORK)))


def test_single_task() -> None:
    result = cpm([_t(1, 5)])
    assert result.project_duration == 5
    assert result.critical_paths == ((1,),)
    assert result.tasks[0].total_slack == 0


def test_disconnected_graph() -> None:
    # 1(3) -> 2(2) takes 5 h; 3(4) alone has 1 h of total and free slack.
    result = cpm([_t(1, 3), _t(2, 2, 1), _t(3, 4)])
    slack = {r.task_id: (r.total_slack, r.free_slack) for r in result.tasks}
    assert result.project_duration == 5
    assert result.critical_paths == ((1, 2),)
    assert slack[3] == (1, 1)


def test_durations_default_to_pert_te_and_can_be_overridden() -> None:
    tasks = [TaskInput(id=1, o=2, m=4, p=12)]  # te = 5
    assert cpm(tasks).project_duration == pytest.approx(5)
    assert cpm(tasks, durations={1: 7}).project_duration == 7


def test_empty_network() -> None:
    result = cpm([])
    assert (result.project_duration, result.tasks, result.critical_paths) == (0, (), ())


def test_cycle_raises_with_cycle_path() -> None:
    # 1 -> 2 -> 3 -> 1, and 4 hangs off the cycle (must not be reported as part of it).
    tasks = [_t(1, 1, 3), _t(2, 1, 1), _t(3, 1, 2), _t(4, 1, 3)]
    with pytest.raises(CycleError) as info:
        topo_sort(tasks)
    assert info.value.cycle == [1, 2, 3, 1]


def test_self_loop_is_a_cycle() -> None:
    with pytest.raises(CycleError) as info:
        cpm([_t(1, 1, 1)])
    assert info.value.cycle == [1, 1]


def test_unknown_predecessor_and_duplicate_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="unknown predecessor"):
        cpm([_t(1, 1, 99)])
    with pytest.raises(ValueError, match="duplicate"):
        cpm([_t(1, 1), _t(1, 2)])


def test_duplicate_predecessor_does_not_duplicate_paths() -> None:
    assert cpm([_t(1, 1), _t(2, 1, 1, 1)]).critical_paths == ((1, 2),)
