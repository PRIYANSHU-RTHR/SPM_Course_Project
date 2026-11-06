"""Assignment engine tests. Scores are hand-computed in the comments."""

from datetime import date

import pytest

from app.engines.assignment import (
    AssignmentWeights,
    Load,
    compare,
    is_eligible,
    recommend_greedy,
    recommend_optimal,
    score,
)
from app.engines.types import LeaveRange, MemberInput, RequiredSkill, TaskInput

# Mon 2026-11-09 .. Fri 2026-11-13: 5 working days; 40 h/week -> 8 h/day -> 40 h in the window.
WEEK = (date(2026, 11, 9), date(2026, 11, 13))

M1 = MemberInput(id=1, skills={"python": 5, "ml": 4}, hours_per_week=40)
M2 = MemberInput(id=2, skills={"python": 3, "ml": 1}, hours_per_week=40)
TEAM = [M1, M2]

T1 = TaskInput(id=1, o=30, m=30, p=30, priority=1, required_skills=(RequiredSkill("python", 3),))
T2 = TaskInput(
    id=2,
    o=30,
    m=30,
    p=30,
    priority=2,
    required_skills=(RequiredSkill("python", 3), RequiredSkill("ml", 4, must=False)),
)


def test_score_hand_computed_empty_load() -> None:
    # M2 on T2: python min(3/3,1)=1, ml min(1/4,1)=0.25, weights 0.5/0.5 -> skill_fit 0.625
    # free 40 h >= 30 h -> capacity_fit 1; nobody loaded -> balance 1
    # 100 * (0.6*0.625 + 0.25*1 + 0.15*1) = 37.5 + 25 + 15 = 77.5
    s = score(T2, M2, WEEK, 30, Load(WEEK), TEAM)
    assert s.skill_fit == pytest.approx(0.625)
    assert (s.capacity_fit, s.balance) == (1.0, 1.0)
    assert (s.skill_part, s.capacity_part, s.balance_part) == pytest.approx((37.5, 25, 15))
    assert s.total == pytest.approx(77.5)
    assert [(m.skill, m.fit) for m in s.skills] == [("python", 1.0), ("ml", 0.25)]


def test_score_hand_computed_with_load() -> None:
    # M1 already has 30 h this week: free 10 h -> capacity_fit 10/30; util 30/40 = 0.75 is the
    # team max -> balance 0. skill_fit 1. 100 * (0.6 + 0.25/3 + 0) = 68.33
    load = Load(WEEK)
    load.add(1, WEEK, 30)
    s = score(T2, M1, WEEK, 30, load, TEAM)
    assert s.capacity_fit == pytest.approx(1 / 3)
    assert s.utilisation == pytest.approx(0.75)
    assert s.balance == 0
    assert s.total == pytest.approx(68.333, abs=1e-3)


def test_custom_weights() -> None:
    s = score(T2, M2, WEEK, 30, Load(WEEK), TEAM, AssignmentWeights(1.0, 0.0, 0.0))
    assert s.total == pytest.approx(62.5)


def test_must_skill_gate_allows_one_level_below() -> None:
    task = TaskInput(id=9, o=1, m=1, p=1, required_skills=(RequiredSkill("react", 4),))
    assert is_eligible(task, MemberInput(1, {"react": 3}, 40), WEEK) == (True, None)
    assert is_eligible(task, MemberInput(1, {"react": 2}, 40), WEEK) == (
        False,
        "react: level 2, needs at least 3",
    )
    assert is_eligible(task, MemberInput(1, {}, 40), WEEK)[1] == "react: level 0, needs at least 3"


def test_nice_to_have_skill_never_blocks() -> None:
    assert is_eligible(T2, MemberInput(3, {"python": 3}, 40), WEEK) == (True, None)


def test_leave_more_than_half_the_window_is_ineligible() -> None:
    three = (LeaveRange(date(2026, 11, 9), date(2026, 11, 11)),)
    two = (LeaveRange(date(2026, 11, 9), date(2026, 11, 10)),)
    assert is_eligible(T1, MemberInput(1, {"python": 5}, 40, three), WEEK) == (
        False,
        "on leave 3 of 5 working days",
    )
    assert is_eligible(T1, MemberInput(1, {"python": 5}, 40, two), WEEK) == (True, None)


def test_greedy_is_strictly_worse_than_optimal() -> None:
    # Greedy: T1 first, tie 100/100 -> M1. Then T2: M1 68.33 (loaded), M2 77.5 -> M2. = 177.5
    # Optimal (same wave): T1->M2 (100) and T2->M1 (100) = 200.
    windows = {1: WEEK, 2: WEEK}
    greedy = recommend_greedy([T1, T2], TEAM, windows)
    optimal = recommend_optimal([T1, T2], TEAM, windows)

    assert [r.member_id for r in greedy.recommendations] == [1, 2]
    assert [r.member_id for r in optimal.recommendations] == [2, 1]
    assert greedy.total_score == pytest.approx(177.5)
    assert optimal.total_score == pytest.approx(200)

    c = compare(greedy, optimal)
    assert c.optimal_total > c.greedy_total
    assert (c.greedy_unassigned, c.optimal_unassigned) == (0, 0)


def test_top_candidates_and_ineligible_reasons_are_returned() -> None:
    m3 = MemberInput(3, {"ml": 5}, 40)
    plan = recommend_greedy([T1], [*TEAM, m3], {1: WEEK})
    rec = plan.recommendations[0]
    assert [c.member_id for c in rec.candidates] == [1, 2]
    assert rec.ineligible == ((3, "python: level 0, needs at least 2"),)


def test_nobody_eligible_leaves_task_unassigned() -> None:
    task = TaskInput(id=5, o=1, m=1, p=1, required_skills=(RequiredSkill("rust", 5),))
    for plan in (
        recommend_greedy([task], TEAM, {5: WEEK}),
        recommend_optimal([task], TEAM, {5: WEEK}),
    ):
        assert plan.unassigned == 1
        assert plan.recommendations[0].member_id is None


def test_optimal_handles_more_tasks_than_members_and_waves() -> None:
    # Three independent tasks, two members: round 1 places two, round 2 the third.
    # T4 depends on T1 so it is planned in wave 1 with the load from wave 0.
    tasks = [
        TaskInput(id=i, o=8, m=8, p=8, predecessors=(1,) if i == 4 else ()) for i in (1, 2, 3, 4)
    ]
    windows = dict.fromkeys((1, 2, 3, 4), WEEK)
    plan = recommend_optimal(tasks, TEAM, windows)
    assert plan.unassigned == 0
    assert sorted(plan.utilisation.values()) == pytest.approx([0.4, 0.4])  # 16 h each of 40


def test_zero_capacity_member_gets_no_capacity_points() -> None:
    idle = MemberInput(7, {"python": 5}, 0)
    s = score(T1, idle, WEEK, 30, Load(WEEK), [idle])
    assert s.capacity_fit == 0
    assert s.total == pytest.approx(100 * (0.6 + 0.15))
