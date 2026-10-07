"""Seed G0 registry rows for SQLite test databases (create_all path)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import BookRow, ChapterRow, CurriculumRow, LocaleRow, SectionRow
from app.registries.loaders import load_all_curricula, load_locales_config


def seed_g0_registry(session: Session) -> None:
    _, locales = load_locales_config()
    for locale_spec in locales.values():
        session.merge(
            LocaleRow(
                code=locale_spec.code,
                name=locale_spec.name,
                script=locale_spec.script,
                status=locale_spec.status,
                fallback_chain=list(locale_spec.fallback_chain),
            )
        )
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
            for position, chapter in enumerate(book.chapters, start=1):
                session.merge(
                    ChapterRow(
                        id=chapter.id,
                        book_id=book.id,
                        overlay_id=chapter.overlay_id,
                        chapter_key=chapter.chapter_key,
                        titles=dict(chapter.titles),
                        position=position,
                    )
                )
    session.flush()
    for spec in load_all_curricula().values():
        for book in spec.books:
            for chapter in book.chapters:
                for section in chapter.sections:
                    session.merge(
                        SectionRow(
                            id=section.id,
                            chapter_id=chapter.id,
                            order=section.order,
                            titles=section.titles,
                            page_start=section.page_start,
                            page_end=section.page_end,
                        )
                    )
    session.flush()
