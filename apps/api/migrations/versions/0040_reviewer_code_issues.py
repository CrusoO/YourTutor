"""Audit rows for admin-issued reviewer sign-in codes (behind REVIEWER_DESK_ENABLED).

Idempotent on SQLite and Postgres: upgrade creates the table only if absent; downgrade drops only
that table, only if present. Ids and times only: the code itself is never stored here.

Revision ID: 0040_reviewer_code_issues
Revises: 0039_reviewer_desk
Create Date: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0040_reviewer_code_issues"
down_revision: str | None = "0039_reviewer_desk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "reviewer_code_issues"
INDEX = "ix_reviewer_code_issues_reviewer_id"


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if TABLE in _tables():
        return
    op.create_table(
        TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("issued_by", sa.Uuid(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(INDEX, TABLE, ["reviewer_id"])


def downgrade() -> None:
    if TABLE in _tables():
        op.drop_table(TABLE)
