"""Earned Value Management. Pure; all money is Decimal (INR, rounded to paise).

BAC = sum of task budgets (planned hours x hourly rate)
PV(t) = each task's budget spread evenly over its baseline working days, summed up to t
EV = sum(percent_complete / 100 x task budget);  AC = sum(actual hours x hourly rate)
SV = EV - PV, CV = EV - AC, SPI = EV / PV, CPI = EV / AC,
EAC = BAC / CPI, ETC = EAC - AC, VAC = BAC - EAC, TCPI = (BAC - EV) / (BAC - AC)
(PMI, PMBOK Guide, earned value formulas; EAC assumes the current CPI continues.)
"""

from collections.abc import Iterable, Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.engines import calendar
from app.engines.types import BaselineTask, EVMResult

PAISE = Decimal("0.01")
ZERO = Decimal("0")


def money(value: Decimal) -> Decimal:
    return value.quantize(PAISE, rounding=ROUND_HALF_UP)


def hours_cost(hours: float, rate: Decimal) -> Decimal:
    """Hours are floats in the model; go through str so 0.1 h does not become 0.1000000001."""
    return money(Decimal(str(hours)) * rate)


def planned_value(baseline: Iterable[BaselineTask], on: date) -> Decimal:
    total = ZERO
    for t in baseline:
        days = calendar.working_days(t.start, t.end)
        if not days:  # zero-length: all value at its start
            total += t.budget if on >= t.start else ZERO
            continue
        done = sum(1 for d in days if d <= on)
        total += t.budget * done / len(days)
    return money(total)


def earned_value(budgets: Sequence[Decimal], percent_complete: Sequence[float]) -> Decimal:
    return money(
        sum(
            (b * Decimal(str(p)) / 100 for b, p in zip(budgets, percent_complete, strict=True)),
            ZERO,
        )
    )


def evm(bac: Decimal, pv: Decimal, ev: Decimal, ac: Decimal) -> EVMResult:
    notes: dict[str, str] = {}
    spi = float(ev / pv) if pv else None
    if spi is None:
        notes["spi"] = "no planned value yet (PV = 0)"
    cpi = float(ev / ac) if ac else None
    if cpi is None:
        notes["cpi"] = "no actual cost yet (AC = 0)"

    eac = etc = vac = None
    if ev and ac:
        eac = money(bac * ac / ev)  # = BAC / CPI, kept exact in Decimal
        etc = money(eac - ac)
        vac = money(bac - eac)
    else:
        reason = "CPI undefined" if not ac else "no earned value yet (EV = 0), CPI is 0"
        for k in ("eac", "etc", "vac"):
            notes[k] = reason

    tcpi = float((bac - ev) / (bac - ac)) if bac != ac else None
    if tcpi is None:
        notes["tcpi"] = "budget fully spent (BAC = AC)"

    return EVMResult(
        bac=money(bac),
        pv=money(pv),
        ev=money(ev),
        ac=money(ac),
        sv=money(ev - pv),
        cv=money(ev - ac),
        spi=spi,
        cpi=cpi,
        eac=eac,
        etc=etc,
        vac=vac,
        tcpi=tcpi,
        notes=notes,
    )
