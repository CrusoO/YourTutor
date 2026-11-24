"""Reviewer desk: append-only review decisions and a suspended flag on accounts.

content_reviews: drop the one-row-per-reviewer unique key (every decision is now its own row when
REVIEWER_DESK_ENABLED is on), add a plain lookup index, and add severity, reason_code, checks,
fix_notes and active_seconds (all nullable). users: add suspended_at (nullable).

Idempotent on SQLite and Postgres. Downgrade removes the new columns and index and puts the unique
key back; if a reviewer has more than one row on a hash, only their latest row is kept so the key
can be restored (the earlier rows are deleted: take a backup first).

Revision ID: 0039_reviewer_desk
Revises: 0038_mistake_notebook
Create Date: 2026-11-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039_reviewer_desk"
down_revision: str | None = "0038_mistake_notebook"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "content_reviews"
UNIQUE = "uq_content_review"
INDEX = "ix_content_reviews_lookup"
NEW_COLUMNS = (
    ("severity", sa.String(12)),
    ("reason_code", sa.String(2)),
    ("checks", sa.JSON()),
    ("fix_notes", sa.JSON()),
    ("active_seconds", sa.Integer()),
)


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _has_unique() -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(u["name"] == UNIQUE for u in inspector.get_unique_constraints(TABLE))


def _has_index() -> bool:
    return any(i["name"] == INDEX for i in sa.inspect(op.get_bind()).get_indexes(TABLE))


def upgrade() -> None:
    existing = _columns(TABLE)
    with op.batch_alter_table(TABLE) as batch:
        for name, kind in NEW_COLUMNS:
            if name not in existing:
                batch.add_column(sa.Column(name, kind, nullable=True))
        if _has_unique():
            batch.drop_constraint(UNIQUE, type_="unique")
    if not _has_index():
        op.create_index(INDEX, TABLE, ["item_id", "content_hash", "reviewer_id"])
    if "suspended_at" not in _columns("users"):
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    if "suspended_at" in _columns("users"):
        with op.batch_alter_table("users") as batch:
            batch.drop_column("suspended_at")
    if _has_index():
        op.drop_index(INDEX, table_name=TABLE)
    # keep only each reviewer's latest row per item and hash so the unique key can return
    op.execute(
        sa.text(
            "DELETE FROM content_reviews WHERE id NOT IN ("
            "SELECT id FROM ("
            "SELECT r.id AS id FROM content_reviews r WHERE NOT EXISTS ("
            "SELECT 1 FROM content_reviews n WHERE n.item_id = r.item_id "
            "AND n.content_hash = r.content_hash AND n.reviewer_id = r.reviewer_id "
            "AND (n.created_at > r.created_at OR (n.created_at = r.created_at AND n.id > r.id))"
            ")) AS latest)"
        )
    )
    existing = _columns(TABLE)
    with op.batch_alter_table(TABLE) as batch:
        for name, _ in NEW_COLUMNS:
            if name in existing:
                batch.drop_column(name)
        if not _has_unique():
            batch.create_unique_constraint(UNIQUE, ["item_id", "content_hash", "reviewer_id"])
