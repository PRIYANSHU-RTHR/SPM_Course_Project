"""Declarative base, constraint naming convention and shared column helpers."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Stable constraint names so Alembic diffs and downgrades are deterministic.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utc_now_column(*, index: bool = False) -> Mapped[datetime]:
    """`timestamptz` set by the database clock (UTC)."""
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=index
    )


class TimestampMixin:
    created_at: Mapped[datetime] = utc_now_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def pg_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Native Postgres enum storing the lowercase *values* (not member names)."""
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])
