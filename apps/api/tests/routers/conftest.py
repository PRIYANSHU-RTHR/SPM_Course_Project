"""Shared fixture: app client wired to a throwaway Postgres database (skips if unreachable)."""

import uuid
from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db import get_session
from app.main import create_app
from app.models import Base, Epic, Project

Client = tuple[TestClient, sessionmaker[Session]]


@pytest.fixture
def client() -> Iterator[Client]:
    server = make_url(Settings().database_url)
    admin = create_engine(server, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 3})
    name = f"orchestrai_test_{uuid.uuid4().hex[:8]}"
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    except OperationalError:
        admin.dispose()
        pytest.skip("Postgres not reachable (start it with `make db-up`)")
    engine = create_engine(server.set(database=name))
    try:
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, expire_on_commit=False)

        def _session() -> Iterator[Session]:
            with factory() as s:
                yield s

        app = create_app(Settings(_env_file=None))  # type: ignore[call-arg]
        app.dependency_overrides[get_session] = _session
        yield TestClient(app), factory
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def make_project(s: Session) -> tuple[Project, Epic]:
    project = Project(
        name="Campus Food-Ordering App",
        start_date=date(2026, 11, 2),
        deadline=date(2026, 12, 18),
        budget=Decimal("500000.00"),
        hourly_rate=Decimal("800.00"),
    )
    epic = Epic(project=project, title="Ordering")
    s.add(project)
    return project, epic
