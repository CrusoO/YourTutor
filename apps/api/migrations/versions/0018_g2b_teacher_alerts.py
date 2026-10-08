"""G2b: teacher alerts for wheel-spinning (written only with the teacher_share scope).

Revision ID: 0018_g2b_teacher_alerts
Revises: 0017_g2_item_diagnosis
Create Date: 2026-10-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_g2b_teacher_alerts"
down_revision: str | None = "0017_g2_item_diagnosis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "teacher_alerts" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "teacher_alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_teacher_alerts_student_id", "teacher_alerts", ["student_id"])


def downgrade() -> None:
    if "teacher_alerts" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("teacher_alerts")
