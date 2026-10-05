"""G1 mastery ladder columns on `mastery`.

Revision ID: 0014_g1_ladder
Revises: 0013_g1_item_role
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_g1_ladder"
down_revision: str | None = "0013_g1_item_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON_DEFAULT = sa.text("'{}'")


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("mastery")}
    if "ladder_level" not in cols:
        op.add_column(
            "mastery",
            sa.Column("ladder_level", sa.Integer(), nullable=False, server_default="0"),
        )
    for name in ("ladder_evidence", "flags", "ladder_memory"):
        if name not in cols:
            op.add_column(
                "mastery",
                sa.Column(name, sa.JSON(), nullable=False, server_default=_JSON_DEFAULT),
            )


def downgrade() -> None:
    for name in ("ladder_memory", "flags", "ladder_evidence", "ladder_level"):
        op.drop_column("mastery", name)
