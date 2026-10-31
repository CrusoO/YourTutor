"""VJ: video_jobs — async engine video job queue.

Revision ID: 0026_vj_video_jobs
Revises: 0025_g11_safety_flags
Create Date: 2026-10-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_vj_video_jobs"
down_revision: str | None = "0025_g11_safety_flags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "video_jobs" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "video_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "org_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("events", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("result_path", sa.String(), nullable=True),
        sa.Column("lesson_mp4_sha256", sa.String(), nullable=True),
        sa.Column("sources_json_path", sa.String(), nullable=True),
        sa.Column("qa_json_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("idempotency_key", name="uq_video_jobs_idempotency_key"),
    )
    op.create_index("ix_video_jobs_student_id", "video_jobs", ["student_id"])
    op.create_index("ix_video_jobs_status", "video_jobs", ["status"])


def downgrade() -> None:
    if "video_jobs" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("video_jobs")
