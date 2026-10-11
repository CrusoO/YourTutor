"""G5: students.onboarding (first-run and warm-up offer answers).

Revision ID: 0021_g5_student_onboarding
Revises: 0020_g4_llm_calls
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_g5_student_onboarding"
down_revision: str | None = "0020_g4_llm_calls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("students")}
    if "onboarding" not in columns:
        op.add_column("students", sa.Column("onboarding", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("students")}
    if "onboarding" in columns:
        op.drop_column("students", "onboarding")
