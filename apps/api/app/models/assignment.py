"""Task → member assignments, kept as history; exactly one `is_current` row per task."""

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, pg_enum, utc_now_column
from app.models.enums import AssignmentSource
from app.models.project import Task
from app.models.team import Member


class Assignment(Base):
    __tablename__ = "assignment"
    __table_args__ = (
        Index(
            "uq_assignment_current_task",
            "task_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("member.id", ondelete="RESTRICT"), index=True)
    # {"score": 91.2, "skill_fit": 0.95, "capacity_fit": 0.8, "balance": 0.7, ...} from the engine.
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    source: Mapped[AssignmentSource] = mapped_column(pg_enum(AssignmentSource, "assignment_source"))
    reason: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = utc_now_column()

    task: Mapped[Task] = relationship(back_populates="assignments")
    member: Mapped[Member] = relationship(back_populates="assignments")
