"""Disruption-driven reallocation proposals (one per reallocation workflow run)."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, pg_enum, utc_now_column
from app.models.enums import ReallocationStatus


class Reallocation(Base):
    __tablename__ = "reallocation"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), index=True
    )
    thread_id: Mapped[str] = mapped_column(String(64), unique=True)
    # The disruption as posted: {"type": "leave", "member_id": 3, ...}.
    disruption: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Engine-computed proposal (schemas.reallocation.ProposalPayload).
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    status: Mapped[ReallocationStatus] = mapped_column(
        pg_enum(ReallocationStatus, "reallocation_status"),
        default=ReallocationStatus.PENDING,
        server_default="pending",
        index=True,
    )
    decided_by: Mapped[str | None] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = utc_now_column()
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
