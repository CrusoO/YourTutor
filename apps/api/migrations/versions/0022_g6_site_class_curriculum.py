"""G6: classes.board -> curriculum_id; users.site_id and students.site_id (school mode).

Revision ID: 0022_g6_site_class_curriculum
Revises: 0021_g5_student_onboarding
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_g6_site_class_curriculum"
down_revision: str | None = "0021_g5_student_onboarding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    cols = _columns("classes")
    if "board" in cols and "curriculum_id" not in cols:
        op.alter_column("classes", "board", new_column_name="curriculum_id")
    for table in ("users", "students"):
        if "site_id" not in _columns(table):
            op.add_column(table, sa.Column("site_id", sa.String(), nullable=True))
            op.create_index(f"ix_{table}_site_id", table, ["site_id"])


def downgrade() -> None:
    for table in ("users", "students"):
        if "site_id" in _columns(table):
            op.drop_index(f"ix_{table}_site_id", table_name=table)
            op.drop_column(table, "site_id")
    cols = _columns("classes")
    if "curriculum_id" in cols and "board" not in cols:
        op.alter_column("classes", "curriculum_id", new_column_name="board")
