"""A database that does not answer must fail fast; once it hung every test that starts the app."""

from __future__ import annotations

from app.db.session import CONNECT_TIMEOUT_SECONDS, engine_options


def test_a_server_database_gets_a_connect_timeout() -> None:
    options = engine_options("postgresql+psycopg://u:p@127.0.0.1:5432/yourtutor")
    assert options["connect_args"] == {"connect_timeout": CONNECT_TIMEOUT_SECONDS}
    assert 0 < CONNECT_TIMEOUT_SECONDS <= 10


def test_sqlite_takes_no_pool_or_timeout_settings() -> None:
    options = engine_options("sqlite://")
    assert "connect_args" not in options and "pool_size" not in options
