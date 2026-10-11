"""G10: report_log (weekly guardian reports already sent).

Revision ID: 0024_g10_report_log
Revises: 0023_g7_passages_content_gaps
Create Date: 2026-10-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_g10_report_log"
down_revision: str | None = "0023_g7_passages_content_gaps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "report_log" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "report_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("week_key", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("student_id", "week_key", "channel"),
    )
    op.create_index("ix_report_log_student_id", "report_log", ["student_id"])


def downgrade() -> None:
    if "report_log" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("report_log")
