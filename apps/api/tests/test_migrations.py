"""Runs the Alembic migrations against the compose Postgres.

Each test gets a throwaway database (`orchestrai_test_<hex>`) created next to the one in
DATABASE_URL and dropped afterwards, so dev/seed data is never touched. The whole module is
skipped when Postgres is not reachable.
"""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import URL, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    AssignmentSource,
    Base,
    Dependency,
    Epic,
    Member,
    Project,
    Risk,
    RiskCategory,
    Task,
)
from tests import pg

EXPECTED_TABLES = {
    "alembic_version",
    "assignment",
    "audit_log",
    "availability",
    "dependency",
    "epic",
    "member",
    "member_skill",
    "project",
    "reallocation",
    "risk",
    "skill",
    "snapshot",
    "task",
}
EXPECTED_ENUMS = {
    "assignment_source",
    "availability_kind",
    "dependency_type",
    "reallocation_status",
    "risk_category",
    "risk_status",
    "task_status",
}


_reason = pg.skip_reason()
if _reason:
    pytest.skip(_reason, allow_module_level=True)


@pytest.fixture
def temp_db_url() -> Iterator[URL]:
    with pg.temp_database() as url:
        yield url


@pytest.fixture
def migrated_db(temp_db_url: URL) -> Iterator[URL]:
    command.upgrade(pg.alembic_config(temp_db_url), "head")
    yield temp_db_url


def _enum_names(url: URL) -> set[str]:
    engine = create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'"))
        names = {row[0] for row in rows}
    engine.dispose()
    return names


def test_upgrade_creates_every_table_and_enum(migrated_db: URL) -> None:
    engine = create_engine(migrated_db)
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES
    engine.dispose()
    assert _enum_names(migrated_db) == EXPECTED_ENUMS


def test_models_match_migration(migrated_db: URL) -> None:
    engine = create_engine(migrated_db)
    with engine.connect() as conn:
        diff = compare_metadata(
            MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata
        )
    engine.dispose()
    assert diff == [], (
        f"models and migrations differ; run `alembic revision --autogenerate`: {diff}"
    )


def test_downgrade_removes_everything_and_upgrade_again(migrated_db: URL) -> None:
    cfg = pg.alembic_config(migrated_db)

    command.downgrade(cfg, "base")
    engine = create_engine(migrated_db)
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()
    assert _enum_names(migrated_db) == set()

    command.upgrade(cfg, "head")


# --- constraints -------------------------------------------------------------------------


def _seed_minimal(session: Session) -> tuple[Project, Epic, Member]:
    project = Project(
        name="Campus Food-Ordering App",
        start_date=date(2026, 11, 2),
        deadline=date(2027, 1, 29),
        budget=Decimal("850000.00"),
        hourly_rate=Decimal("1200.00"),
    )
    epic = Epic(project=project, title="Ordering", position=1)
    member = Member(name="Aditi Sharma", role="Backend Engineer", email="aditi@example.test")
    session.add_all([project, epic, member])
    session.flush()
    return project, epic, member


def _task(project: Project, epic: Epic, title: str, o: float, m: float, p: float) -> Task:
    return Task(
        project=project,
        epic=epic,
        title=title,
        optimistic_hours=o,
        most_likely_hours=m,
        pessimistic_hours=p,
        required_skills=[{"skill": "python", "level": 3, "must": True}],
    )


@pytest.fixture
def session(migrated_db: URL) -> Iterator[Session]:
    engine = create_engine(migrated_db)
    with Session(engine) as s:
        yield s
    engine.dispose()


def test_valid_rows_insert_with_server_defaults(session: Session) -> None:
    project, epic, _ = _seed_minimal(session)
    task = _task(project, epic, "Menu API", 4, 6, 10)
    session.add(task)
    session.commit()
    session.refresh(task)

    assert task.status == "todo"
    assert task.priority == 3
    assert task.percent_complete == 0
    assert task.created_at.tzinfo is not None
    assert task.required_skills == [{"skill": "python", "level": 3, "must": True}]


def test_task_pert_order_is_enforced(session: Session) -> None:
    project, epic, _ = _seed_minimal(session)
    session.add(_task(project, epic, "Bad estimate", 8, 6, 10))
    with pytest.raises(IntegrityError, match="ck_task_pert_order"):
        session.flush()


def test_task_priority_range_is_enforced(session: Session) -> None:
    project, epic, _ = _seed_minimal(session)
    task = _task(project, epic, "Out of range", 1, 2, 3)
    task.priority = 6
    session.add(task)
    with pytest.raises(IntegrityError, match="ck_task_priority_range"):
        session.flush()


def test_dependency_rejects_self_loop_and_duplicates(session: Session) -> None:
    project, epic, _ = _seed_minimal(session)
    a = _task(project, epic, "A", 1, 2, 3)
    b = _task(project, epic, "B", 1, 2, 3)
    session.add_all([a, b])
    session.flush()

    session.add(Dependency(pred_task_id=a.id, succ_task_id=a.id))
    with pytest.raises(IntegrityError, match="ck_dependency_no_self_loop"):
        session.flush()
    session.rollback()

    project, epic, _ = _seed_minimal(session)
    a = _task(project, epic, "A", 1, 2, 3)
    b = _task(project, epic, "B", 1, 2, 3)
    session.add_all([a, b])
    session.flush()
    session.add(Dependency(pred_task_id=a.id, succ_task_id=b.id))
    session.flush()
    session.add(Dependency(pred_task_id=a.id, succ_task_id=b.id))
    with pytest.raises(IntegrityError, match="uq_dependency_pred_task_id_succ_task_id"):
        session.flush()


def test_only_one_current_assignment_per_task(session: Session) -> None:
    project, epic, member = _seed_minimal(session)
    task = _task(project, epic, "Checkout flow", 6, 8, 14)
    session.add(task)
    session.flush()

    # History rows are fine as long as only one is current.
    session.add(Assignment(task=task, member=member, source=AssignmentSource.AI, is_current=False))
    session.add(Assignment(task=task, member=member, source=AssignmentSource.AI, is_current=True))
    session.flush()

    session.add(
        Assignment(task=task, member=member, source=AssignmentSource.PM_OVERRIDE, is_current=True)
    )
    with pytest.raises(IntegrityError, match="uq_assignment_current_task"):
        session.flush()


def test_risk_is_unique_per_rule_and_subject(session: Session) -> None:
    project, _, _ = _seed_minimal(session)

    def risk() -> Risk:
        return Risk(
            project_id=project.id,
            rule_key="member_overload",
            subject_ref="member:1",
            title="Aditi is at 130% utilisation in week 3",
            category=RiskCategory.RESOURCE,
            probability=4,
            impact=3,
        )

    session.add(risk())
    session.flush()
    session.add(risk())
    with pytest.raises(IntegrityError, match="uq_risk_project_id_rule_key_subject_ref"):
        session.flush()
