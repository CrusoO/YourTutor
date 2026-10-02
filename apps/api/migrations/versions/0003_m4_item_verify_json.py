"""Store item.verify as JSON and add options for MCQ.

Revision ID: 0003_m4
Revises: 0002_m3
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_verify_json"
down_revision: str | None = "0002_m3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if "items" not in sa.inspect(bind).get_table_names():
        return
    cols = {c["name"]: c for c in sa.inspect(bind).get_columns("items")}
    if "options" not in cols:
        op.add_column(
            "items",
            sa.Column("options", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )
    verify = cols.get("verify")
    if verify is None:
        op.add_column("items", sa.Column("verify", sa.JSON(), nullable=True))
        return
    dialect = bind.dialect.name
    col_type = verify["type"]
    type_name = type(col_type).__name__.lower()
    if "json" in type_name:
        return
    if dialect == "postgresql":
        op.execute(
            sa.text(
                "ALTER TABLE items ALTER COLUMN verify TYPE JSON USING "
                "CASE WHEN verify IS NULL THEN NULL ELSE to_json(verify::text) END"
            )
        )
    else:
        with op.batch_alter_table("items") as batch:
            batch.alter_column("verify", existing_type=sa.String(), type_=sa.JSON())


def downgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("items")}
    if "options" in cols:
        op.drop_column("items", "options")
    if "verify" in cols and bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER TABLE items ALTER COLUMN verify TYPE VARCHAR USING "
                "CASE WHEN verify IS NULL THEN NULL ELSE verify::text END"
            )
        )
