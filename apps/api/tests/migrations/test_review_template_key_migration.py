"""Migration 0041 is idempotent, reversible, and agrees with the model."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.db.models import ContentReviewRow

PATH = Path(__file__).resolve().parents[2] / "migrations" / "versions"
PATH = PATH / "0041_review_template_key.py"


def _load():
    spec = importlib.util.spec_from_file_location("m0041", PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(engine: sa.engine.Engine, step: str) -> None:
    with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        getattr(_load(), step)()


def _engine() -> sa.engine.Engine:
    """A database holding the table as it was before 0041: every model column but template_key."""
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    columns = [c.copy() for c in ContentReviewRow.__table__.columns if c.key != "template_key"]
    sa.Table("content_reviews", metadata, *columns)
    metadata.create_all(engine)
    return engine


def _names(engine: sa.engine.Engine) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns("content_reviews")}


def test_upgrade_downgrade_upgrade_on_sqlite() -> None:
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO content_reviews (id, item_id, content_hash, reviewer_id, "
                "reviewer_label, decision, created_at) VALUES "
                "('a','I','h','r','R','approve','2026-01-01')"
            )
        )
    _run(engine, "upgrade")
    _run(engine, "upgrade")  # idempotent
    assert _names(engine) == {c.key for c in ContentReviewRow.__table__.columns}
    with engine.begin() as conn:  # the old row survives with a NULL key
        assert conn.execute(sa.text("SELECT template_key FROM content_reviews")).scalar() is None
    _run(engine, "downgrade")
    _run(engine, "downgrade")
    assert "template_key" not in _names(engine)
    _run(engine, "upgrade")
    assert "template_key" in _names(engine)


def test_chain_is_linear() -> None:
    assert _load().down_revision == "0040_reviewer_code_issues"
