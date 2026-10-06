"""The Python side of the lesson schema contract; the TS validator runs the same fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.lessons.schema import (
    Lesson,
    Scene,
    WidgetSpec,
    lesson_json_schemas,
    validate_lesson_dict,
)
from app.registries.paths import repo_root

FIXTURES = repo_root() / "packages" / "shared" / "fixtures" / "lessons"
SCHEMAS = repo_root() / "packages" / "shared" / "schemas"
FILES = sorted(FIXTURES.glob("*.json"))


def test_fixture_directory_has_valid_and_invalid_cases() -> None:
    names = [p.stem for p in FILES]
    assert sum(n.startswith("valid_") for n in names) >= 2
    assert sum(n.startswith("invalid_") for n in names) >= 14


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_lesson_fixture(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert validate_lesson_dict(data["lesson"]) == data["expect_errors"], path.stem


def test_valid_lesson_parses_into_typed_models() -> None:
    data = json.loads((FIXTURES / "valid_full_lesson.json").read_text(encoding="utf-8"))
    lesson = Lesson.model_validate(data["lesson"])
    assert [beat.kind for beat in lesson.beats] == [
        "predict",
        "explore",
        "explain_scene",
        "worked_example",
        "explore",
        "check",
    ]
    scene = lesson.scenes()[0]
    assert isinstance(scene, Scene) and scene.skill_id == lesson.skill_id


def test_generated_json_schemas_match_the_committed_files() -> None:
    """Edit the Pydantic models, then run `python scripts/write_lesson_schemas.py`."""
    generated = lesson_json_schemas()
    assert set(generated) == {"lesson.schema.json", "scene.schema.json", "widget.schema.json"}
    for name, schema in generated.items():
        committed = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
        assert committed == schema, f"{name} is out of date"


def test_widget_union_is_exposed_for_the_widget_schema() -> None:
    assert WidgetSpec is not None
