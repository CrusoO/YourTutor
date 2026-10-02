"""Content tables plus accounts, consent, and sessions.

Revision ID: 0001_m2
Revises:
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_m2"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "skills",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.JSON(), nullable=False),
        sa.Column("grade_band", sa.JSON(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("prerequisites", sa.JSON(), nullable=False),
        sa.Column("related", sa.JSON(), nullable=False),
        sa.Column("misconceptions", sa.JSON(), nullable=False),
        sa.Column("bkt", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
    )
    op.create_table(
        "items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("skill_ids", sa.JSON(), nullable=False),
        sa.Column("primary_skill", sa.String(), nullable=False),
        sa.Column("difficulty", sa.Float(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("pool", sa.String(), nullable=False),
        sa.Column("stem", sa.JSON(), nullable=False),
        sa.Column("answer", sa.JSON(), nullable=False),
        sa.Column("solution_steps", sa.JSON(), nullable=False),
        sa.Column("hints", sa.JSON(), nullable=False),
        sa.Column("prediction_prompt", sa.JSON(), nullable=False),
        sa.Column("misconception_rules", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reviewed_by", sa.String(), nullable=True),
    )
    op.create_index("ix_items_primary_skill", "items", ["primary_skill"])
    op.create_index("ix_items_pool", "items", ["pool"])
    op.create_index("ix_items_status", "items", ["status"])
    op.create_table(
        "misconceptions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("remedial_skill", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
    )
    op.create_table(
        "overlays",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("board", sa.String(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("chapter", sa.String(), nullable=False),
        sa.Column("skill_ids", sa.JSON(), nullable=False),
        sa.Column("live", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "glossary_terms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("term", sa.String(), nullable=False),
        sa.Column("translation", sa.String(), nullable=False),
    )
    op.create_table(
        "checkpoint_forms",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("checkpoint_id", sa.String(), nullable=False),
        sa.Column("form_a", sa.JSON(), nullable=False),
        sa.Column("form_b", sa.JSON(), nullable=False),
        sa.Column("match_map", sa.JSON(), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("locale", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "students",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("board", sa.String(), nullable=False),
        sa.Column("home_language", sa.String(), nullable=False),
        sa.Column("exam_language", sa.String(), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("current_chapter_id", sa.String(), nullable=True),
        sa.Column("pin_hash", sa.String(), nullable=True),
        sa.Column("pin_failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pin_locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "consents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("students.id", ondelete="CASCADE")),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "classes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("teacher_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("board", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "class_memberships",
        sa.Column(
            "class_id",
            sa.Uuid(),
            sa.ForeignKey("classes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "otp_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("ip", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_otp_challenges_email", "otp_challenges", ["email"])
    op.create_table(
        "rate_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("bucket", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rate_events_bucket", "rate_events", ["bucket"])
    op.create_index("ix_rate_events_created_at", "rate_events", ["created_at"])
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("checkpoint_id", sa.String(), nullable=True),
        sa.Column("checkpoint_form", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("students.id", ondelete="CASCADE")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_reason", sa.String(), nullable=True),
        sa.Column("resumable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("active_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("llm_called", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("client_event_id", sa.Uuid(), unique=True, nullable=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE")),
        sa.Column("item_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("hint_level", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "checkpoint_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("checkpoint_id", sa.String(), nullable=False),
        sa.Column("form", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column(
            "consent_id",
            sa.Uuid(),
            sa.ForeignKey("consents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "review_queue",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("students.id", ondelete="CASCADE")),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "review_queue",
        "checkpoint_tokens",
        "events",
        "sessions",
        "auth_sessions",
        "rate_events",
        "otp_challenges",
        "class_memberships",
        "classes",
        "consents",
        "students",
        "users",
        "checkpoint_forms",
        "glossary_terms",
        "overlays",
        "misconceptions",
        "items",
        "skills",
    ):
        op.drop_table(table)
