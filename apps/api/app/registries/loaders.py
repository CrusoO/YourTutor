from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.registries.paths import config_dir, content_curricula_dir


class RegistryLoadError(ValueError):
    pass


LOCALE_STATUSES = ("active", "draft")


@dataclass(frozen=True)
class LocaleSpec:
    code: str
    fallback_chain: tuple[str, ...]
    name: str = ""
    script: str = ""
    status: str = "draft"


@dataclass(frozen=True)
class GradeBand:
    id: str
    grades: tuple[int, ...]
    max_words: int  # per tutor message
    soft_minutes: int
    soft_items: int
    hard_minutes: int
    read_aloud_default: bool
    style: str = ""  # tone and sentence style, put in every LLM prompt
    target_size: str = "normal"  # UI tap-target class: normal or large
    choice: str = ""  # what the student may choose: two_options, skill_first, goal_setting, ...


@dataclass(frozen=True)
class QuietHours:
    start: str
    end: str


@dataclass(frozen=True)
class JurisdictionProfile:
    id: str
    quiet_hours: QuietHours
    notation_profile: str


@dataclass(frozen=True)
class NotationProfile:
    id: str
    decimal_separator: str
    multiply_symbols: tuple[str, ...]
    divide_symbols: tuple[str, ...]


@dataclass(frozen=True)
class SectionSpec:
    key: str
    id: str  # f"{chapter_id}.{key}"; the overlay `section_map` is keyed by `key`
    order: int
    titles: dict[str, str]
    page_start: int | None
    page_end: int | None


@dataclass(frozen=True)
class ChapterSpec:
    id: str
    overlay_id: str
    chapter_key: str
    sections: tuple[SectionSpec, ...] = ()
    titles: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BookSpec:
    id: str
    grade: int
    default_chapter_id: str
    chapters: tuple[ChapterSpec, ...]
    subject: str = "math"  # what the book teaches; the context picker lists it
    medium: str | None = None  # language of instruction, when a curriculum has several


