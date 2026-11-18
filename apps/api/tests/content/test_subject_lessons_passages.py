"""Lessons and passages under `<root>/<board>/<class>/<subject>/` load like the root's own."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.ask.passages import load_passages
from app.lessons.loader import lesson_errors, load_lessons
from tests.legacy_content import LEGACY_CONTENT_ROOT

SUBJECT = Path("cbse") / "10" / "maths"


def _lesson() -> dict:
    path = LEGACY_CONTENT_ROOT / "lessons" / "two_step_balancing.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def test_a_lesson_in_a_subject_folder_is_loaded_and_checked(tmp_path: Path) -> None:
    lesson = _lesson()
    # a subject folder only counts once it holds a content folder, as for items
    (tmp_path / SUBJECT / "skills").mkdir(parents=True)
    _write(tmp_path / SUBJECT / "lessons" / "l.yaml", lesson)
    assert list(load_lessons(tmp_path)) == [lesson["id"]]
    errors = lesson_errors(tmp_path, {"MATH.SOMETHING.ELSE"})
    assert any("unknown skill" in e for e in errors)
    assert lesson_errors(tmp_path, {lesson["skill_id"]}) == []


def test_root_and_subject_lessons_are_both_loaded(tmp_path: Path) -> None:
    lesson = _lesson()
    (tmp_path / SUBJECT / "skills").mkdir(parents=True)
    _write(tmp_path / "lessons" / "a.yaml", lesson)
    _write(tmp_path / SUBJECT / "lessons" / "b.yaml", {**lesson, "id": "LESSON.OTHER.1"})
    assert sorted(load_lessons(tmp_path)) == sorted([lesson["id"], "LESSON.OTHER.1"])
    errors = lesson_errors(tmp_path, {lesson["skill_id"]})
    assert any("more than one lesson" in e for e in errors)


def test_a_passage_in_a_subject_folder_is_loaded(tmp_path: Path) -> None:
    row = {
        "id": "PSG.SUBJ.1",
        "chapter_id": "cbse.10.maths.quadratic",
        "section_key": "s1",
        "skill_ids": ["MATH.ALG.QUAD.SOLVE_FORMULA"],
        "source_type": "authored_notes",
        "licence_status": "owned",
        "source_ref": "NOTE.X",
        "text": "A quadratic equation has at most two roots.",
    }
    (tmp_path / SUBJECT / "skills").mkdir(parents=True)
    _write(tmp_path / SUBJECT / "passages" / "p.yaml", {"passages": [row]})
    assert [p.id for p in load_passages(tmp_path)] == ["PSG.SUBJ.1"]
