"""Project plan: project, epics, tasks and task dependencies."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pg_enum
from app.models.enums import DependencyType, TaskStatus

if TYPE_CHECKING:
    from app.models.assignment import Assignment


class Project(TimestampMixin, Base):
    __tablename__ = "project"
    __table_args__ = (
        CheckConstraint("budget >= 0", name="budget_non_negative"),
        CheckConstraint("hourly_rate >= 0", name="hourly_rate_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    brief: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    deadline: Mapped[date] = mapped_column(Date)
    # Money as exact decimals (INR, 2 dp) — never float.
    budget: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    epics: Mapped[list["Epic"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Epic.position",
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )


class Epic(TimestampMixin, Base):
    __tablename__ = "epic"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(default=0, server_default=text("0"))

    project: Mapped[Project] = relationship(back_populates="epics")
    # DB cascade (FK ON DELETE CASCADE) removes tasks; the ORM must not try to null epic_id.
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="epic", cascade="all", passive_deletes=True
    )


class Task(TimestampMixin, Base):
    __tablename__ = "task"
    __table_args__ = (
        CheckConstraint(
            "0 <= optimistic_hours AND optimistic_hours <= most_likely_hours "
            "AND most_likely_hours <= pessimistic_hours",
            name="pert_order",
        ),
        CheckConstraint("priority BETWEEN 1 AND 5", name="priority_range"),
        CheckConstraint("percent_complete BETWEEN 0 AND 100", name="percent_complete_range"),
        CheckConstraint("actual_hours >= 0", name="actual_hours_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), index=True
    )
    epic_id: Mapped[int] = mapped_column(ForeignKey("epic.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    optimistic_hours: Mapped[float] = mapped_column(Float)
    most_likely_hours: Mapped[float] = mapped_column(Float)
    pessimistic_hours: Mapped[float] = mapped_column(Float)
    priority: Mapped[int] = mapped_column(default=3, server_default=text("3"))
    status: Mapped[TaskStatus] = mapped_column(
        pg_enum(TaskStatus, "task_status"), default=TaskStatus.TODO, server_default="todo"
    )
    # [{"skill": "react", "level": 3, "must": true}, ...] — skill names from the skill table.
    required_skills: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    percent_complete: Mapped[float] = mapped_column(Float, default=0.0, server_default=text("0"))
    actual_hours: Mapped[float] = mapped_column(Float, default=0.0, server_default=text("0"))

    project: Mapped[Project] = relationship(back_populates="tasks")
    epic: Mapped[Epic] = relationship(back_populates="tasks")
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )


class Dependency(Base):
    """`pred` must finish before `succ` starts (FS)."""

    __tablename__ = "dependency"
    __table_args__ = (
        UniqueConstraint("pred_task_id", "succ_task_id"),
        CheckConstraint("pred_task_id <> succ_task_id", name="no_self_loop"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pred_task_id: Mapped[int] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"))
    succ_task_id: Mapped[int] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"), index=True)
    type: Mapped[DependencyType] = mapped_column(
        pg_enum(DependencyType, "dependency_type"),
        default=DependencyType.FS,
        server_default="FS",
    )

    pred: Mapped[Task] = relationship(foreign_keys=[pred_task_id])
    succ: Mapped[Task] = relationship(foreign_keys=[succ_task_id])