@dataclass(frozen=True)
class CurriculumSpec:
    id: str
    default_timezone: str
    jurisdiction_profile: str
    legacy_board: str | None
    books: tuple[BookSpec, ...]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RegistryLoadError(f"missing registry file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RegistryLoadError(f"invalid registry root in {path}")
    return data


def load_locales_config(root: Path | None = None) -> tuple[str, dict[str, LocaleSpec]]:
    data = _load_yaml((root or config_dir()) / "locales.yaml")
    default = str(data.get("default") or "en")
    raw = data.get("locales") or []
    out: dict[str, LocaleSpec] = {}
    for row in raw:
        code = str(row["code"])
        chain = tuple(str(x) for x in (row.get("fallback_chain") or []))
        missing = [field for field in ("name", "script", "status") if not row.get(field)]
        if missing:
            raise RegistryLoadError(f"locale {code!r} is missing {', '.join(missing)}")
        if row["status"] not in LOCALE_STATUSES:
            raise RegistryLoadError(f"locale {code!r} has unknown status {row['status']!r}")
        out[code] = LocaleSpec(
            code=code,
            fallback_chain=chain,
            name=str(row["name"]),
            script=str(row["script"]),
            status=str(row["status"]),
        )
    if default not in out:
        raise RegistryLoadError(f"default locale {default!r} not defined")
    return default, out


def load_grade_bands(root: Path | None = None) -> tuple[GradeBand, ...]:
    data = _load_yaml((root or config_dir()) / "grade_bands.yaml")
    bands = []
    seen: dict[int, str] = {}
    for row in data.get("bands") or []:
        band_id = str(row["id"])
        missing = [
            key
            for key in (
                "max_words",
                "soft_minutes",
                "soft_items",
                "hard_minutes",
                "read_aloud_default",
            )
            if key not in row
        ]
        if missing:
            raise RegistryLoadError(f"grade band {band_id!r} is missing {', '.join(missing)}")
        grades = tuple(int(g) for g in row["grades"])
        for grade in grades:
            if grade in seen:
                raise RegistryLoadError(
                    f"grade {grade} is in two bands: {seen[grade]!r} and {band_id!r}"
                )
            seen[grade] = band_id
        bands.append(
            GradeBand(
                id=band_id,
                grades=grades,
                max_words=int(row["max_words"]),
                soft_minutes=int(row["soft_minutes"]),
                soft_items=int(row["soft_items"]),
                hard_minutes=int(row["hard_minutes"]),
                read_aloud_default=bool(row["read_aloud_default"]),
                style=str(row.get("style") or "").strip(),
                target_size=str(row.get("target_size") or "normal"),
                choice=str(row.get("choice") or ""),
            )
        )
    return tuple(bands)


def load_jurisdiction_profile(profile_id: str, root: Path | None = None) -> JurisdictionProfile:
    base = root or config_dir()
    path = base / "jurisdictions" / f"{profile_id}.yaml"
    data = _load_yaml(path)
    if str(data.get("id")) != profile_id:
        raise RegistryLoadError(f"jurisdiction id mismatch in {path}")
    qh = data.get("quiet_hours") or {}
    return JurisdictionProfile(
        id=profile_id,
        quiet_hours=QuietHours(start=str(qh["start"]), end=str(qh["end"])),
        notation_profile=str(data.get("notation_profile") or "default_ascii"),
    )


def load_notation_profiles(root: Path | None = None) -> dict[str, NotationProfile]:
    data = _load_yaml((root or config_dir()) / "notation_profiles.yaml")
    out: dict[str, NotationProfile] = {}
    for pid, row in (data.get("profiles") or {}).items():
        out[str(pid)] = NotationProfile(
            id=str(pid),
            decimal_separator=str(row.get("decimal_separator") or "."),
            multiply_symbols=tuple(str(s) for s in (row.get("multiply_symbols") or ["*"])),
            divide_symbols=tuple(str(s) for s in (row.get("divide_symbols") or ["/"])),
        )
    return out


def _load_chapter(ch: dict[str, Any], path: Path) -> ChapterSpec:
    chapter_id = str(ch["id"])
    sections: list[SectionSpec] = []
    for row in ch.get("sections") or []:
        key = str(row["key"])
        titles = {str(k): str(v) for k, v in (row.get("titles") or {}).items()}
        if "en" not in titles:
            raise RegistryLoadError(f"section {chapter_id}.{key} needs an `en` title in {path}")
        start, end = row.get("page_start"), row.get("page_end")
        sections.append(
            SectionSpec(
                key=key,
                id=f"{chapter_id}.{key}",
                order=int(row["order"]),
                titles=titles,
                page_start=int(start) if start is not None else None,
                page_end=int(end) if end is not None else None,
            )
        )
    return ChapterSpec(
        id=chapter_id,
        overlay_id=str(ch["overlay_id"]),
        chapter_key=str(ch["chapter_key"]),
        sections=tuple(sections),
        titles={str(k): str(v) for k, v in (ch.get("titles") or {}).items()},
    )


def load_curriculum(curriculum_id: str, root: Path | None = None) -> CurriculumSpec:
    base = root or content_curricula_dir()
    path = base / curriculum_id / "curriculum.yaml"
    data = _load_yaml(path)
    if str(data.get("id")) != curriculum_id:
        raise RegistryLoadError(f"curriculum id mismatch in {path}")
    books: list[BookSpec] = []
    for book in data.get("books") or []:
        chapters = tuple(_load_chapter(ch, path) for ch in book.get("chapters") or [])
        books.append(
            BookSpec(
                id=str(book["id"]),
                grade=int(book["grade"]),
                default_chapter_id=str(book["default_chapter_id"]),
                chapters=chapters,
                subject=str(book.get("subject") or "math"),
                medium=str(book["medium"]) if book.get("medium") else None,
            )
        )
    legacy = data.get("legacy_board")
    return CurriculumSpec(
        id=curriculum_id,
        default_timezone=str(data["default_timezone"]),
        jurisdiction_profile=str(data["jurisdiction_profile"]),
        legacy_board=str(legacy) if legacy else None,
        books=tuple(books),
    )


def load_all_curricula(root: Path | None = None) -> dict[str, CurriculumSpec]:
    base = root or content_curricula_dir()
    if not base.is_dir():
        raise RegistryLoadError(f"missing curricula directory: {base}")
    out: dict[str, CurriculumSpec] = {}
    for child in sorted(base.iterdir()):
        if child.is_dir() and (child / "curriculum.yaml").is_file():
            spec = load_curriculum(child.name, root=base)
            out[spec.id] = spec
    return out


def book_for_grade(spec: CurriculumSpec, grade: int) -> BookSpec | None:
    for book in spec.books:
        if book.grade == grade:
            return book
    return spec.books[0] if spec.books else None
