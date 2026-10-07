"""S1b: chapter titles and order for the chapter map.

Revision ID: 0016_s1b_chapter_titles
Revises: 0015_g1_overlay_curriculum
Create Date: 2026-10-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_s1b_chapter_titles"
down_revision: str | None = "0015_g1_overlay_curriculum"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("chapters")}
    if "titles" not in cols:
        op.add_column(
            "chapters", sa.Column("titles", sa.JSON(), nullable=False, server_default="{}")
        )
    if "position" not in cols:
        op.add_column(
            "chapters", sa.Column("position", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("chapters")}
    if "position" in cols:
        op.drop_column("chapters", "position")
    if "titles" in cols:
        op.drop_column("chapters", "titles")
