"""Mistake notebook entries (off by default, behind MISTAKE_NOTEBOOK_ENABLED).

Idempotent on SQLite and Postgres: upgrade creates the table only if absent; downgrade drops only
that table, only if present. No data migration. Ids and times only, no learner text.

Revision ID: 0038_mistake_notebook
Revises: 0037_consent_audit
Create Date: 2026-11-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_mistake_notebook"
down_revision: str | None = "0037_consent_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "notebook_entries"
INDEX = "ix_notebook_entries_student_id"


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if TABLE in _tables():
        return
    op.create_table(
        TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.Column("misconception_id", sa.String(), nullable=True),
        sa.Column("stage", sa.SmallInteger(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("anchor_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("student_id", "item_id", name="uq_notebook_student_item"),
    )
    op.create_index(INDEX, TABLE, ["student_id"])


def downgrade() -> None:
    if TABLE in _tables():
        op.drop_table(TABLE)
