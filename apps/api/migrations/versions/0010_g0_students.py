"""G0 student curriculum context and locale FKs.

Revision ID: 0010_g0_students
Revises: 0009_g0_registry
Create Date: 2026-10-04
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_g0_students"
down_revision: str | None = "0009_g0_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    student_cols = {c["name"] for c in sa.inspect(bind).get_columns("students")}
    if "curriculum_id" not in student_cols:
        op.add_column("students", sa.Column("curriculum_id", sa.String(), nullable=True))
    if "book_id" not in student_cols:
        op.add_column("students", sa.Column("book_id", sa.String(), nullable=True))
    if "context_key" not in student_cols:
        op.add_column("students", sa.Column("context_key", sa.JSON(), nullable=True))

    conn = bind
    conn.execute(
        sa.text(
            "UPDATE students SET home_language = 'en' "
            "WHERE home_language NOT IN (SELECT code FROM locales)"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE students SET exam_language = 'en' "
            "WHERE exam_language NOT IN (SELECT code FROM locales)"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE users SET locale = 'en' WHERE locale NOT IN (SELECT code FROM locales)"
        )
    )
    rows = conn.execute(sa.text("SELECT id, board, grade, current_chapter_id, timezone FROM students")).all()
    for row in rows:
        board = row.board or "bhutan"
        curriculum_id = board if board in {"bhutan", "seba"} else board
        book_id = f"{board}_class9" if board in {"bhutan", "seba"} else "sample_class9"
        chapter_id = row.current_chapter_id or book_id
        context = {
            "curriculum_id": curriculum_id,
            "book_id": book_id,
            "chapter_id": chapter_id,
        }
        tz_row = conn.execute(
            sa.text("SELECT default_timezone FROM curricula WHERE id = :id"),
            {"id": curriculum_id},
        ).first()
        tz = row.timezone or (tz_row[0] if tz_row else "UTC")
        conn.execute(
            sa.text(
                "UPDATE students SET curriculum_id = :c, book_id = :b, context_key = :ctx, "
                "current_chapter_id = :ch, timezone = :tz WHERE id = :id"
            ),
            {
                "c": curriculum_id,
                "b": book_id,
                "ctx": json.dumps(context),
                "ch": chapter_id,
                "tz": tz,
                "id": str(row.id),
            },
        )

    op.alter_column("students", "curriculum_id", nullable=False)
    op.alter_column("students", "book_id", nullable=False)
    op.create_foreign_key("fk_students_curriculum", "students", "curricula", ["curriculum_id"], ["id"])
    op.create_foreign_key("fk_students_book", "students", "books", ["book_id"], ["id"])
    op.create_foreign_key(
        "fk_students_home_language", "students", "locales", ["home_language"], ["code"]
    )
    op.create_foreign_key(
        "fk_students_exam_language", "students", "locales", ["exam_language"], ["code"]
    )
    op.create_foreign_key("fk_users_locale", "users", "locales", ["locale"], ["code"])


def downgrade() -> None:
    op.drop_constraint("fk_users_locale", "users", type_="foreignkey")
    op.drop_constraint("fk_students_exam_language", "students", type_="foreignkey")
    op.drop_constraint("fk_students_home_language", "students", type_="foreignkey")
    op.drop_constraint("fk_students_book", "students", type_="foreignkey")
    op.drop_constraint("fk_students_curriculum", "students", type_="foreignkey")
    op.drop_column("students", "context_key")
    op.drop_column("students", "book_id")
    op.drop_column("students", "curriculum_id")
