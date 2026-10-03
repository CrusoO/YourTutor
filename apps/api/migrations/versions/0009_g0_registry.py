"""G0 curriculum and locale registry tables.

Revision ID: 0009_g0_registry
Revises: 0008_retire
Create Date: 2026-10-04
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_g0_registry"
down_revision: str | None = "0008_retire"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "locales" not in tables:
        op.create_table(
            "locales",
            sa.Column("code", sa.String(), primary_key=True),
            sa.Column("fallback_chain", sa.JSON(), nullable=False),
        )
    if "curricula" not in tables:
        op.create_table(
            "curricula",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("default_timezone", sa.String(), nullable=False),
            sa.Column("jurisdiction_profile", sa.String(), nullable=False),
            sa.Column("legacy_board", sa.String(), nullable=True),
        )
    if "books" not in tables:
        op.create_table(
            "books",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("curriculum_id", sa.String(), sa.ForeignKey("curricula.id"), nullable=False),
            sa.Column("grade", sa.Integer(), nullable=False),
            sa.Column("default_chapter_id", sa.String(), nullable=False),
        )
    if "chapters" not in tables:
        op.create_table(
            "chapters",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("book_id", sa.String(), sa.ForeignKey("books.id"), nullable=False),
            sa.Column("overlay_id", sa.String(), nullable=False),
            sa.Column("chapter_key", sa.String(), nullable=False),
        )
    _seed_registry(bind)


def _seed_registry(conn) -> None:
    locales = [
        ("en", []),
        ("ne", ["en"]),
        ("as", ["en"]),
    ]
    for code, chain in locales:
        conn.execute(
            sa.text(
                "INSERT INTO locales (code, fallback_chain) VALUES (:c, :f) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"c": code, "f": json.dumps(chain)},
        )
    curricula = [
        ("bhutan", "Asia/Thimphu", "default_strict", "bhutan"),
        ("seba", "Asia/Kolkata", "default_strict", "seba"),
        ("sample_board", "UTC", "default_strict", None),
    ]
    for cid, tz, jur, legacy in curricula:
        conn.execute(
            sa.text(
                "INSERT INTO curricula (id, default_timezone, jurisdiction_profile, legacy_board) "
                "VALUES (:id, :tz, :j, :lb) ON CONFLICT (id) DO NOTHING"
            ),
            {"id": cid, "tz": tz, "j": jur, "lb": legacy},
        )
    books = [
        ("bhutan_class9", "bhutan", 9, "bhutan_class9"),
        ("seba_class9", "seba", 9, "seba_class9"),
        ("sample_class9", "sample_board", 9, "sample_class9"),
    ]
    for bid, cid, grade, default_ch in books:
        conn.execute(
            sa.text(
                "INSERT INTO books (id, curriculum_id, grade, default_chapter_id) "
                "VALUES (:id, :c, :g, :d) ON CONFLICT (id) DO NOTHING"
            ),
            {"id": bid, "c": cid, "g": grade, "d": default_ch},
        )
    chapters = [
        ("bhutan_class9", "bhutan_class9", "bhutan_class9", "linear_equations"),
        ("seba_class9", "seba_class9", "seba_class9", "linear_equations"),
        ("sample_class9", "sample_class9", "bhutan_class9", "linear_equations"),
    ]
    for ch_id, book_id, overlay_id, key in chapters:
        conn.execute(
            sa.text(
                "INSERT INTO chapters (id, book_id, overlay_id, chapter_key) "
                "VALUES (:id, :b, :o, :k) ON CONFLICT (id) DO NOTHING"
            ),
            {"id": ch_id, "b": book_id, "o": overlay_id, "k": key},
        )


def downgrade() -> None:
    op.drop_table("chapters")
    op.drop_table("books")
    op.drop_table("curricula")
    op.drop_table("locales")
