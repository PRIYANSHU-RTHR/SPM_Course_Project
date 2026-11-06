"""Planning agent: demo fixture replay and post-validation rules (fixture mode, no network)."""

from app.agents.llm import LLMClient
from app.agents.planning import (
    DEMO_BRIEF,
    PlannedEpic,
    PlannedTask,
    SkillReq,
    WBSPlan,
    generate_plan,
    match_skill,
    validate_plan,
)
from app.config import Settings
from app.engines.cpm import cpm
from app.engines.types import TaskInput
from app.seed import SKILLS


def _task(lid: str, *, skills=(("python", 3),), o=4.0, m=6.0, p=8.0, preds=()) -> PlannedTask:
    return PlannedTask(
        local_id=lid,
        title=f"Task {lid}",
        required_skills=[SkillReq(skill=s, level=lvl) for s, lvl in skills],
        o=o,
        m=m,
        p=p,
        predecessors=list(preds),
    )


def _plan(*tasks: PlannedTask) -> WBSPlan:
    return WBSPlan(epics=[PlannedEpic(local_id="E1", title="Core", tasks=list(tasks))])


def _tasks(plan: WBSPlan) -> list[PlannedTask]:
    return [t for e in plan.epics for t in e.tasks]


def test_demo_brief_fixture_gives_a_valid_wbs() -> None:
    client = LLMClient(Settings(_env_file=None, llm_mode="fixture"))  # type: ignore[call-arg]
    plan, warnings = generate_plan(client, DEMO_BRIEF.read_text(encoding="utf-8"), SKILLS)

    tasks = _tasks(plan)
    assert len(plan.epics) == 5
    assert [t.local_id for t in tasks] == [f"T-{n:03d}" for n in range(1, 26)]
    assert all(r.skill in SKILLS for t in tasks for r in t.required_skills)
    assert all(t.o <= t.m <= t.p for t in tasks)
    assert sorted(warnings) == sorted(
        [
            "T-005 'Build sign-in and profile screens': skill 'reactjs' mapped to 'react'",
            "T-006 'Build canteen and menu API': skill 'PostgreSQL' mapped to 'postgres'",
            "T-021 'Run end-to-end and device testing': skill 'QA' mapped to 'testing'",
        ]
    )
    # The validated plan feeds straight into the CPM engine.
    num = {t.local_id: k for k, t in enumerate(tasks)}
    result = cpm(
        [
            TaskInput(
                num[t.local_id], t.o, t.m, t.p, predecessors=tuple(num[x] for x in t.predecessors)
            )
            for t in tasks
        ]
    )
    assert result.critical_paths


def test_skill_matching() -> None:
    assert match_skill("React.js", SKILLS) == "react"
    assert match_skill("UI Design", SKILLS) == "ui-design"
    assert match_skill("PostgreSQL", SKILLS) == "postgres"
    assert match_skill("graphql", SKILLS) is None
    assert match_skill("upi", ["react"]) is None  # synonym target not in this vocabulary


def test_bad_skills_are_mapped_dropped_clamped_and_merged() -> None:
    plan, warnings = validate_plan(
        _plan(_task("A", skills=(("graphql", 3), ("Python", 7), ("py", 2)))), SKILLS
    )
    assert [(r.skill, r.level) for r in _tasks(plan)[0].required_skills] == [("python", 5)]
    assert "T-001 'Task A': dropped unknown skill 'graphql'" in warnings
    assert "T-001 'Task A': skill python level 7 clamped to 5" in warnings


def test_task_left_without_skills_is_flagged() -> None:
    _, warnings = validate_plan(_plan(_task("A", skills=(("graphql", 3),))), SKILLS)
    assert "T-001 'Task A': no skill from the vocabulary" in warnings


def test_wrong_three_point_order_and_out_of_range_hours() -> None:
    plan, warnings = validate_plan(_plan(_task("A", o=12, m=6, p=200)), SKILLS)
    t = _tasks(plan)[0]
    assert (t.o, t.m, t.p) == (6, 12, 80)
    assert "T-001 'Task A': o/m/p 12.0/6.0/200.0 reordered" in warnings
    assert "T-001 'Task A': hours clamped to 1-80" in warnings


def test_cycles_are_broken_with_a_warning() -> None:
    # A -> B -> C -> A plus D after C: one link is removed, the rest survive.
    plan, warnings = validate_plan(
        _plan(
            _task("A", preds=("C",)),
            _task("B", preds=("A",)),
            _task("C", preds=("B",)),
            _task("D", preds=("C",)),
        ),
        SKILLS,
    )
    preds = {t.local_id: t.predecessors for t in _tasks(plan)}
    assert preds == {"T-001": [], "T-002": ["T-001"], "T-003": ["T-002"], "T-004": ["T-003"]}
    assert "cycle T-001 -> T-002 -> T-003 -> T-001: removed link T-003 -> T-001" in warnings


def test_unknown_self_and_duplicate_links_are_cleaned() -> None:
    plan, warnings = validate_plan(
        _plan(_task("A"), _task("B", preds=("A", "A", "B", "Z"))), SKILLS
    )
    assert _tasks(plan)[1].predecessors == ["T-001"]
    assert "T-002 'Task B': unknown predecessor 'Z' removed" in warnings
    assert "T-002 'Task B': depends on itself, link removed" in warnings


def test_empty_epic_dropped_and_task_count_flagged() -> None:
    plan = WBSPlan(
        epics=[
            PlannedEpic(local_id="E1", title="Core", tasks=[_task("A")]),
            PlannedEpic(local_id="E2", title="Later", tasks=[]),
        ]
    )
    fixed, warnings = validate_plan(plan, SKILLS)
    assert [e.title for e in fixed.epics] == ["Core"]
    assert "epic 'Later' has no tasks and was dropped" in warnings
    assert "1 tasks; the prompt asks for 15-35" in warnings
    assert len(plan.epics) == 2  # input is not mutated
