"""M4: Loop B records and snapshots (shadow traits, versioned post-session snapshots).

Revision ID: 0027_m4_loop_b
Revises: 0026_vj_video_jobs
Create Date: 2026-11-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_m4_loop_b"
down_revision: str | None = "0026_vj_video_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "loop_b_records" not in existing:
        op.create_table(
            "loop_b_records",
            sa.Column(
                "student_id",
                sa.Uuid(),
                sa.ForeignKey("students.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("data", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "loop_b_snapshots" not in existing:
        op.create_table(
            "loop_b_snapshots",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "student_id",
                sa.Uuid(),
                sa.ForeignKey("students.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("session_id", sa.String(), nullable=False),
            sa.Column("watermark", sa.Integer(), nullable=False),
            sa.Column("record_version", sa.Integer(), nullable=False),
            sa.Column("versions", sa.JSON(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("student_id", "record_version", name="uq_loop_b_snapshot"),
        )
        op.create_index("ix_loop_b_snapshots_student_id", "loop_b_snapshots", ["student_id"])


def downgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "loop_b_snapshots" in existing:
        op.drop_table("loop_b_snapshots")
    if "loop_b_records" in existing:
        op.drop_table("loop_b_records")
