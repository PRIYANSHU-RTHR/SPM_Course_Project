"""Audit summaries are a pure template over one row plus a name lookup (no DB needed)."""

from typing import Any

import pytest

from app.models import AuditLog
from app.services.audit import Names, actor_label, summarize

NAMES = Names(
    tasks={12: "Payment gateway integration", 31: "UPI refund flow"},
    members={1: "Aarav Mehta", 4: "Diya Shah"},
    risks={7: "Aarav Mehta overbooked in 2 weeks"},
)


def _row(action: str, entity: str, entity_id: int, **kw: Any) -> AuditLog:
    return AuditLog(
        actor=kw.pop("actor", "PM"), action=action, entity=entity, entity_id=entity_id, **kw
    )


@pytest.mark.parametrize(
    ("row", "summary"),
    [
        (
            _row(
                "disruption.leave",
                "project",
                1,
                after={"member_id": 1, "start_date": "2026-11-09", "end_date": "2026-11-20"},
            ),
            "PM recorded leave for Aarav Mehta from 2026-11-09 to 2026-11-20",
        ),
        (
            _row(
                "disruption.slip",
                "task",
                12,
                before={"most_likely_hours": 16.0},
                after={"most_likely_hours": 24.0},
            ),
            "PM recorded a slip on T-012 “Payment gateway integration”: "
            "most likely 16 h → 24 h (+8 h)",
        ),
        (
            _row("disruption.scope_add", "task", 31, after={"most_likely_hours": 12}),
            "PM added new scope T-031 “UPI refund flow”, most likely 12 h",
        ),
        (
            _row(
                "assignment.ai",
                "assignment",
                90,
                actor="pm:asha",
                before={"task_id": 12, "member_id": 1},
                after={"task_id": 12, "member_id": 4, "source": "ai"},
            ),
            "pm:asha reassigned T-012 “Payment gateway integration” from Aarav Mehta to "
            "Diya Shah (AI recommendation)",
        ),
        (
            _row(
                "assignment.pm_override",
                "assignment",
                91,
                after={"task_id": 99, "member_id": 4, "source": "pm_override"},
            ),
            "PM assigned T-099 to Diya Shah (PM override)",
        ),
        (
            _row("reallocation.rejected", "reallocation", 3),
            "PM rejected reallocation proposal #3",
        ),
        (
            _row(
                "risk_opened",
                "risk",
                7,
                actor="system:risk-engine",
                after={"probability": 4, "impact": 5},
            ),
            "Risk engine opened risk “Aarav Mehta overbooked in 2 weeks” (P4 x I5 = 20)",
        ),
        (
            _row("risk_closed", "risk", 8, actor="system:risk-engine", after={"probability": 2}),
            "Risk engine closed risk #8",
        ),
        (
            _row("risk.plan", "risk", 7),
            "PM generated the RMMM plan for risk “Aarav Mehta overbooked in 2 weeks”",
        ),
        (
            _row(
                "simulation.advance",
                "project",
                1,
                before={"sim_date": "2026-11-06"},
                after={"sim_date": "2026-11-20", "working_days": 10},
            ),
            "PM advanced the simulated clock from 2026-11-06 to 2026-11-20 (10 working days)",
        ),
        (
            _row(
                "workflow.plan_approved", "project", 2, after={"epics": 5, "tasks": 25, "edits": 1}
            ),
            "PM approved the generated plan: 5 epics, 25 tasks after 1 edit round",
        ),
        (_row("member.renamed", "member", 4), "PM: member.renamed on member #4"),
    ],
)
def test_summary(row: AuditLog, summary: str) -> None:
    assert summarize(row, NAMES) == summary


def test_missing_values_do_not_crash() -> None:
    row = _row("disruption.slip", "task", 5, before=None, after=None)
    assert summarize(row, Names()) == "PM recorded a slip on T-005: most likely ? → ?"


def test_actor_label() -> None:
    assert actor_label("system:risk-agent") == "Risk agent"
    assert actor_label("pm:asha") == "pm:asha"
