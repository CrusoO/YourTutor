"""Seed G0 registry rows for SQLite test databases (create_all path)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import BookRow, ChapterRow, CurriculumRow, LocaleRow
from app.registries.loaders import load_all_curricula, load_locales_config


def seed_g0_registry(session: Session) -> None:
    _, locales = load_locales_config()
    for spec in locales.values():
        session.merge(LocaleRow(code=spec.code, fallback_chain=list(spec.fallback_chain)))
    session.flush()
    for spec in load_all_curricula().values():
        session.merge(
            CurriculumRow(
                id=spec.id,
                default_timezone=spec.default_timezone,
                jurisdiction_profile=spec.jurisdiction_profile,
                legacy_board=spec.legacy_board,
            )
        )
    session.flush()
    for spec in load_all_curricula().values():
        for book in spec.books:
            session.merge(
                BookRow(
                    id=book.id,
                    curriculum_id=spec.id,
                    grade=book.grade,
                    default_chapter_id=book.default_chapter_id,
                )
            )
    session.flush()
    for spec in load_all_curricula().values():
        for book in spec.books:
            for chapter in book.chapters:
                session.merge(
                    ChapterRow(
                        id=chapter.id,
                        book_id=book.id,
                        overlay_id=chapter.overlay_id,
                        chapter_key=chapter.chapter_key,
                    )
                )
    session.flush()
