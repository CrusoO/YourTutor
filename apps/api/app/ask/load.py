"""Validate and load passages (called by `content validate` / `content load`)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.ask.embed import default_embedder
from app.ask.passages import chapter_index, load_passages, passage_errors
from app.db.models import PassageRow
from app.registries.loaders import CurriculumSpec, load_locales_config


def validate_passages(
    root: Path,
    curricula: dict[str, CurriculumSpec],
    skill_ids: set[str],
    sources: set[str],
) -> list[str]:
    index = chapter_index(curricula)
    sections = {chapter: set(keys) for chapter, (_, _, keys) in index.items()}
    locales = set(load_locales_config()[1])
    return passage_errors(root, sections, skill_ids, sources, locales)


def upsert_passages(session: Session, root: Path, curricula: dict[str, CurriculumSpec]) -> int:
    """Replace the passage rows with what `<root>/passages` holds; embed each text once."""
    index = chapter_index(curricula)
    embedder = default_embedder()
    session.query(PassageRow).delete()
    passages = load_passages(root)
    for p in passages:
        curriculum_id, book_id, _ = index[p.chapter_id]
        session.add(
            PassageRow(
                id=p.id,
                curriculum_id=curriculum_id,
                book_id=book_id,
                chapter_id=p.chapter_id,
                section_id=f"{p.chapter_id}.{p.section_key}",
                page=p.page,
                locale=p.locale,
                text=p.text.strip(),
                skill_ids=list(p.skill_ids),
                embedding=embedder.embed(p.text),
                source_type=p.source_type,
                licence_status=p.licence_status,
                source_ref=p.source_ref,
                reviewer=p.reviewer,
                content_hash=p.content_hash,
                edition_year=p.edition_year,
                status=p.status,
            )
        )
    return len(passages)
