"""G4: llm_calls (gateway call log, no student text; reply kept only when sampled for review).

Revision ID: 0020_g4_llm_calls
Revises: 0019_g3_lessons_scenes_widgets
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_g4_llm_calls"
down_revision: str | None = "0019_g3_lessons_scenes_widgets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "llm_calls" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("band_id", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("skip_reason", sa.String(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("failure_codes", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("sampled", sa.Boolean(), nullable=False),
        sa.Column("output_text", sa.String(), nullable=True),
        sa.Column("review_status", sa.String(), nullable=True),
    )
    op.create_index("ix_llm_calls_session_id", "llm_calls", ["session_id"])
    op.create_index("ix_llm_calls_purpose", "llm_calls", ["purpose"])
    op.create_index("ix_llm_calls_sampled", "llm_calls", ["sampled"])


def downgrade() -> None:
    if "llm_calls" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("llm_calls")
