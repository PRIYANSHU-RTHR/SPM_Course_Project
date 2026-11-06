"""Risk rules: each fires just past its threshold and stays quiet exactly at it."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.engines.cpm import cpm
from app.engines.evm import evm
from app.engines.risk import (
    RiskConfig,
    RiskSnapshot,
    TaskState,
    bus_factor,
    cpi_low,
    detect_risks,
    late_predecessor,
    low_on_time_probability,
    member_overload,
    score_at_least,
    score_below,
    skill_gap,
    spi_low,
)
from app.engines.types import (
    ForecastResult,
    LeaveRange,
    MemberInput,
    MemberWeekLoad,
    RequiredSkill,
    ScheduledTask,
    ScheduleResult,
    TaskInput,
)

CFG = RiskConfig()
MON = date(2026, 11, 2)  # project start, a Monday
FRI = date(2026, 11, 6)
NEXT_MON = date(2026, 11, 9)

# A (16h) -> B (8h); C (4h) runs in parallel with slack.
A = TaskInput(id=1, o=16, m=16, p=16, required_skills=(RequiredSkill("python", 4),))
B = TaskInput(id=2, o=8, m=8, p=8, predecessors=(1,))
C = TaskInput(id=3, o=4, m=4, p=4)
TASKS = (A, B, C)

ADITI = MemberInput(id=10, skills={"python": 4}, hours_per_week=40)
RAVI = MemberInput(id=11, skills={"react": 4}, hours_per_week=40)


def _scheduled(task_id: int, start: date, end: date, hours: float) -> ScheduledTask:
    return ScheduledTask(task_id, None, start, end, hours, start, 0)


SCHEDULE = ScheduleResult(
    tasks=(
        _scheduled(1, MON, date(2026, 11, 3), 16),
        _scheduled(2, date(2026, 11, 4), date(2026, 11, 4), 8),
        _scheduled(3, MON, MON, 4),
    ),
    loads=(),
    finish=date(2026, 11, 4),
    delayed=(),
)


def snapshot(**overrides: object) -> RiskSnapshot:
    base = RiskSnapshot(
        as_of=MON,
        project_start=MON,
        tasks=TASKS,
        task_state={1: TaskState("Payment API"), 2: TaskState("Checkout UI"), 3: TaskState("Docs")},
        members=(ADITI, RAVI),
        member_names={10: "Aditi Sharma", 11: "Ravi Kumawat"},
        assignments={1: 10, 2: 11, 3: 11},
        cpm=cpm(list(TASKS)),
        schedule=SCHEDULE,
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def forecast_result(p_on_time: float, p80: float = 120.0) -> ForecastResult:
    return ForecastResult(
        runs=5000,
        seed=42,
        deadline_hours=100.0,
        p_on_time=p_on_time,
        mean=95.0,
        p50=96.0,
        p80=p80,
        p95=130.0,
        histogram=(),
        cdf=(),
    )


def week(member_id: int, hours: float, capacity: float, start: date = MON) -> MemberWeekLoad:
    util = hours / capacity if capacity else 0.0
    return MemberWeekLoad(member_id, start, hours, capacity, util)


# --- band tables -------------------------------------------------------------------------


def test_band_tables_are_inclusive_lower_and_exclusive_upper() -> None:
    assert score_at_least(3, ((3, 5), (2, 4), (1, 3))) == 5
    assert score_at_least(2.99, ((3, 5), (2, 4), (1, 3))) == 4
    assert score_below(0.80, ((0.80, 5), (0.85, 4), (0.90, 3))) == 4
    assert score_below(0.7999, ((0.80, 5), (0.85, 4), (0.90, 3))) == 5


# --- member_overload ---------------------------------------------------------------------


def test_overload_quiet_at_exactly_full_capacity() -> None:
    snap = snapshot(schedule=replace(SCHEDULE, loads=(week(10, 40, 40),)))
    assert member_overload(snap, CFG) == []


def test_overload_fires_just_above_capacity() -> None:
    snap = snapshot(schedule=replace(SCHEDULE, loads=(week(10, 41, 40), week(11, 20, 40))))

    [finding] = member_overload(snap, CFG)

    assert (finding.subject_ref, finding.category) == ("member:10", "resource")
    assert (finding.probability, finding.impact) == (3, 3)  # 1 week over; peak 1.025
    assert finding.evidence["weeks_over"] == 1
    assert finding.evidence["peak_utilisation"] == 1.025
    assert finding.title == "Aditi Sharma is over capacity in 1 week(s), peak 102%"


def test_overload_scores_follow_tables_and_zero_capacity_counts() -> None:
    loads = (
        week(10, 50, 40, MON),
        week(10, 61, 40, NEXT_MON),
        week(10, 8, 0, date(2026, 11, 16)),  # booked during a week with no capacity
    )
    [finding] = member_overload(snapshot(schedule=replace(SCHEDULE, loads=loads)), CFG)

    assert finding.probability == 5  # 3 weeks over
    assert finding.impact == 5  # infinite peak
    assert finding.evidence["peak_utilisation"] is None


# --- bus_factor ----------------------------------------------------------------------------


def test_bus_factor_fires_when_one_person_can_do_a_critical_task() -> None:
    weak = MemberInput(id=12, skills={"python": 2}, hours_per_week=40)  # below level - 1

    [finding] = bus_factor(snapshot(members=(ADITI, RAVI, weak)), CFG)

    assert finding.subject_ref == "task:1"
    assert finding.evidence["eligible_members"] == 1
    assert finding.title == "T-001 Payment API: only Aditi Sharma can do this critical task"
    assert (finding.probability, finding.impact) == (4, 4)  # criticality 1.0; 16 h


def test_bus_factor_quiet_with_a_second_eligible_person() -> None:
    backup = MemberInput(id=12, skills={"python": 3}, hours_per_week=40)  # exactly level - 1
    assert bus_factor(snapshot(members=(ADITI, RAVI, backup)), CFG) == []


def test_bus_factor_ignores_non_critical_and_done_tasks() -> None:
    done = snapshot(task_state={1: TaskState("Payment API", "done")})
    assert bus_factor(done, CFG) == []

    slack_task = TaskInput(id=3, o=4, m=4, p=4, required_skills=(RequiredSkill("python", 4),))
    snap = snapshot(tasks=(A, B, slack_task), cpm=cpm([A, B, slack_task]))
    assert [f.subject_ref for f in bus_factor(snap, CFG)] == ["task:1"]


# --- spi_low / cpi_low ----------------------------------------------------------------------


def test_spi_quiet_at_threshold_and_fires_below() -> None:
    at = evm(Decimal("100000"), Decimal("50000"), Decimal("45000"), Decimal("45000"))
    below = evm(Decimal("100000"), Decimal("50000"), Decimal("44500"), Decimal("44500"))

    assert at.spi == pytest.approx(0.90)
    assert spi_low(snapshot(evm=at), CFG) == []

    [finding] = spi_low(snapshot(evm=below), CFG)
    assert (finding.rule_key, finding.subject_ref, finding.category) == (
        "spi_low",
        "project",
        "schedule",
    )
    assert finding.probability == 3  # SPI 0.89
    assert finding.impact == 4  # -SV / BAC = 0.055
    assert finding.evidence["spi"] == 0.89


def test_cpi_quiet_at_threshold_and_fires_below() -> None:
    at = evm(Decimal("100000"), Decimal("50000"), Decimal("45000"), Decimal("50000"))
    below = evm(Decimal("100000"), Decimal("50000"), Decimal("45000"), Decimal("60000"))

    assert at.cpi == pytest.approx(0.90)
    assert cpi_low(snapshot(evm=at), CFG) == []

    [finding] = cpi_low(snapshot(evm=below), CFG)
    assert finding.category == "cost"
    assert finding.probability == 5  # CPI 0.75
    assert finding.impact == 5  # EAC 133 333 vs BAC 100 000 = 33% overrun


def test_spi_cpi_quiet_when_ratio_undefined() -> None:
    nothing_planned = evm(Decimal("100000"), Decimal("0"), Decimal("0"), Decimal("0"))
    assert spi_low(snapshot(evm=nothing_planned), CFG) == []
    assert cpi_low(snapshot(evm=nothing_planned), CFG) == []


def test_evm_rules_wait_until_enough_value_is_planned() -> None:
    # PV is 4.9% of BAC: SPI 0 and CPI 0.5 are ignored as early-project noise.
    early = evm(Decimal("100000"), Decimal("4900"), Decimal("0"), Decimal("1000"))
    assert spi_low(snapshot(evm=early), CFG) == []
    assert cpi_low(snapshot(evm=early), CFG) == []

    # Exactly 5%: judged.
    judged = evm(Decimal("100000"), Decimal("5000"), Decimal("1000"), Decimal("2000"))
    assert [f.rule_key for f in spi_low(snapshot(evm=judged), CFG)] == ["spi_low"]
    assert [f.rule_key for f in cpi_low(snapshot(evm=judged), CFG)] == ["cpi_low"]


# --- low_on_time_probability ----------------------------------------------------------------


def test_on_time_quiet_at_threshold() -> None:
    assert low_on_time_probability(snapshot(forecast=forecast_result(0.60)), CFG) == []


def test_on_time_fires_below_threshold_with_table_scores() -> None:
    [mild] = low_on_time_probability(snapshot(forecast=forecast_result(0.59, p80=104)), CFG)
    [severe] = low_on_time_probability(snapshot(forecast=forecast_result(0.29, p80=120)), CFG)

    assert (mild.probability, mild.impact) == (3, 3)  # P80 4% over deadline
    assert (severe.probability, severe.impact) == (5, 5)  # P80 20% over deadline
    assert severe.title == "P(on time) is 29%, below 60%"
    assert severe.evidence["deadline_hours"] == 100.0


# --- late_predecessor ------------------------------------------------------------------------


def test_late_predecessor_quiet_on_planned_end_day_and_over_weekend() -> None:
    a_end = date(2026, 11, 3)
    assert late_predecessor(snapshot(as_of=a_end), CFG) == []

    friday_end = replace(SCHEDULE, tasks=(_scheduled(1, MON, FRI, 16), *SCHEDULE.tasks[1:]))
    saturday = date(2026, 11, 7)
    assert late_predecessor(snapshot(schedule=friday_end, as_of=saturday), CFG) == []


def test_late_predecessor_fires_one_working_day_after_planned_end() -> None:
    [finding] = late_predecessor(snapshot(as_of=date(2026, 11, 4)), CFG)

    assert finding.subject_ref == "task:2"
    assert finding.evidence["working_days_late"] == 1
    assert finding.evidence["predecessor_id"] == 1
    assert (finding.probability, finding.impact) == (3, 5)  # 1 day; successor is critical
    assert (
        finding.title == "T-002 Checkout UI is blocked by T-001 Payment API, 1 working day(s) late"
    )


def test_late_predecessor_quiet_when_predecessor_done() -> None:
    state = {1: TaskState("Payment API", "done"), 2: TaskState("Checkout UI")}
    assert late_predecessor(snapshot(as_of=date(2026, 11, 20), task_state=state), CFG) == []


# --- skill_gap ------------------------------------------------------------------------------


def test_skill_gap_quiet_when_someone_is_one_level_short() -> None:
    near = MemberInput(id=10, skills={"python": 3}, hours_per_week=40)  # level - 1 is eligible
    assert skill_gap(snapshot(members=(near, RAVI)), CFG) == []


def test_skill_gap_fires_when_nobody_qualifies() -> None:
    weak = MemberInput(id=10, skills={"python": 2}, hours_per_week=40)

    [finding] = skill_gap(snapshot(members=(weak, RAVI)), CFG)

    assert (finding.subject_ref, finding.category) == ("task:1", "skill")
    assert (finding.probability, finding.impact) == (5, 5)
    assert finding.evidence["must_skills"] == "python>=4"


def test_skill_gap_fires_when_the_only_expert_is_on_leave() -> None:
    away = replace(ADITI, leave=(LeaveRange(MON, date(2026, 11, 13)),))

    [finding] = skill_gap(snapshot(members=(away, RAVI)), CFG)

    assert finding.subject_ref == "task:1"


# --- detect_risks ---------------------------------------------------------------------------


def test_detect_risks_sorts_by_score_and_is_deterministic() -> None:
    snap = snapshot(
        members=(MemberInput(id=10, skills={}, hours_per_week=40), RAVI),
        forecast=forecast_result(0.59, p80=104),
        schedule=replace(SCHEDULE, loads=(week(11, 41, 40),)),
        as_of=date(2026, 11, 4),
    )

    findings = detect_risks(snap)

    assert [(f.rule_key, f.subject_ref, f.score) for f in findings] == [
        ("skill_gap", "task:1", 25),
        ("late_predecessor", "task:2", 15),
        ("low_on_time_probability", "project", 9),
        ("member_overload", "member:11", 9),
    ]
    assert detect_risks(snap) == findings


def test_custom_config_changes_threshold() -> None:
    snap = snapshot(forecast=forecast_result(0.65))

    def keys(cfg: RiskConfig | None) -> list[str]:
        return [f.rule_key for f in detect_risks(snap, cfg) if f.subject_ref == "project"]

    assert keys(None) == []
    assert keys(RiskConfig(p_on_time_threshold=0.7)) == ["low_on_time_probability"]
