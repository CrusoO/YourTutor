"""G1 item role (recall, explain, procedure, apply, transfer).

Revision ID: 0013_g1_item_role
Revises: 0012_g0_locale_columns
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_g1_item_role"
down_revision: str | None = "0012_g0_locale_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("items")}
    if "role" not in cols:
        op.add_column(
            "items",
            sa.Column("role", sa.String(), nullable=False, server_default="procedure"),
        )
    # Seed backfill until the next content load: existing word problems are `apply` items.
    bind.execute(
        sa.text(
            "UPDATE items SET role = 'apply' WHERE primary_skill = 'MATH.ALG.LIN1.WORD_PROBLEMS'"
        )
    )


def downgrade() -> None:
    op.drop_column("items", "role")
