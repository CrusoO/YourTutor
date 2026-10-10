"""G3: lessons, scenes and widgets tables (loaded from content/lessons).

Revision ID: 0019_g3_lessons_scenes_widgets
Revises: 0018_g2b_teacher_alerts
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_g3_lessons_scenes_widgets"
down_revision: str | None = "0018_g2b_teacher_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "lessons" not in tables:
        op.create_table(
            "lessons",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("skill_id", sa.String(), nullable=False),
            sa.Column("title", sa.JSON(), nullable=False),
            sa.Column("source_ref", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("beats", sa.JSON(), nullable=False),
        )
        op.create_index("ix_lessons_skill_id", "lessons", ["skill_id"], unique=True)
    if "scenes" not in tables:
        op.create_table(
            "scenes",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "lesson_id",
                sa.String(),
                sa.ForeignKey("lessons.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("skill_id", sa.String(), nullable=False),
            sa.Column("source_ref", sa.String(), nullable=False),
            sa.Column("body", sa.JSON(), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("duration_s", sa.Float(), nullable=False),
            sa.Column("kb_per_minute", sa.Float(), nullable=False),
        )
        op.create_index("ix_scenes_lesson_id", "scenes", ["lesson_id"])
        op.create_index("ix_scenes_skill_id", "scenes", ["skill_id"])
    if "widgets" not in tables:
        op.create_table(
            "widgets",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "lesson_id",
                sa.String(),
                sa.ForeignKey("lessons.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("body", sa.JSON(), nullable=False),
        )
        op.create_index("ix_widgets_lesson_id", "widgets", ["lesson_id"])


def downgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    for name in ("widgets", "scenes", "lessons"):
        if name in tables:
            op.drop_table(name)
