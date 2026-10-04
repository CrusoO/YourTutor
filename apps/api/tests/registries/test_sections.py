from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.validator import curricula_for, load_bundle, validate_bundle, validate_path
from app.db.models import SectionRow
from app.registries.loaders import (
    BookSpec,
    ChapterSpec,
    CurriculumSpec,
    SectionSpec,
    load_all_curricula,
)
from app.registries.paths import repo_root
from app.registries.sections import section_map_errors


@dataclass
class _Overlay:
    id: str
    skill_ids: list[str]
    section_map: dict[str, list[str]] = field(default_factory=dict)


def _curriculum(keys: tuple[str, ...], overlay_id: str = "OV") -> dict[str, CurriculumSpec]:
    sections = tuple(
        SectionSpec(
            key=key,
            id=f"CH.{key}",
            order=index + 1,
            titles={"en": key},
            page_start=None,
            page_end=None,
        )
        for index, key in enumerate(keys)
    )
    chapter = ChapterSpec(id="CH", overlay_id=overlay_id, chapter_key="k", sections=sections)
    book = BookSpec(id="B", grade=9, default_chapter_id="CH", chapters=(chapter,))
    spec = CurriculumSpec(
        id="C",
        default_timezone="UTC",
        jurisdiction_profile="default_strict",
        legacy_board=None,
        books=(book,),
    )
    return {"C": spec}


def test_seed_curricula_have_three_placeholder_sections_each() -> None:
    for spec in load_all_curricula().values():
        for book in spec.books:
            for chapter in book.chapters:
                assert [s.key for s in chapter.sections] == ["s1", "s2", "s3"]
                assert chapter.sections[0].id == f"{chapter.id}.s1"
                assert chapter.sections[0].titles["en"] == "Section 1"


def test_seed_content_validates_with_section_maps() -> None:
    report = validate_path(repo_root() / "content")
    assert not [e for e in report.errors if "section" in e], report.errors
    assert report.bundle is not None
    overlay = next(o for o in report.bundle.overlays if o.id == "bhutan_class9")
    assert sorted(overlay.section_map) == ["s1", "s2", "s3"]
    assert [s for skills in overlay.section_map.values() for s in skills] == overlay.skill_ids


def test_valid_section_map_has_no_errors() -> None:
    overlay = _Overlay("OV", ["A", "B"], {"s1": ["A"], "s2": ["B"]})
    assert section_map_errors([overlay], _curriculum(("s1", "s2"))) == []


def test_unknown_section_key_is_an_error() -> None:
    overlay = _Overlay("OV", ["A"], {"s1": ["A"], "s9": ["A"]})
    errors = section_map_errors([overlay], _curriculum(("s1",)))
    assert any("'s9'" in e and "no section" in e for e in errors)


def test_unknown_skill_in_section_map_is_an_error() -> None:
    overlay = _Overlay("OV", ["A"], {"s1": ["A", "Z"]})
    errors = section_map_errors([overlay], _curriculum(("s1",)))
    assert any("skill Z" in e for e in errors)


def test_section_without_mapping_is_an_error() -> None:
    overlay = _Overlay("OV", ["A"], {"s1": ["A"]})
    errors = section_map_errors([overlay], _curriculum(("s1", "s2")))
    assert any("'s2'" in e and "missing" in e for e in errors)


def test_sections_seeded_in_db(db: Session) -> None:
    rows = db.scalars(select(SectionRow)).all()
    assert len(rows) == 9
    row = db.get(SectionRow, "bhutan_class9.s2")
    assert row is not None
    assert row.chapter_id == "bhutan_class9"
    assert row.order == 2
    assert row.titles == {"en": "Section 2"}


def test_validator_reports_broken_section_map_in_real_bundle() -> None:
    root = repo_root() / "content"
    bundle = load_bundle(root)
    overlay = next(o for o in bundle.overlays if o.id == "bhutan_class9")
    overlay.section_map["s9"] = ["MATH.NOT.REAL"]
    report = validate_bundle(bundle, curricula_for(root))
    assert any("'s9'" in e for e in report.errors)
    assert any("MATH.NOT.REAL" in e for e in report.errors)
