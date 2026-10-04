"""G0 sections table and overlays.section_map.

Revision ID: 0011_g0_sections
Revises: 0010_g0_students
Create Date: 2026-10-04
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_g0_sections"
down_revision: str | None = "0010_g0_students"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Placeholder sections for the seed chapters (draft; replaced when the curriculum lead maps pages).
_CHAPTERS = ("bhutan_class9", "seba_class9", "sample_class9")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "sections" not in inspector.get_table_names():
        op.create_table(
            "sections",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("chapter_id", sa.String(), sa.ForeignKey("chapters.id"), nullable=False),
            sa.Column("order", sa.Integer(), nullable=False),
            sa.Column("titles", sa.JSON(), nullable=False),
            sa.Column("page_start", sa.Integer(), nullable=True),
            sa.Column("page_end", sa.Integer(), nullable=True),
        )
    overlay_cols = {c["name"] for c in inspector.get_columns("overlays")}
    if "section_map" not in overlay_cols:
        op.add_column(
            "overlays",
            sa.Column("section_map", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )
    for chapter_id in _CHAPTERS:
        for order in (1, 2, 3):
            bind.execute(
                sa.text(
                    'INSERT INTO sections (id, chapter_id, "order", titles) '
                    "VALUES (:id, :ch, :o, :t) ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": f"{chapter_id}.s{order}",
                    "ch": chapter_id,
                    "o": order,
                    "t": json.dumps({"en": f"Section {order}"}),
                },
            )


def downgrade() -> None:
    op.drop_column("overlays", "section_map")
    op.drop_table("sections")
