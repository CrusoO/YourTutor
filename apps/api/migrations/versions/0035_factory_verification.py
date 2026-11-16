"""Factory verification record, certificate hash and suspension on items.

Idempotent on SQLite and Postgres: every step first checks whether it is already done.

Revision ID: 0035_factory_verification
Revises: 0034_role_agreements
Create Date: 2026-11-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_factory_verification"
down_revision: str | None = "0034_role_agreements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("verification", sa.JSON()),
    ("certificate_hash", sa.String()),
    ("suspended_at", sa.DateTime(timezone=True)),
    ("suspension_reason", sa.String()),
)


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("items")}


def upgrade() -> None:
    have = _columns()
    for name, kind in _COLUMNS:
        if name not in have:
            op.add_column("items", sa.Column(name, kind, nullable=True))


def downgrade() -> None:
    have = _columns()
    for name, _ in reversed(_COLUMNS):
        if name in have:
            op.drop_column("items", name)
