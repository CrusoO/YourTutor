"""Staff decisions on content items (the review screen).

Revision ID: 0031_content_reviews
Revises: 0030_clear_video_prompts
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_content_reviews"
down_revision: str | None = "0030_clear_video_prompts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "content_reviews" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "content_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("item_id", sa.String(120), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_label", sa.String(120), nullable=False),
        sa.Column("decision", sa.String(10), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("item_id", "content_hash", "reviewer_id", name="uq_content_review"),
    )
    op.create_index("ix_content_reviews_item_id", "content_reviews", ["item_id"])


def downgrade() -> None:
    op.drop_table("content_reviews")
