"""Router tests run against a dedicated, migrated test database.

One `orchestrai_test_<hex>` database per test session (Alembic `upgrade head`), every table
truncated after each test, dropped at the end. Skipped when Postgres is not reachable.
"""

from collections.abc import Iterator

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db import get_session
from app.main import create_app
from app.models import Base
from tests import pg
from tests.routers.helpers import Client


@pytest.fixture(scope="session")
def api_engine() -> Iterator[Engine]:
    reason = pg.skip_reason()
    if reason:
        pytest.skip(reason)
    with pg.temp_database() as url:
        command.upgrade(pg.alembic_config(url), "head")
        engine = create_engine(url)
        yield engine
        engine.dispose()


@pytest.fixture
def session_factory(api_engine: Engine) -> Iterator[sessionmaker[Session]]:
    yield sessionmaker(bind=api_engine, autoflush=False, expire_on_commit=False)
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with api_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> TestClient:
    app = create_app(Settings(_env_file=None))  # type: ignore[call-arg]

    def override() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    return TestClient(app)


@pytest.fixture
def api(client: TestClient, session_factory: sessionmaker[Session]) -> Client:
    """(client, session factory) pair used by the engine endpoint tests (Steps 06-11)."""
    return client, session_factory


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Direct DB access for arranging rows that have no endpoint yet (e.g. assignments)."""
    with session_factory() as session:
        yield session
