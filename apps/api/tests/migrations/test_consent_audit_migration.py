"""Migration 0037 is idempotent, reversible, keeps old consent rows, and agrees with the models."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from tests.migrations.test_roundtrip import _config, _postgres_url, _tables

PATH = Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0037_consent_audit.py"
TABLE = "consent_events"
NEW_COLUMNS = {"text_manifest", "method", "verified_at"}


def _load():
    spec = importlib.util.spec_from_file_location("m0037", PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _engine() -> sa.engine.Engine:
    engine = sa.create_engine("sqlite://")
    meta = sa.MetaData()
    sa.Table(
        "consents",
        meta,
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("version", sa.String, nullable=False),
    )
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO consents (id, version) VALUES ('a', 'v1')"))
    return engine


def _run(engine: sa.engine.Engine, step: str) -> None:
    with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        getattr(_load(), step)()


def _cols(engine: sa.engine.Engine) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns("consents")}


def test_upgrade_downgrade_upgrade_on_sqlite_keeps_old_rows() -> None:
    engine = _engine()
    _run(engine, "upgrade")
    _run(engine, "upgrade")  # idempotent
    assert NEW_COLUMNS <= _cols(engine)
    assert TABLE in sa.inspect(engine).get_table_names()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version, method FROM consents")).one() == ("v1", None)
    _run(engine, "downgrade")
    _run(engine, "downgrade")
    assert not NEW_COLUMNS & _cols(engine)
    assert TABLE not in sa.inspect(engine).get_table_names()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version FROM consents")).scalar() == "v1"
    _run(engine, "upgrade")
    assert TABLE in sa.inspect(engine).get_table_names()


def test_chain_and_models_agree() -> None:
    from app.db.models import ConsentEventRow, ConsentRow

    assert _load().down_revision == "0036_learner_method_counts"
    engine = _engine()
    _run(engine, "upgrade")
    migrated = {c["name"] for c in sa.inspect(engine).get_columns(TABLE)}
    assert migrated == {c.key for c in ConsentEventRow.__table__.columns}
    assert NEW_COLUMNS <= {c.key for c in ConsentRow.__table__.columns}
    assert not sa.inspect(engine).get_foreign_keys(TABLE)  # must outlive the account


@pytest.mark.postgres
def test_upgrade_downgrade_upgrade_on_postgres() -> None:
    url = _postgres_url()
    if url is None:
        pytest.skip("Postgres is not available")
    engine = create_engine(url, future=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except OperationalError:
        pytest.skip("Postgres is not available")
    cfg = _config(url)
    command.upgrade(cfg, "head")
    assert TABLE in _tables(engine)
    command.downgrade(cfg, "0036_learner_method_counts")
    assert TABLE not in _tables(engine)
    assert not NEW_COLUMNS & {c["name"] for c in sa.inspect(engine).get_columns("consents")}
    command.upgrade(cfg, "head")
    assert TABLE in _tables(engine)
    engine.dispose()
