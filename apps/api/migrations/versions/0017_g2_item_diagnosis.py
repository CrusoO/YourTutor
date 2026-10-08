"""G2: item fields for diagnosis and the stuck-point picker.

Revision ID: 0017_g2_item_diagnosis
Revises: 0016_s1b_chapter_titles
Create Date: 2026-10-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_g2_item_diagnosis"
down_revision: str | None = "0016_s1b_chapter_titles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON_LISTS = ("slip_patterns", "prereq_signatures", "intermediate_values", "step_hints")


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("items")}
    for name in _JSON_LISTS:
        if name not in cols:
            op.add_column("items", sa.Column(name, sa.JSON(), nullable=False, server_default="[]"))
    if "min_plausible_ms" not in cols:
        op.add_column("items", sa.Column("min_plausible_ms", sa.Integer(), nullable=True))
    if "hint_restate" not in cols:
        op.add_column("items", sa.Column("hint_restate", sa.JSON(), nullable=True))


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("items")}
    for name in ("hint_restate", "min_plausible_ms", *_JSON_LISTS):
        if name in cols:
            op.drop_column("items", name)
