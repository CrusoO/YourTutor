"""Item verification tier and provenance (question-bank rights, week 1).

Revision ID: 0032_item_tier_provenance
Revises: 0031_content_reviews
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_item_tier_provenance"
down_revision: str | None = "0031_content_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("items")}


def upgrade() -> None:
    have = _columns()
    if "tier" not in have:
        op.add_column("items", sa.Column("tier", sa.String(1), nullable=True))
    if "provenance" not in have:
        op.add_column("items", sa.Column("provenance", sa.JSON(), nullable=True))


def downgrade() -> None:
    have = _columns()
    if "provenance" in have:
        op.drop_column("items", "provenance")
    if "tier" in have:
        op.drop_column("items", "tier")
