from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.config import settings
from app.content.loader import LoadError, load_path
from app.content.validator import validate_path
from app.lessons.budget import MAX_KB_PER_MINUTE, scene_duration_seconds, scene_kb_per_minute
from app.lessons.loader import (
    LessonLoadError,
    lesson_errors,
    lesson_for_skill,
    load_lessons,
    servable,
)
from app.lessons.schema import Lesson
from app.registries.paths import repo_root
from tests.content.conftest import write_yaml

CONTENT = repo_root() / "content"
SEED_SKILLS = {path.stem for path in (CONTENT / "skills").rglob("*.yaml")}
EXPECTED_SKILLS = {
    "MATH.ALG.LIN1.SOLVE_TWO_STEP",
    "MATH.ALG.LIN1.SOLVE_ONE_STEP",
    "MATH.ALG.INVERSE_OPERATIONS",
    "MATH.ALG.LIN1.FRACTION_COEFF",
}


def _seed_skill_ids() -> set[str]:
    ids: set[str] = set()
    for path in (CONTENT / "skills").rglob("*.yaml"):
        ids.add(str(yaml.safe_load(path.read_text(encoding="utf-8"))["id"]))
    return ids


def test_seed_has_four_draft_lessons_for_four_distinct_skills() -> None:
    lessons = load_lessons(CONTENT)
    assert len(lessons) == 4
    assert {lesson.skill_id for lesson in lessons.values()} == EXPECTED_SKILLS
    for lesson in lessons.values():
        assert lesson.status.value == "draft"
        assert lesson.source_ref.startswith("NOTE.")


def test_every_scene_carries_skill_id_and_source_ref_and_traces_to_its_lesson() -> None:
    for lesson in load_lessons(CONTENT).values():
        scenes = lesson.scenes()
        assert scenes, lesson.id
        for scene in scenes:
            assert scene.skill_id == lesson.skill_id
            assert scene.source_ref.strip() == lesson.source_ref


def test_seed_lessons_use_both_initial_widget_types_and_no_machine_translation() -> None:
    lessons = load_lessons(CONTENT).values()
    types = {widget.type for lesson in lessons for widget in lesson.widgets()}
    assert types == {"balance_scale", "function_graph"}
    raw = json.dumps([lesson.model_dump(mode="json") for lesson in lessons], ensure_ascii=False)
    assert "<Nepali" not in raw and "<Assamese" not in raw
    for lesson in lessons:
        dumped = lesson.model_dump(mode="json", by_alias=True, exclude_none=True)
        assert '"ne"' not in json.dumps(dumped) and '"as"' not in json.dumps(dumped)


def test_seed_lessons_reference_real_skills_and_pass_every_check() -> None:
    assert EXPECTED_SKILLS <= _seed_skill_ids()
    assert lesson_errors(CONTENT, _seed_skill_ids()) == []


def test_ported_lesson_keeps_the_prototypes_structure() -> None:
    lesson = lesson_for_skill("MATH.ALG.LIN1.SOLVE_TWO_STEP", CONTENT)
    assert lesson is not None
    assert [beat.kind for beat in lesson.beats] == [
        "predict",
        "explore",
        "explain_scene",
        "worked_example",
        "explore",
        "check",
    ]
    scene = lesson.scenes()[0]
    assert len(scene.steps) == 5


def test_lesson_for_unknown_skill_is_none() -> None:
    assert lesson_for_skill("MATH.NOPE", CONTENT) is None


def test_servable_follows_the_content_gate() -> None:
    lesson = lesson_for_skill("MATH.ALG.LIN1.SOLVE_TWO_STEP", CONTENT)
    assert lesson is not None
    settings.allow_draft_content = False
    assert servable(lesson) is False
    settings.allow_draft_content = True
    assert servable(lesson) is True
    approved = Lesson.model_validate(
        {**lesson.model_dump(mode="json", by_alias=True), "status": "approved"}
    )
    settings.allow_draft_content = False
    assert servable(approved) is True


# --- error reporting -------------------------------------------------------------------------


def _copy_seed_lesson(tmp_path: Path, name: str = "two_step_balancing") -> dict:
    data = yaml.safe_load((CONTENT / "lessons" / f"{name}.yaml").read_text(encoding="utf-8"))
    (tmp_path / "lessons").mkdir(exist_ok=True)
    return data


def test_errors_name_the_file_and_the_rule(tmp_path: Path) -> None:
    data = _copy_seed_lesson(tmp_path)
    data["beats"][0], data["beats"][1] = data["beats"][1], data["beats"][0]
    write_yaml(tmp_path / "lessons" / "broken.yaml", data)
    errors = lesson_errors(tmp_path, {data["skill_id"]})
    assert any("broken.yaml" in e and "lesson.first_beat_not_predict" in e for e in errors)


