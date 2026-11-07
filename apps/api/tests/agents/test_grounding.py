"""Number grounding check used by the explanation and risk agents."""

from app.agents.grounding import fact_numbers, ungrounded_numbers

FACTS = fact_numbers({"total": 91.2, "skill_fit": 0.625, "free": 32.0, "sv": -1200, "ok": True})


def test_rounded_and_exact_numbers_are_grounded() -> None:
    assert ungrounded_numbers("Scores 91 (91.2), skill fit 0.63 or 0.625, 32 h free.", FACTS) == []


def test_percent_matches_the_fraction_and_commas_and_signs_are_ignored() -> None:
    assert ungrounded_numbers("Skill fit 62.5%, behind by 1,200 (SV -1200).", FACTS) == []


def test_ids_are_not_numbers_but_invented_values_are_caught() -> None:
    assert ungrounded_numbers("T-014 goes to member M-3.", FACTS) == []
    assert ungrounded_numbers("Scores 92 and saves 15% of the time.", FACTS) == ["92", "15%"]


def test_bools_are_not_facts() -> None:
    assert 1.0 not in FACTS
