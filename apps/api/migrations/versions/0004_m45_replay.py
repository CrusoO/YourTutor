"""Event replay columns and item content_hash.

Revision ID: 0004_m45
Revises: 0003_verify_json
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_m45"
down_revision: str | None = "0003_verify_json"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "events" in tables:
        cols = {c["name"] for c in sa.inspect(bind).get_columns("events")}
        if "state_before" not in cols:
            op.add_column("events", sa.Column("state_before", sa.String(), nullable=True))
        if "state_after" not in cols:
            op.add_column("events", sa.Column("state_after", sa.String(), nullable=True))
        if "rule_id" not in cols:
            op.add_column("events", sa.Column("rule_id", sa.String(), nullable=True))
    if "items" in tables:
        cols = {c["name"] for c in sa.inspect(bind).get_columns("items")}
        if "content_hash" not in cols:
            op.add_column("items", sa.Column("content_hash", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "events" in tables:
        op.drop_column("events", "rule_id")
        op.drop_column("events", "state_after")
        op.drop_column("events", "state_before")
    if "items" in tables:
        op.drop_column("items", "content_hash")
