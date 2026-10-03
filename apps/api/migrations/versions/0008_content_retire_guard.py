"""misconception_hits with RESTRICT FK to items (learner data guard).

Revision ID: 0008_retire
Revises: 0007_m7a
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_retire"
down_revision: str | None = "0007_m7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if "misconception_hits" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "misconception_hits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "misconception_id",
            sa.String(),
            sa.ForeignKey("misconceptions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.String(),
            sa.ForeignKey("items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_misconception_hits_student_id", "misconception_hits", ["student_id"])
    op.create_index("ix_misconception_hits_item_id", "misconception_hits", ["item_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if "misconception_hits" not in sa.inspect(bind).get_table_names():
        return
    op.drop_index("ix_misconception_hits_item_id", table_name="misconception_hits")
    op.drop_index("ix_misconception_hits_student_id", table_name="misconception_hits")
    op.drop_table("misconception_hits")
