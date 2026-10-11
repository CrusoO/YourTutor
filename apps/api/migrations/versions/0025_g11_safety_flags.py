"""G11: safety_flags (distress signals that pause tutoring).

Revision ID: 0025_g11_safety_flags
Revises: 0024_g10_report_log
Create Date: 2026-10-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_g11_safety_flags"
down_revision: str | None = "0024_g10_report_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "safety_flags" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "safety_flags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_safety_flags_student_id", "safety_flags", ["student_id"])


def downgrade() -> None:
    if "safety_flags" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("safety_flags")