def test_lesson_for_an_unknown_skill_is_an_error(tmp_path: Path) -> None:
    data = _copy_seed_lesson(tmp_path)
    write_yaml(tmp_path / "lessons" / "orphan.yaml", data)
    errors = lesson_errors(tmp_path, {"MATH.SOMETHING.ELSE"})
    assert any("unknown skill" in e for e in errors)


def test_two_lessons_for_one_skill_is_an_error(tmp_path: Path) -> None:
    data = _copy_seed_lesson(tmp_path)
    write_yaml(tmp_path / "lessons" / "a.yaml", data)
    other = {**data, "id": "LESSON.TWO_STEP.COPY"}
    write_yaml(tmp_path / "lessons" / "b.yaml", other)
    errors = lesson_errors(tmp_path, {data["skill_id"]})
    assert any("more than one lesson" in e for e in errors)


def test_duplicate_lesson_ids_are_an_error(tmp_path: Path) -> None:
    data = _copy_seed_lesson(tmp_path)
    write_yaml(tmp_path / "lessons" / "a.yaml", data)
    write_yaml(tmp_path / "lessons" / "b.yaml", {**data, "skill_id": "MATH.OTHER"})
    errors = lesson_errors(tmp_path, {data["skill_id"], "MATH.OTHER"})
    assert any("duplicate lesson id" in e for e in errors)


def test_a_missing_lessons_folder_is_fine(tmp_path: Path) -> None:
    assert lesson_errors(tmp_path, set()) == []
    assert load_lessons(tmp_path) == {}


def test_load_lessons_raises_a_clear_error_on_a_bad_file(tmp_path: Path) -> None:
    (tmp_path / "lessons").mkdir()
    (tmp_path / "lessons" / "bad.yaml").write_text("id: x\n", encoding="utf-8")
    with pytest.raises(LessonLoadError, match="bad.yaml"):
        load_lessons(tmp_path)


# --- size budget ---------------------------------------------------------------------------


def test_seed_scenes_are_well_inside_the_budget() -> None:
    for lesson in load_lessons(CONTENT).values():
        for scene in lesson.scenes():
            assert scene_duration_seconds(scene) > 10
            assert scene_kb_per_minute(scene) < MAX_KB_PER_MINUTE / 2, scene.id


def test_a_bloated_scene_breaks_the_budget(tmp_path: Path) -> None:
    data = _copy_seed_lesson(tmp_path)
    step = data["beats"][2]["scene"]["steps"][0]
    step["actions"] = [
        {"kind": "write_text", "x": n, "y": n, "size": 10, "text": "x" * 2000} for n in range(50)
    ]
    write_yaml(tmp_path / "lessons" / "huge.yaml", data)
    errors = lesson_errors(tmp_path, {data["skill_id"]})
    assert any("KB per minute" in e for e in errors)


# --- content validate / load integration ----------------------------------------------------


def test_content_validate_reports_lesson_errors(content_root: Path) -> None:
    data = yaml.safe_load(
        (CONTENT / "lessons" / "two_step_balancing.yaml").read_text(encoding="utf-8")
    )
    data["skill_id"] = "MATH.S1"
    for beat in data["beats"]:
        if beat["kind"] == "explain_scene":
            beat["scene"]["skill_id"] = "MATH.S1"
    data["beats"].pop()  # no check beat
    write_yaml(content_root / "lessons" / "bad.yaml", data)
    report = validate_path(content_root)
    assert any("lesson.last_beat_not_check" in e for e in report.errors), report.errors


def test_content_validate_accepts_a_good_lesson(content_root: Path) -> None:
    data = yaml.safe_load(
        (CONTENT / "lessons" / "two_step_balancing.yaml").read_text(encoding="utf-8")
    )
    data["skill_id"] = "MATH.S1"
    for beat in data["beats"]:
        if beat["kind"] == "explain_scene":
            beat["scene"]["skill_id"] = "MATH.S1"
    write_yaml(content_root / "lessons" / "good.yaml", data)
    write_yaml(
        content_root / "sources" / "notes.yaml",
        {"sources": [{"id": "NOTE.LIN1.TWO_STEP", "licence": "authored", "title": "Two-step"}]},
    )
    report = validate_path(content_root)
    assert not [e for e in report.errors if "lesson" in e.lower()], report.errors


def test_content_load_refuses_bad_lessons(content_root: Path, tmp_path: Path) -> None:
    data = yaml.safe_load(
        (CONTENT / "lessons" / "two_step_balancing.yaml").read_text(encoding="utf-8")
    )
    data["skill_id"] = "MATH.NOT.THERE"
    write_yaml(content_root / "lessons" / "bad.yaml", data)
    with pytest.raises(LoadError, match="lesson"):
        load_path(content_root, database_url=f"sqlite:///{tmp_path / 'x.db'}")
