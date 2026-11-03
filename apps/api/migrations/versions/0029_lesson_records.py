"""The learning card a signed-in learner chose to keep.

Revision ID: 0029_lesson_records
Revises: 0028_group_lessons
Create Date: 2026-11-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_lesson_records"
down_revision: str | None = "0028_group_lessons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "lesson_records" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "lesson_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(80), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lesson_records_student_id", "lesson_records", ["student_id"])


def downgrade() -> None:
    op.drop_table("lesson_records")
