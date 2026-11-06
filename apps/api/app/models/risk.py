"""Risk register (RMMM). Detectors upsert on (project_id, rule_key, subject_ref)."""

from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, pg_enum
from app.models.enums import RiskCategory, RiskStatus


class Risk(TimestampMixin, Base):
    __tablename__ = "risk"
    __table_args__ = (
        UniqueConstraint("project_id", "rule_key", "subject_ref"),
        CheckConstraint("probability BETWEEN 1 AND 5", name="probability_range"),
        CheckConstraint("impact BETWEEN 1 AND 5", name="impact_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"))
    # Which detector raised it (e.g. "member_overload") and about what (e.g. "member:3").
    rule_key: Mapped[str] = mapped_column(String(64))
    subject_ref: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[RiskCategory] = mapped_column(pg_enum(RiskCategory, "risk_category"))
    probability: Mapped[int]
    impact: Mapped[int]
    status: Mapped[RiskStatus] = mapped_column(
        pg_enum(RiskStatus, "risk_status"), default=RiskStatus.OPEN, server_default="open"
    )
    # {"mitigation": str, "monitoring": str, "management": str} from the risk agent.
    rmmm: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
