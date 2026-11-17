"""Sealed method and error counts per learner and skill (off by default, flag and consent gated).

Idempotent on SQLite and Postgres: upgrade creates the table only if absent; downgrade drops only
that table, only if present. No data migration.

Revision ID: 0036_learner_method_counts
Revises: 0035_factory_verification
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_learner_method_counts"
down_revision: str | None = "0035_factory_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "learner_method_counts"
INDEX = "ix_learner_method_counts_updated_week"


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if TABLE in _tables():
        return
    op.create_table(
        TABLE,
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("skill_id", sa.String(), primary_key=True),
        sa.Column("key_id", sa.SmallInteger(), nullable=False),
        sa.Column("payload", sa.LargeBinary(), nullable=False),
        sa.Column("schema_v", sa.SmallInteger(), nullable=False),
        sa.Column("updated_week", sa.Integer(), nullable=False),
    )
    op.create_index(INDEX, TABLE, ["updated_week"])


def downgrade() -> None:
    if TABLE in _tables():
        op.drop_table(TABLE)
