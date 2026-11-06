"""Seed data checks. The checks on the data itself need no database."""

import random
import uuid
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import URL, create_engine, func, make_url, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Assignment, Base, Dependency, Epic, Member, Project, Snapshot, Task
from app.seed import (
    DEPENDENCIES,
    EPICS,
    MEMBERS,
    SKILLS,
    SNAPSHOT_DAYS,
    TASKS,
    _progress_curve,
    parse_skills,
    seed_demo,
)

API_DIR = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 11, 6)
VOLATILE_COLUMNS = {"created_at", "updated_at"}


def test_task_estimates_and_ids_are_valid() -> None:
    assert 20 <= len(TASKS) <= 30
    for task in TASKS:
        assert 0 <= task.o <= task.m <= task.p
        assert 1 <= task.priority <= 5
        assert 0 <= task.epic < len(EPICS)
        assert 0 <= task.percent <= 100
    for pred, succ in DEPENDENCIES:
        assert pred != succ
        assert 1 <= pred <= len(TASKS)
        assert 1 <= succ <= len(TASKS)


def test_dependencies_have_no_cycle_and_no_duplicates() -> None:
    assert len(set(DEPENDENCIES)) == len(DEPENDENCIES)
    remaining = set(range(1, len(TASKS) + 1))
    while remaining:
        ready = {
            task
            for task in remaining
            if not any(pred in remaining and succ == task for pred, succ in DEPENDENCIES)
        }
        assert ready, f"cycle among tasks {sorted(remaining)}"
        remaining -= ready


def test_every_required_skill_is_in_the_vocabulary_and_someone_can_do_it() -> None:
    levels = [member[3] for member in MEMBERS]
    for task in TASKS:
        for row in parse_skills(task.skills):
            assert row["skill"] in SKILLS
            if row["must"]:
                assert any(
                    member.get(str(row["skill"]), 0) >= int(row["level"]) - 1 for member in levels
                ), f"{task.title} has no eligible member for {row['skill']}"


def test_owners_meet_the_plan_eligibility_rule() -> None:
    levels = {name: skills for name, _, _, skills in MEMBERS}
    for task in TASKS:
        if task.owner is None:
            continue
        for row in parse_skills(task.skills):
            if row["must"]:
                assert levels[task.owner].get(str(row["skill"]), 0) >= int(row["level"]) - 1


def test_a_task_never_starts_before_its_predecessors_finish() -> None:
    for pred, succ in DEPENDENCIES:
        if TASKS[succ - 1].percent > 0:
            assert TASKS[pred - 1].percent == 100, f"T-{succ:03} started before T-{pred:03} ended"


def test_only_one_member_has_payments_four() -> None:
    assert sum(1 for member in MEMBERS if member[3].get("payments", 0) >= 4) == 1


def test_progress_curve_rises_and_ends_at_one() -> None:
    curve = _progress_curve(random.Random(7))
    assert len(curve) == SNAPSHOT_DAYS
    assert curve == sorted(curve)
    assert curve[-1] == 1.0


# --- against a throwaway Postgres database -------------------------------------------------


def _server_url() -> URL:
    return make_url(Settings().database_url)


@pytest.fixture
def migrated_db() -> Iterator[URL]:
    server = _server_url()
    probe = create_engine(server, connect_args={"connect_timeout": 3})
    try:
        with probe.connect():
            pass
    except OperationalError:
        pytest.skip(f"Postgres not reachable at {server.host}:{server.port}/{server.database}")
    finally:
        probe.dispose()

    name = f"orchestrai_test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(server, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = server.set(database=name)
    try:
        cfg = Config(str(API_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(API_DIR / "migrations"))
        cfg.set_main_option(
            "sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%")
        )
        cfg.attributes["configure_logger"] = False
        command.upgrade(cfg, "head")
        yield url
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def session(migrated_db: URL) -> Iterator[Session]:
    engine = create_engine(migrated_db)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _dump(session: Session) -> dict[str, list[dict[str, Any]]]:
    """Every row of every table, ordered by id, without the clock-driven columns."""
    dump = {}
    for table in Base.metadata.sorted_tables:
        columns = [c for c in table.columns if c.name not in VOLATILE_COLUMNS]
        rows = session.execute(select(*columns).order_by(table.c.id)).mappings().all()
        dump[table.name] = [dict(row) for row in rows]
    return dump


def test_seeding_twice_gives_identical_data(session: Session) -> None:
    seed_demo(session, seed=42, as_of=AS_OF)
    session.commit()
    first = _dump(session)

    seed_demo(session, seed=42, as_of=AS_OF)
    session.commit()

    assert _dump(session) == first


def test_seed_value_only_changes_the_daily_wobble(session: Session) -> None:
    seed_demo(session, seed=42, as_of=AS_OF)
    session.commit()
    first = _dump(session)

    seed_demo(session, seed=7, as_of=AS_OF)
    session.commit()
    second = _dump(session)

    assert first["snapshot"] != second["snapshot"]
    assert first["task"] == second["task"]
    assert first["snapshot"][-1]["ev"] == second["snapshot"][-1]["ev"]
    assert first["snapshot"][-1]["ac"] == second["snapshot"][-1]["ac"]


def test_seed_creates_the_expected_shape(session: Session) -> None:
    project = seed_demo(session, seed=42, as_of=AS_OF)
    session.commit()

    def count(model: type) -> int:
        return session.scalar(select(func.count()).select_from(model)) or 0

    assert project.start_date == date(2026, 10, 16)
    assert project.start_date < AS_OF < project.deadline
    assert count(Project) == 1
    assert count(Member) == 8
    assert count(Epic) == 5
    assert count(Task) == len(TASKS)
    assert count(Dependency) == len(DEPENDENCIES)
    assert count(Assignment) == sum(1 for t in TASKS if t.owner)
    assert count(Snapshot) == SNAPSHOT_DAYS

    snapshots = session.scalars(select(Snapshot).order_by(Snapshot.date)).all()
    assert snapshots[-1].date == AS_OF
    assert all(day.date.weekday() < 5 for day in snapshots)
    for values in ([s.pv for s in snapshots], [s.ev for s in snapshots], [s.ac for s in snapshots]):
        assert values == sorted(values)


def test_latest_snapshot_is_slightly_behind_plan_and_on_budget(session: Session) -> None:
    seed_demo(session, seed=42, as_of=AS_OF)
    session.commit()
    last = session.scalars(select(Snapshot).order_by(Snapshot.date.desc())).first()
    assert last is not None
    assert 0.90 <= last.ev / last.pv < 1.0
    assert 1.0 <= last.ev / last.ac <= 1.1


def test_seeding_on_a_weekend_uses_the_friday_before(session: Session) -> None:
    seed_demo(session, seed=42, as_of=date(2026, 11, 8))
    session.commit()
    last = session.scalars(select(Snapshot).order_by(Snapshot.date.desc())).first()
    assert last is not None
    assert last.date == AS_OF
