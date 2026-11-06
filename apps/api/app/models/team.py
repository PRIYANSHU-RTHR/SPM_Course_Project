"""Team: members, skills, skill levels and availability."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pg_enum, utc_now_column
from app.models.enums import AvailabilityKind

if TYPE_CHECKING:
    from app.models.assignment import Assignment


class Member(TimestampMixin, Base):
    __tablename__ = "member"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254), unique=True)

    skills: Mapped[list["MemberSkill"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )
    availability: Mapped[list["Availability"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )
    # passive_deletes="all": never null member_id; the FK (ON DELETE RESTRICT) decides.
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="member", passive_deletes="all"
    )


class Skill(Base):
    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = utc_now_column()


class MemberSkill(Base):
    __tablename__ = "member_skill"
    __table_args__ = (
        UniqueConstraint("member_id", "skill_id"),
        CheckConstraint("level BETWEEN 1 AND 5", name="level_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("member.id", ondelete="CASCADE"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id", ondelete="CASCADE"), index=True)
    level: Mapped[int]

    member: Mapped[Member] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()


class Availability(Base):
    """A date range for one member: working capacity (`work`) or time off (`leave`, 0 h/week)."""

    __tablename__ = "availability"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="range_order"),
        CheckConstraint("hours_per_week >= 0 AND hours_per_week <= 80", name="hours_range"),
        CheckConstraint("kind <> 'leave' OR hours_per_week = 0", name="leave_zero_hours"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("member.id", ondelete="CASCADE"), index=True)
    kind: Mapped[AvailabilityKind] = mapped_column(pg_enum(AvailabilityKind, "availability_kind"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    hours_per_week: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = utc_now_column()

    member: Mapped[Member] = relationship(back_populates="availability")
