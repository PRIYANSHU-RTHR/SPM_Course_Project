"""Postgres helpers for tests: reachability check, throwaway databases, Alembic config.

Tests never touch the database named in DATABASE_URL; they create `orchestrai_test_<hex>`
databases on the same server and drop them afterwards.
"""

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic.config import Config
from sqlalchemy import URL, create_engine, make_url, text
from sqlalchemy.exc import OperationalError

from app.config import Settings

API_DIR = Path(__file__).resolve().parents[1]


def server_url() -> URL:
    return make_url(Settings().database_url)


def skip_reason() -> str | None:
    """None if Postgres accepts our credentials, else a human-readable reason to skip.

    With `REQUIRE_POSTGRES=1` (set in CI) an unreachable server is an error instead, so a
    broken service container can't turn the database tests into silent skips.
    """
    url = server_url()
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    try:
        with engine.connect():
            return None
    except OperationalError as exc:
        reason = (
            f"Postgres not reachable at {url.host}:{url.port}/{url.database} "
            "(start it with `make db-up` and point DATABASE_URL at it)"
        )
        if os.environ.get("REQUIRE_POSTGRES") == "1":
            raise RuntimeError(f"{reason}; REQUIRE_POSTGRES=1, so this is an error") from exc
        return reason
    finally:
        engine.dispose()


@contextmanager
def temp_database() -> Iterator[URL]:
    server = server_url()
    name = f"orchestrai_test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(server, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield server.set(database=name)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def alembic_config(url: URL) -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    # ConfigParser interpolation: escape '%' in the URL.
    cfg.set_main_option(
        "sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%")
    )
    cfg.attributes["configure_logger"] = False
    return cfg
