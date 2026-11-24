"""Migration 0039 is idempotent, reversible, and agrees with the models."""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.db.models import ContentReviewRow, UserRow

PATH = Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0039_reviewer_desk.py"
NEW = {"severity", "reason_code", "checks", "fix_notes", "active_seconds"}


def _load():
    spec = importlib.util.spec_from_file_location("m0039", PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _old_engine() -> sa.engine.Engine:
    """content_reviews and users as they were at 0038, with the unique key."""
    engine = sa.create_engine("sqlite://")
    meta = sa.MetaData()
    sa.Table(
        "content_reviews",
        meta,
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("item_id", sa.String(120), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("reviewer_id", sa.Uuid, nullable=False),
        sa.Column("reviewer_label", sa.String(120), nullable=False),
        sa.Column("decision", sa.String(10), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("item_id", "content_hash", "reviewer_id", name="uq_content_review"),
    )
    sa.Table("users", meta, sa.Column("id", sa.Uuid, primary_key=True))
    meta.create_all(engine)
    return engine


def _run(engine: sa.engine.Engine, step: str) -> None:
    with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        getattr(_load(), step)()


def _cols(engine: sa.engine.Engine, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def _unique(engine: sa.engine.Engine) -> list[str]:
    inspector = sa.inspect(engine)
    return [str(u["name"]) for u in inspector.get_unique_constraints("content_reviews")]


def test_upgrade_downgrade_upgrade_on_sqlite() -> None:
    engine = _old_engine()
    _run(engine, "upgrade")
    _run(engine, "upgrade")  # idempotent
    assert NEW <= _cols(engine, "content_reviews") and "suspended_at" in _cols(engine, "users")
    assert _unique(engine) == []
    _run(engine, "downgrade")
    _run(engine, "downgrade")
    assert not NEW & _cols(engine, "content_reviews") and "suspended_at" not in _cols(
        engine, "users"
    )
    assert _unique(engine) == ["uq_content_review"]
    _run(engine, "upgrade")
    assert NEW <= _cols(engine, "content_reviews")


def test_downgrade_keeps_each_reviewers_latest_row_so_the_key_can_return() -> None:
    engine = _old_engine()
    _run(engine, "upgrade")
    who = uuid.uuid4()
    with engine.begin() as conn:
        for decision, minute in (("fix", 1), ("approve", 2)):
            conn.execute(
                sa.text(
                    "INSERT INTO content_reviews (id, item_id, content_hash, reviewer_id, "
                    "reviewer_label, decision, created_at) VALUES "
                    "(:id, 'I', 'h', :r, 'x', :d, :t)"
                ),
                {
                    "id": uuid.uuid4().hex,
                    "r": who.hex,
                    "d": decision,
                    "t": f"2026-11-24 10:0{minute}:00",
                },
            )
    _run(engine, "downgrade")
    with engine.connect() as conn:
        kept: list[str] = list(
            conn.execute(sa.text("SELECT decision FROM content_reviews")).scalars().all()
        )
    assert kept == ["approve"]


def test_chain_and_models_agree() -> None:
    assert _load().down_revision == "0038_mistake_notebook"
    engine = _old_engine()
    _run(engine, "upgrade")
    # template_key is added later, by migration 0041
    model = {c.key for c in ContentReviewRow.__table__.columns} - {"template_key"}
    assert _cols(engine, "content_reviews") == model
    assert "suspended_at" in {c.key for c in UserRow.__table__.columns}
