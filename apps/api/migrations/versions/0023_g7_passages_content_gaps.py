"""G7: passages and content_gaps tables (Study Mode Ask).

Revision ID: 0023_g7_passages_content_gaps
Revises: 0022_g6_site_class_curriculum
Create Date: 2026-10-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_g7_passages_content_gaps"
down_revision: str | None = "0022_g6_site_class_curriculum"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "passages" not in tables:
        op.create_table(
            "passages",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("curriculum_id", sa.String(), nullable=False),
            sa.Column("book_id", sa.String(), nullable=False),
            sa.Column("chapter_id", sa.String(), nullable=False),
            sa.Column("section_id", sa.String(), nullable=False),
            sa.Column("page", sa.Integer(), nullable=True),
            sa.Column("locale", sa.String(), nullable=False),
            sa.Column("text", sa.String(), nullable=False),
            sa.Column("skill_ids", sa.JSON(), nullable=False),
            sa.Column("embedding", sa.JSON(), nullable=False),
            sa.Column("source_type", sa.String(), nullable=False),
            sa.Column("licence_status", sa.String(), nullable=False),
            sa.Column("source_ref", sa.String(), nullable=True),
            sa.Column("reviewer", sa.String(), nullable=True),
            sa.Column("content_hash", sa.String(), nullable=False),
            sa.Column("edition_year", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
        )
        for column in ("curriculum_id", "book_id", "chapter_id", "section_id"):
            op.create_index(f"ix_passages_{column}", "passages", [column])
    if "content_gaps" not in tables:
        op.create_table(
            "content_gaps",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("context_key", sa.JSON(), nullable=False),
            sa.Column("question_hash", sa.String(), nullable=False),
            sa.Column("question_text", sa.String(), nullable=True),
            sa.Column("skill_id", sa.String(), nullable=True),
            sa.Column("tier", sa.String(), nullable=True),
            sa.Column("reason", sa.String(), nullable=False),
        )
        op.create_index("ix_content_gaps_question_hash", "content_gaps", ["question_hash"])


def downgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "content_gaps" in tables:
        op.drop_table("content_gaps")
    if "passages" in tables:
        op.drop_table("passages")
