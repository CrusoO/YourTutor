"""Class join codes and pending class memberships.

Revision ID: 0033_class_join_codes
Revises: 0032_item_tier_provenance
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_class_join_codes"
down_revision: str | None = "0032_item_tier_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    classes = _columns("classes")
    if "join_code_hash" not in classes:
        op.add_column("classes", sa.Column("join_code_hash", sa.String(), nullable=True))
        op.create_index("ix_classes_join_code_hash", "classes", ["join_code_hash"], unique=True)
    if "join_code_expires_at" not in classes:
        op.add_column(
            "classes", sa.Column("join_code_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
    if "join_code_updated_at" not in classes:
        op.add_column(
            "classes", sa.Column("join_code_updated_at", sa.DateTime(timezone=True), nullable=True)
        )
    members = _columns("class_memberships")
    if "status" not in members:
        # Every existing membership was made by a teacher or an admin: it stays active.
        op.add_column(
            "class_memberships",
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
        )
    if "label" not in members:
        op.add_column("class_memberships", sa.Column("label", sa.String(), nullable=True))
    if "requested_at" not in members:
        op.add_column(
            "class_memberships",
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    members = _columns("class_memberships")
    for name in ("requested_at", "label", "status"):
        if name in members:
            op.drop_column("class_memberships", name)
    classes = _columns("classes")
    if "join_code_hash" in classes:
        op.drop_index("ix_classes_join_code_hash", table_name="classes")
        op.drop_column("classes", "join_code_hash")
    for name in ("join_code_updated_at", "join_code_expires_at"):
        if name in classes:
            op.drop_column("classes", name)
