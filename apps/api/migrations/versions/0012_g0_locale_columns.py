"""G0 locales: name, script, status.

Revision ID: 0012_g0_locale_columns
Revises: 0011_g0_sections
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_g0_locale_columns"
down_revision: str | None = "0011_g0_sections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Seeded to match config/locales.yaml; later edits reach the table through the content loader.
_KNOWN = {
    "en": ("English", "Latn", "active"),
    "ne": ("Nepali", "Deva", "draft"),
    "as": ("Assamese", "Beng", "draft"),
}


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("locales")}
    for name in ("name", "script", "status"):
        if name not in cols:
            op.add_column("locales", sa.Column(name, sa.String(), nullable=True))
    for code, (name, script, status) in _KNOWN.items():
        bind.execute(
            sa.text("UPDATE locales SET name = :n, script = :s, status = :t WHERE code = :c"),
            {"n": name, "s": script, "t": status, "c": code},
        )
    bind.execute(sa.text("UPDATE locales SET name = code WHERE name IS NULL"))
    bind.execute(sa.text("UPDATE locales SET script = '' WHERE script IS NULL"))
    bind.execute(sa.text("UPDATE locales SET status = 'draft' WHERE status IS NULL"))
    for name in ("name", "script", "status"):
        op.alter_column("locales", name, nullable=False)


def downgrade() -> None:
    op.drop_column("locales", "status")
    op.drop_column("locales", "script")
    op.drop_column("locales", "name")
