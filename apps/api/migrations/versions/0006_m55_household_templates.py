"""Household id, token occasion/used_at, paper entries, item template fields.

Revision ID: 0006_m55
Revises: 0005_m5
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_m55"
down_revision: str | None = "0005_m5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if table not in tables:
        return
    cols = {c["name"] for c in sa.inspect(bind).get_columns(table)}
    if column.name not in cols:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing(
        "study_participants", sa.Column("household_id", sa.String(), nullable=True)
    )
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "study_participants" in tables:
        cols = {c["name"] for c in sa.inspect(bind).get_columns("study_participants")}
        if "household_id" in cols:
            existing = {i["name"] for i in sa.inspect(bind).get_indexes("study_participants")}
            if "ix_study_participants_household_id" not in existing:
                op.create_index(
                    "ix_study_participants_household_id", "study_participants", ["household_id"]
                )

    _add_column_if_missing("checkpoint_tokens", sa.Column("occasion", sa.String(), nullable=True))
    _add_column_if_missing(
        "checkpoint_tokens", sa.Column("used_at", sa.DateTime(timezone=True), nullable=True)
    )

    _add_column_if_missing("items", sa.Column("template_id", sa.String(), nullable=True))
    _add_column_if_missing("items", sa.Column("generator_version", sa.String(), nullable=True))
    _add_column_if_missing("items", sa.Column("template_hash", sa.String(), nullable=True))
    if "items" in tables:
        existing = {i["name"] for i in sa.inspect(bind).get_indexes("items")}
        if "ix_items_template_id" not in existing:
            cols = {c["name"] for c in sa.inspect(bind).get_columns("items")}
            if "template_id" in cols:
                op.create_index("ix_items_template_id", "items", ["template_id"])

    if "paper_entries" not in tables:
        op.create_table(
            "paper_entries",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "participant_id",
                sa.Uuid(),
                sa.ForeignKey("study_participants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("checkpoint_id", sa.String(), nullable=False),
            sa.Column("form", sa.String(), nullable=False),
            sa.Column("occasion", sa.String(), nullable=False),
            sa.Column("entry_pass", sa.Integer(), nullable=False),
            sa.Column("answers", sa.JSON(), nullable=False),
            sa.Column("mismatches", sa.JSON(), nullable=False),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "paper_entries" in tables:
        op.drop_table("paper_entries")
    if "items" in tables:
        indexes = {i["name"] for i in sa.inspect(bind).get_indexes("items")}
        if "ix_items_template_id" in indexes:
            op.drop_index("ix_items_template_id", table_name="items")
        cols = {c["name"] for c in sa.inspect(bind).get_columns("items")}
        for name in ("template_hash", "generator_version", "template_id"):
            if name in cols:
                op.drop_column("items", name)
    if "checkpoint_tokens" in tables:
        cols = {c["name"] for c in sa.inspect(bind).get_columns("checkpoint_tokens")}
        for name in ("used_at", "occasion"):
            if name in cols:
                op.drop_column("checkpoint_tokens", name)
    if "study_participants" in tables:
        indexes = {i["name"] for i in sa.inspect(bind).get_indexes("study_participants")}
        if "ix_study_participants_household_id" in indexes:
            op.drop_index("ix_study_participants_household_id", table_name="study_participants")
        cols = {c["name"] for c in sa.inspect(bind).get_columns("study_participants")}
        if "household_id" in cols:
            op.drop_column("study_participants", "household_id")
