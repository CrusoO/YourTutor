"""G1: overlays.board becomes overlays.curriculum_id.

Revision ID: 0015_g1_overlay_curriculum
Revises: 0014_g1_ladder
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_g1_overlay_curriculum"
down_revision: str | None = "0014_g1_ladder"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("overlays")}
    if "board" in cols and "curriculum_id" not in cols:
        op.alter_column("overlays", "board", new_column_name="curriculum_id")


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("overlays")}
    if "curriculum_id" in cols and "board" not in cols:
        op.alter_column("overlays", "curriculum_id", new_column_name="board")
