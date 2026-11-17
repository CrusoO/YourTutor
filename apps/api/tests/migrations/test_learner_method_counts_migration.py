"""Migration 0036 is idempotent, reversible, and agrees with the model."""

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

PATH = Path(__file__).resolve().parents[2] / "migrations" / "versions"
PATH = PATH / "0036_learner_method_counts.py"
TABLE = "learner_method_counts"


def _load():
    spec = importlib.util.spec_from_file_location("m0036", PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _engine() -> sa.engine.Engine:
    engine = sa.create_engine("sqlite://")
    meta = sa.MetaData()
    sa.Table("students", meta, sa.Column("id", sa.Uuid, primary_key=True))
    meta.create_all(engine)
    return engine


def _run(engine: sa.engine.Engine, step: str) -> None:
    with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        getattr(_load(), step)()


def _names(engine: sa.engine.Engine) -> set[str]:
    return set(sa.inspect(engine).get_table_names())


def test_upgrade_downgrade_upgrade_on_sqlite() -> None:
    engine = _engine()
    _run(engine, "upgrade")
    _run(engine, "upgrade")  # idempotent
    assert TABLE in _names(engine)
    _run(engine, "downgrade")
    _run(engine, "downgrade")
    assert TABLE not in _names(engine) and "students" in _names(engine)
    _run(engine, "upgrade")
    assert TABLE in _names(engine)


def test_chain_and_model_agree() -> None:
    from app.db.models import LearnerMethodCountRow

    assert _load().down_revision == "0035_factory_verification"
    engine = _engine()
    _run(engine, "upgrade")
    migrated = {c["name"] for c in sa.inspect(engine).get_columns(TABLE)}
    assert migrated == {c.key for c in LearnerMethodCountRow.__table__.columns}
    pk = sa.inspect(engine).get_pk_constraint(TABLE)["constrained_columns"]
    assert set(pk) == {"student_id", "skill_id"}


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
    command.downgrade(cfg, "0035_factory_verification")
    assert TABLE not in _tables(engine) and "students" in _tables(engine)
    command.upgrade(cfg, "head")
    assert TABLE in _tables(engine)
    engine.dispose()
