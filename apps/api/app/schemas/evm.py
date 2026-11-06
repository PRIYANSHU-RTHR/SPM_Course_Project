"""Response schema for GET /projects/{id}/evm. Money is INR as a decimal string."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class EvmPointOut(BaseModel):
    on: date
    pv: Decimal
    ev: Decimal | None = Field(description="null on planned-only points")
    ac: Decimal | None


class ProjectEvm(BaseModel):
    project_id: int
    as_of: date
    budget: Decimal = Field(description="Project budget as entered (for comparison with BAC)")
    bac: Decimal = Field(description="Sum of task budgets: PERT hours x hourly rate")
    pv: Decimal
    ev: Decimal
    ac: Decimal
    sv: Decimal
    cv: Decimal
    spi: float | None
    cpi: float | None
    eac: Decimal | None
    etc: Decimal | None
    vac: Decimal | None
    tcpi: float | None
    notes: dict[str, str] = Field(description="Why a metric is null")
    snapshots: list[EvmPointOut] = Field(description="Recorded progress, PV from the baseline")
    planned: list[EvmPointOut] = Field(description="Weekly PV curve (Fridays) to the finish")
