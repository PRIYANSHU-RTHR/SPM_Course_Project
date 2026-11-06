"""Progress snapshots (EVM inputs) and the immutable audit log."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now_column


class Snapshot(Base):
    """Cumulative planned value, earned value and actual cost on a date (INR, 2 dp)."""

    __tablename__ = "snapshot"
    __table_args__ = (UniqueConstraint("project_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    pv: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    ev: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    ac: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = utc_now_column()


class AuditLog(Base):
    """Append-only record of every state-changing PM action."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int]
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = utc_now_column(index=True)
