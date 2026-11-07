"""Number grounding: every number in model prose must come from the facts it was given.

A number in the text matches a fact value if the value, rounded to the number of decimals
written, equals it ("91" matches 91.2, "0.63" matches 0.625). A percentage also matches the
fraction ("60%" matches 0.6). Signs are ignored ("SV of 1,200 behind" vs -1200). Ids like
T-014 are not counted as numbers.
"""

import re
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from typing import Any

from pydantic import BaseModel

_ID = re.compile(r"\b[A-Z]{1,3}-\d+\b")
_NUMBER = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(%?)")


def fact_numbers(obj: Any) -> set[float]:
    """Every int/float anywhere in the facts (bools excluded)."""
    if isinstance(obj, BaseModel):
        obj = obj.model_dump()
    elif is_dataclass(obj) and not isinstance(obj, type):
        obj = asdict(obj)
    if isinstance(obj, bool) or obj is None:
        return set()
    if isinstance(obj, int | float):
        return {abs(float(obj))}
    if isinstance(obj, dict):
        return {n for v in obj.values() for n in fact_numbers(v)}
    if isinstance(obj, list | tuple | set):
        return {n for v in obj for n in fact_numbers(v)}
    return set()


def _matches(written: float, decimals: int, percent: bool, facts: Iterable[float]) -> bool:
    # Within half a unit of the last written digit, so 0.625 may be written 0.62 or 0.63.
    tolerance = 0.5 * 10**-decimals + 1e-9
    for value in facts:
        if abs(value - written) <= tolerance:
            return True
        if percent and abs(value * 100 - written) <= tolerance:
            return True
    return False


def ungrounded_numbers(text: str, facts: set[float]) -> list[str]:
    """Numbers written in `text` that no fact accounts for (empty list = grounded)."""
    bad = []
    for match in _NUMBER.finditer(_ID.sub(" ", text)):
        whole, frac, pct = match.groups()
        written = float(whole.replace(",", "") + (f".{frac}" if frac else ""))
        if not _matches(written, len(frac or ""), pct == "%", facts):
            bad.append(match.group(0))
    return bad
