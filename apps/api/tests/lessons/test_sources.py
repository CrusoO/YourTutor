"""Lesson and scene source refs must name an approved entry in content/sources/."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.lessons.loader import lesson_errors
from app.lessons.sources import approved_source_ids, source_errors
from app.registries.paths import repo_root
from tests.content.conftest import write_yaml

CONTENT = repo_root() / "content"
SKILLS = {path.stem for path in (CONTENT / "skills").rglob("*.yaml")}


def _copy_lessons(tmp_path: Path) -> Path:
    folder = tmp_path / "lessons"
    folder.mkdir()
    for path in (CONTENT / "lessons").glob("*.yaml"):
        (folder / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def _sources(root: Path, rows: list[dict]) -> None:
    write_yaml(root / "sources" / "notes.yaml", {"sources": rows})


def test_seed_sources_are_approved_and_cover_every_lesson_ref() -> None:
    assert source_errors(CONTENT) == []
    ids = approved_source_ids(CONTENT)
    assert {"NOTE.ALG.INVERSE", "NOTE.LIN1.ONE_STEP"} <= ids
    assert [e for e in lesson_errors(CONTENT, SKILLS, sources=ids) if "source." in e] == []


def test_a_lesson_naming_an_unknown_source_is_an_error(tmp_path: Path) -> None:
    root = _copy_lessons(tmp_path)
    _sources(root, [{"id": "NOTE.OTHER", "licence": "authored", "title": "Other"}])
    errors = lesson_errors(root, SKILLS, sources=approved_source_ids(root))
    assert any("source.unknown" in e and "NOTE.LIN1.ONE_STEP" in e for e in errors)
    # a scene's own source_ref is checked too, not only the lesson's
    assert any("source.unknown" in e and "scene" in e for e in errors)


def test_no_sources_registry_means_every_ref_is_unknown(tmp_path: Path) -> None:
    root = _copy_lessons(tmp_path)
    assert approved_source_ids(root) == set()
    assert any("source.unknown" in e for e in lesson_errors(root, SKILLS, sources=set()))


def test_a_licence_that_is_not_approved_is_refused(tmp_path: Path) -> None:
    _sources(
        tmp_path,
        [
            {"id": "NOTE.A", "licence": "authored", "title": "A"},
            {"id": "BOOK.B", "licence": "all_rights_reserved", "title": "B"},
            {"id": "NOTE.A", "licence": "authored", "title": "dup"},
        ],
    )
    errors = source_errors(tmp_path)
    assert any("BOOK.B" in e and "licence" in e for e in errors)
    assert any("NOTE.A" in e and "duplicate" in e for e in errors)
    assert approved_source_ids(tmp_path) == {"NOTE.A"}


def test_a_broken_sources_file_is_reported(tmp_path: Path) -> None:
    folder = tmp_path / "sources"
    folder.mkdir()
    (folder / "notes.yaml").write_text("sources: [unclosed", encoding="utf-8")
    assert any("notes.yaml" in e for e in source_errors(tmp_path))
    yaml.safe_load("a: 1")
