"""Migration 0035 is idempotent and agrees with the model."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

PATH = (
    Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0035_factory_verification.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("m0035", PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _engine() -> sa.engine.Engine:
    engine = sa.create_engine("sqlite://")
    meta = sa.MetaData()
    sa.Table(
        "items", meta, sa.Column("id", sa.String, primary_key=True), sa.Column("tier", sa.String)
    )
    meta.create_all(engine)
    return engine


def _run(engine: sa.engine.Engine, step: str) -> None:
    module = _load()
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            getattr(module, step)()


def _columns(engine: sa.engine.Engine) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns("items")}


def test_upgrade_and_downgrade_are_idempotent() -> None:
    engine = _engine()
    new = {"verification", "certificate_hash", "suspended_at", "suspension_reason"}
    _run(engine, "upgrade")
    _run(engine, "upgrade")
    assert new <= _columns(engine) and {"id", "tier"} <= _columns(engine)
    _run(engine, "downgrade")
    _run(engine, "downgrade")
    assert not new & _columns(engine) and {"id", "tier"} <= _columns(engine)


def test_revision_chain_and_model_agree() -> None:
    module = _load()
    assert module.down_revision == "0034_role_agreements"
    from app.db.models import ItemRow

    engine = _engine()
    _run(engine, "upgrade")
    model_cols = {c.key for c in ItemRow.__table__.columns}
    assert {"verification", "certificate_hash", "suspended_at", "suspension_reason"} <= model_cols
    assert {"verification", "certificate_hash", "suspended_at", "suspension_reason"} <= _columns(
        engine
    )
