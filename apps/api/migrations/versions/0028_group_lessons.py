"""Group lessons: a lesson shared by a link, and the anonymous results people choose to send back.

Revision ID: 0028_group_lessons
Revises: 0027_m4_loop_b
Create Date: 2026-11-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_group_lessons"
down_revision: str | None = "0027_m4_loop_b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "group_lessons" not in existing:
        op.create_table(
            "group_lessons",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "owner_id",
                sa.Uuid(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("code", sa.String(16), nullable=False),
            sa.Column("prompt", sa.String(300), nullable=False),
            sa.Column("language", sa.String(8), nullable=False),
            sa.Column("blocks", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_group_lessons_owner_id", "group_lessons", ["owner_id"])
        op.create_index("ix_group_lessons_code", "group_lessons", ["code"], unique=True)
    if "group_results" not in existing:
        op.create_table(
            "group_results",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "group_id",
                sa.Uuid(),
                sa.ForeignKey("group_lessons.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("participant", sa.String(64), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("items", sa.JSON(), nullable=False),
            sa.UniqueConstraint("group_id", "participant", name="uq_group_participant"),
        )
        op.create_index("ix_group_results_group_id", "group_results", ["group_id"])


def downgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "group_results" in existing:
        op.drop_table("group_results")
    if "group_lessons" in existing:
        op.drop_table("group_lessons")
