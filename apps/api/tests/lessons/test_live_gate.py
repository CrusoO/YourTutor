"""A live chapter needs an approved lesson for every skill (PLAN G3)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from app.content.validator import validate_path
from app.lessons.loader import live_lesson_errors
from app.lessons.schema import Lesson
from app.registries.paths import repo_root

FIXTURE = repo_root() / "packages" / "shared" / "fixtures" / "lessons" / "valid_full_lesson.json"


def _lesson(skill_id: str, status: str) -> Lesson:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))["lesson"]
    data["id"] = f"LESSON.{skill_id}"
    data["skill_id"] = skill_id
    data["status"] = status
    for beat in data["beats"]:
        if beat["kind"] == "explain_scene":
            beat["scene"]["skill_id"] = skill_id
    return Lesson.model_validate(data)


def _overlay(id_: str, live: bool, skills: list[str]) -> SimpleNamespace:
    return SimpleNamespace(id=id_, live=live, skill_ids=skills)


def test_live_overlay_with_an_approved_lesson_per_skill_passes() -> None:
    lessons = {"a": _lesson("S.A", "approved"), "b": _lesson("S.B", "approved")}
    assert live_lesson_errors(lessons, [_overlay("OV", True, ["S.A", "S.B"])]) == []


def test_live_overlay_names_skills_with_no_lesson_or_only_a_draft() -> None:
    lessons = {"a": _lesson("S.A", "approved"), "b": _lesson("S.B", "draft")}
    errors = live_lesson_errors(lessons, [_overlay("OV", True, ["S.A", "S.B", "S.C"])])
    assert len(errors) == 1
    assert "OV is live but lacks an approved lesson" in errors[0]
    assert "S.B (draft)" in errors[0] and "S.C (none)" in errors[0] and "S.A" not in errors[0]


def test_a_non_live_overlay_is_not_held_to_it() -> None:
    assert live_lesson_errors({}, [_overlay("OV", False, ["S.A"])]) == []


def test_content_validate_refuses_a_live_chapter_without_an_approved_lesson(
    content_root: Path,
) -> None:
    overlay = content_root / "overlays" / "ov.yaml"
    data = yaml.safe_load(overlay.read_text(encoding="utf-8"))
    data["live"] = True
    overlay.write_text(yaml.safe_dump(data), encoding="utf-8")
    report = validate_path(content_root)
    assert any(
        "ov1 is live but lacks an approved lesson: MATH.S1 (none)" in e for e in report.errors
    )
