"""Role agreements, phone sign-in, the age answer, child usernames and guardian approvals.

Idempotent on SQLite and Postgres: every step first checks whether it is already done.

Revision ID: 0034_role_agreements
Revises: 0033_class_join_codes
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0034_role_agreements"
down_revision: str | None = "0033_class_join_codes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {str(i["name"]) for i in sa.inspect(op.get_bind()).get_indexes(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _uuid() -> sa.types.TypeEngine:
    return sa.Uuid()


def upgrade() -> None:
    if "phone" not in _columns("users"):
        op.add_column("users", sa.Column("phone", sa.String(), nullable=True))
    if "ix_users_phone" not in _indexes("users"):
        op.create_index("ix_users_phone", "users", ["phone"], unique=True)

    students = _columns("students")
    if "is_adult" not in students:
        op.add_column("students", sa.Column("is_adult", sa.Boolean(), nullable=True))
    if "birth_year" not in students:
        op.add_column("students", sa.Column("birth_year", sa.Integer(), nullable=True))
    if "username" not in students:
        op.add_column("students", sa.Column("username", sa.String(), nullable=True))
    if "ix_students_username" not in _indexes("students"):
        op.create_index("ix_students_username", "students", ["username"], unique=True)

    tables = _tables()
    if "agreement_acceptances" not in tables:
        op.create_table(
            "agreement_acceptances",
            sa.Column("id", _uuid(), primary_key=True),
            sa.Column(
                "user_id", _uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("version", sa.String(), nullable=False),
            sa.Column("items", _text_array(), nullable=False),
            sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_agreement_acceptances_user_id", "agreement_acceptances", ["user_id"])
    if "guardian_approvals" not in tables:
        op.create_table(
            "guardian_approvals",
            sa.Column("id", _uuid(), primary_key=True),
            sa.Column(
                "student_id",
                _uuid(),
                sa.ForeignKey("students.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token_hash", sa.String(), nullable=False),
            sa.Column("nickname", sa.String(), nullable=False),
            sa.Column("contact", sa.String(), nullable=False),
            sa.Column("contact_kind", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_guardian_approvals_student_id", "guardian_approvals", ["student_id"], unique=True
        )
        op.create_index(
            "ix_guardian_approvals_token_hash", "guardian_approvals", ["token_hash"], unique=True
        )
        op.create_index("ix_guardian_approvals_expires_at", "guardian_approvals", ["expires_at"])


def _text_array() -> sa.types.TypeEngine:
    """text[] on Postgres, a JSON list on SQLite (as app.db.types.TextArray)."""
    return sa.JSON().with_variant(postgresql.ARRAY(sa.Text()), "postgresql")


def downgrade() -> None:
    tables = _tables()
    for name in ("guardian_approvals", "agreement_acceptances"):
        if name in tables:
            op.drop_table(name)
    if "ix_students_username" in _indexes("students"):
        op.drop_index("ix_students_username", table_name="students")
    students = _columns("students")
    for name in ("username", "birth_year", "is_adult"):
        if name in students:
            op.drop_column("students", name)
    if "ix_users_phone" in _indexes("users"):
        op.drop_index("ix_users_phone", table_name="users")
    if "phone" in _columns("users"):
        op.drop_column("users", "phone")
