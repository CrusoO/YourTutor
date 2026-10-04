"""Study participants, checkpoint results, token participant_id.

Revision ID: 0005_m5
Revises: 0004_m45
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_m5"
down_revision: str | None = "0004_m45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "study_participants" not in tables:
        op.create_table(
            "study_participants",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "student_id",
                sa.Uuid(),
                sa.ForeignKey("students.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("site_id", sa.String(), nullable=False),
            sa.Column("pseudonymous_code", sa.String(), nullable=False, unique=True),
            sa.Column("group", sa.String(), nullable=False),
            sa.Column(
                "consent_id",
                sa.Uuid(),
                sa.ForeignKey("consents.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("assignment_method", sa.String(), nullable=False),
            sa.Column("assignment_seed", sa.String(), nullable=False),
            sa.Column("pretest_form", sa.String(), nullable=False),
            sa.Column("posttest_form", sa.String(), nullable=True),
        )
    if "checkpoint_results" not in tables:
        op.create_table(
            "checkpoint_results",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "student_id",
                sa.Uuid(),
                sa.ForeignKey("students.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "participant_id",
                sa.Uuid(),
                sa.ForeignKey("study_participants.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("checkpoint_id", sa.String(), nullable=False),
            sa.Column("form", sa.String(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("per_skill", sa.JSON(), nullable=False),
            sa.Column("occasion", sa.String(), nullable=False),
            sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "checkpoint_tokens" in tables:
        cols = {c["name"] for c in sa.inspect(bind).get_columns("checkpoint_tokens")}
        if "participant_id" not in cols:
            op.add_column(
                "checkpoint_tokens",
                sa.Column(
                    "participant_id",
                    sa.Uuid(),
                    sa.ForeignKey("study_participants.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "checkpoint_tokens" in tables:
        cols = {c["name"] for c in sa.inspect(bind).get_columns("checkpoint_tokens")}
        if "participant_id" in cols:
            op.drop_column("checkpoint_tokens", "participant_id")
    if "checkpoint_results" in tables:
        op.drop_table("checkpoint_results")
    if "study_participants" in tables:
        op.drop_table("study_participants")
