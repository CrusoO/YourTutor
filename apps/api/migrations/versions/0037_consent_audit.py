"""Consent audit: what wording was shown (text_manifest, method, verified_at) and consent_events.

Idempotent on SQLite and Postgres: each column and the table are added only if absent; downgrade
removes only what this revision added, only if present. No data migration. consent_events has no
foreign key to students or users on purpose: the trail outlives the account.

Revision ID: 0037_consent_audit
Revises: 0036_learner_method_counts
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037_consent_audit"
down_revision: str | None = "0036_learner_method_counts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "consent_events"
INDEX = "ix_consent_events_student_id"
COLUMNS = ("text_manifest", "method", "verified_at")


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _consent_columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("consents")}


def upgrade() -> None:
    have = _consent_columns()
    with op.batch_alter_table("consents") as batch:
        if "text_manifest" not in have:
            batch.add_column(sa.Column("text_manifest", sa.JSON(), nullable=True))
        if "method" not in have:
            batch.add_column(sa.Column("method", sa.String(), nullable=True))
        if "verified_at" not in have:
            batch.add_column(sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    if TABLE in _tables():
        return
    op.create_table(
        TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=True),
        sa.Column("guardian_user_id", sa.Uuid(), nullable=True),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("text_sha256", sa.String(), nullable=True),
        sa.Column("method", sa.String(), nullable=True),
        sa.Column("actor_kind", sa.String(), nullable=False),
        sa.Column("prev_hash", sa.String(), nullable=False),
        sa.Column("row_hash", sa.String(), nullable=False),
    )
    op.create_index(INDEX, TABLE, ["student_id"])


def downgrade() -> None:
    if TABLE in _tables():
        op.drop_table(TABLE)
    have = _consent_columns()
    present = [c for c in COLUMNS if c in have]
    if present:
        with op.batch_alter_table("consents") as batch:
            for name in present:
                batch.drop_column(name)
