"""PM edits on the WBS and the helpers the planning graph is built from (pure, no DB)."""

from datetime import date

import pytest

from app.agents.planning import PlannedEpic, PlannedTask, SkillReq, WBSPlan
from app.engines.types import MemberInput
from app.schemas.workflow import TaskChange
from app.workflows.plan import EditError, apply_changes, skill_gaps, task_inputs, wbs_tasks

VOCAB = ["python", "react", "testing"]


def _task(lid: str, preds: tuple[str, ...] = (), skill: str = "python") -> PlannedTask:
    return PlannedTask(
        local_id=lid,
        title=f"Task {lid}",
        required_skills=[SkillReq(skill=skill, level=3)],
        o=4,
        m=6,
        p=8,
        predecessors=list(preds),
    )


def _plan() -> WBSPlan:
    """T-001 -> T-002 -> T-003, and T-004 on its own in a second epic."""
    return WBSPlan(
        epics=[
            PlannedEpic(
                local_id="E1",
                title="Core",
                tasks=[_task("T-001"), _task("T-002", ("T-001",)), _task("T-003", ("T-002",))],
            ),
            PlannedEpic(local_id="E2", title="QA", tasks=[_task("T-004", skill="testing")]),
        ]
    )


def _by_id(plan: WBSPlan) -> dict[str, PlannedTask]:
    return {t.local_id: t for t in wbs_tasks(plan)}


def test_update_sets_only_given_fields_and_maps_skill_names() -> None:
    original = _plan()
    changes = [
        TaskChange(op="update", task_id="T-002", m=10, p=20),
        TaskChange(
            op="update", task_id="T-004", required_skills=[SkillReq(skill="React.js", level=4)]
        ),
    ]

    edited = _by_id(apply_changes(original, changes, VOCAB))

    assert (edited["T-002"].o, edited["T-002"].m, edited["T-002"].p) == (4, 10, 20)
    assert edited["T-002"].title == "Task T-002"
    assert edited["T-004"].required_skills == [SkillReq(skill="react", level=4)]
    assert _by_id(original)["T-002"].m == 6  # the input plan is not modified


def test_remove_drops_links_to_the_task_and_empty_epics() -> None:
    edited = apply_changes(_plan(), [TaskChange(op="remove", task_id="T-004")], VOCAB)
    assert [e.local_id for e in edited.epics] == ["E1"]

    edited = apply_changes(_plan(), [TaskChange(op="remove", task_id="T-002")], VOCAB)
    assert _by_id(edited)["T-003"].predecessors == []
    assert list(_by_id(edited)) == ["T-001", "T-003", "T-004"]  # ids are not renumbered


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (TaskChange(op="update", task_id="T-999", m=5), "unknown task T-999"),
        (TaskChange(op="update", task_id="T-001", o=9), "o <= m <= p"),
        (TaskChange(op="update", task_id="T-001", p=200), "<= 80 hours"),
        (
            TaskChange(
                op="update", task_id="T-001", required_skills=[SkillReq(skill="cobol", level=3)]
            ),
            "unknown skill 'cobol'",
        ),
        (
            TaskChange(
                op="update", task_id="T-001", required_skills=[SkillReq(skill="react", level=6)]
            ),
            "level must be 1-5",
        ),
        (TaskChange(op="update", task_id="T-001", predecessors=["T-001"]), "itself"),
        (TaskChange(op="update", task_id="T-001", predecessors=["T-404"]), "unknown predecessor"),
        (
            TaskChange(op="update", task_id="T-001", predecessors=["T-003"]),
            "cycle: ",
        ),
    ],
)
def test_invalid_edits_are_rejected_not_repaired(change: TaskChange, message: str) -> None:
    with pytest.raises(EditError, match=message.replace("(", r"\(")):
        apply_changes(_plan(), [change], VOCAB)


def test_cycle_message_names_the_loop() -> None:
    with pytest.raises(EditError) as exc:
        apply_changes(
            _plan(), [TaskChange(op="update", task_id="T-001", predecessors=["T-003"])], VOCAB
        )
    assert "T-001" in str(exc.value)
    assert "T-003" in str(exc.value)


def test_removing_every_task_is_rejected() -> None:
    changes = [TaskChange(op="remove", task_id=f"T-00{n}") for n in range(1, 5)]
    with pytest.raises(EditError, match="at least one task"):
        apply_changes(_plan(), changes, VOCAB)


def test_task_inputs_number_tasks_in_wbs_order() -> None:
    tasks, label = task_inputs(_plan())

    assert [t.id for t in tasks] == [1, 2, 3, 4]
    assert label == {1: "T-001", 2: "T-002", 3: "T-003", 4: "T-004"}
    assert tasks[2].predecessors == (2,)


def test_skill_gaps_use_the_assignment_eligibility_rule() -> None:
    window = (date(2026, 11, 9), date(2026, 12, 18))
    pythonista = MemberInput(id=1, skills={"python": 2}, hours_per_week=40)  # 2 >= 3 - 1: ok

    assert skill_gaps(_plan(), [pythonista], window) == [
        "T-004: no team member has the must-have skills"
    ]
    assert skill_gaps(_plan(), [], window) == [
        "the team has no members, so no task can be assigned"
    ]
