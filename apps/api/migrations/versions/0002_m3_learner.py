"""Item verify column, mastery, and review_cards.

Revision ID: 0002_m3
Revises: 0001_m2
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_m3"
down_revision: str | None = "0001_m2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = sa.inspect(bind).get_table_names()
    item_cols = {c["name"] for c in sa.inspect(bind).get_columns("items")}
    if "verify" not in item_cols:
        op.add_column("items", sa.Column("verify", sa.String(), nullable=True))
    if "mastery" in existing_tables:
        return
    op.create_table(
        "mastery",
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("skill_id", sa.String(), primary_key=True),
        sa.Column("p_known", sa.Float(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unhinted_correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hinted_correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "review_cards",
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("skill_id", sa.String(), primary_key=True),
        sa.Column("fsrs_state", sa.JSON(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("review_cards")
    op.drop_table("mastery")
    op.drop_column("items", "verify")
