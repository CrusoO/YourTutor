"""Passages: grounded source text with provenance and licence (ARCHITECTURE section 12.2).

`<content>/passages/*.yaml` holds passages mapped to a chapter section. The loader refuses any
passage whose licence is not one of the allowed ones, so unlicensed text can never be indexed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ALLOWED_LICENCES = frozenset({"owned", "licensed", "open_licence_compatible"})
SOURCE_TYPES = frozenset({"authored_notes", "licensed_textbook"})
STATUSES = frozenset({"draft", "approved", "retired"})


class Passage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    chapter_id: str
    section_key: str
    page: int | None = None
    locale: str = "en"
    text: str = Field(min_length=1)
    skill_ids: list[str] = Field(default_factory=list)
    source_type: str
    licence_status: str
    source_ref: str | None = None  # an id in content/sources when the text is an authored note
    reviewer: str | None = None
    edition_year: int | None = None
    status: str = "draft"

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.strip().encode("utf-8")).hexdigest()


def passages_dir(root: Path) -> Path:
    return root / "passages"


def _files(root: Path) -> list[Path]:
    folder = passages_dir(root)
    return sorted(folder.glob("*.yaml")) if folder.is_dir() else []


def _parse(path: Path) -> tuple[list[Passage], list[str]]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        rows = data["passages"]
        if not isinstance(rows, list):
            raise TypeError("passages must be a list")
    except (yaml.YAMLError, KeyError, TypeError, AttributeError) as exc:
        return [], [f"passages {path.name}: schema.invalid ({str(exc).splitlines()[0]})"]
    out: list[Passage] = []
    errors: list[str] = []
    for row in rows:
        try:
            out.append(Passage.model_validate(row))
        except ValidationError as exc:
            ident = row.get("id") if isinstance(row, dict) else "?"
            errors.append(
                f"passages {path.name}: {ident} schema.invalid ({exc.errors()[0]['msg']})"
            )
    return out, errors


def load_passages(root: Path) -> list[Passage]:
    out: list[Passage] = []
    for path in _files(root):
        found, errors = _parse(path)
        if errors:
            raise ValueError("; ".join(errors))
        out.extend(found)
    return out


def passage_errors(
    root: Path,
    sections: dict[str, set[str]],
    skill_ids: set[str],
    sources: set[str],
    locales: set[str],
) -> list[str]:
    """Every problem in the passages folder.

    `sections` maps chapter id -> section keys. Rules: a known licence and source type, a known
    chapter and section, known skills and locale, an approved source for authored notes, and
    unique ids.
    """
    errors: list[str] = []
    seen: set[str] = set()
    for path in _files(root):
        found, parse_errors = _parse(path)
        errors.extend(parse_errors)
        for p in found:
            where = f"passages {path.name}: {p.id}"
            if p.id in seen:
                errors.append(f"{where} duplicate passage id")
            seen.add(p.id)
            if p.licence_status not in ALLOWED_LICENCES:
                errors.append(
                    f"{where} licence.refused ({p.licence_status!r}; allowed: "
                    f"{', '.join(sorted(ALLOWED_LICENCES))})"
                )
            if p.source_type not in SOURCE_TYPES:
                errors.append(f"{where} source_type.unknown ({p.source_type!r})")
            if p.status not in STATUSES:
                errors.append(f"{where} status.unknown ({p.status!r})")
            if p.chapter_id not in sections:
                errors.append(f"{where} chapter.unknown ({p.chapter_id})")
            elif p.section_key not in sections[p.chapter_id]:
                errors.append(f"{where} section.unknown ({p.chapter_id}.{p.section_key})")
            for skill in p.skill_ids:
                if skill not in skill_ids:
                    errors.append(f"{where} skill.unknown ({skill})")
            if p.locale not in locales:
                errors.append(f"{where} locale.unknown ({p.locale})")
            if p.source_type == "authored_notes" and p.source_ref not in sources:
                errors.append(f"{where} source.unknown ({p.source_ref})")
            if p.source_type == "licensed_textbook" and not (p.reviewer and p.edition_year):
                errors.append(f"{where} textbook text needs a reviewer and an edition_year")
    return errors


def chapter_index(curricula: dict) -> dict[str, tuple[str, str, tuple[str, ...]]]:
    """Chapter id -> (curriculum id, book id, section keys), from the curriculum registry."""
    out: dict[str, tuple[str, str, tuple[str, ...]]] = {}
    for spec in curricula.values():
        for book in spec.books:
            for chapter in book.chapters:
                out[chapter.id] = (spec.id, book.id, tuple(s.key for s in chapter.sections))
    return out
