"""Family code, paper consent reference.

Revision ID: 0007_m7a
Revises: 0006_m55
Create Date: 2026-10-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_m7a"
down_revision: str | None = "0006_m55"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if table not in tables:
        return
    cols = {c["name"] for c in sa.inspect(bind).get_columns(table)}
    if column.name not in cols:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("students", sa.Column("family_code", sa.String(), nullable=True))
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "students" in tables:
        existing = {i["name"] for i in sa.inspect(bind).get_indexes("students")}
        if "ix_students_family_code" not in existing:
            cols = {c["name"] for c in sa.inspect(bind).get_columns("students")}
            if "family_code" in cols:
                op.create_index("ix_students_family_code", "students", ["family_code"])
    _add_column_if_missing("consents", sa.Column("paper_ref", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "consents" in tables:
        cols = {c["name"] for c in sa.inspect(bind).get_columns("consents")}
        if "paper_ref" in cols:
            op.drop_column("consents", "paper_ref")
    if "students" in tables:
        indexes = {i["name"] for i in sa.inspect(bind).get_indexes("students")}
        if "ix_students_family_code" in indexes:
            op.drop_index("ix_students_family_code", table_name="students")
        cols = {c["name"] for c in sa.inspect(bind).get_columns("students")}
        if "family_code" in cols:
            op.drop_column("students", "family_code")
