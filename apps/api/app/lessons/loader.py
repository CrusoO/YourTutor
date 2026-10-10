"""Load lessons from `<content>/lessons/*.yaml`. S1a serves lessons straight from validated content
files; database tables for lessons, scenes and widgets arrive with G3."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.config import settings
from app.lessons.budget import MAX_KB_PER_MINUTE, scene_kb_per_minute
from app.lessons.schema import Lesson, lesson_rule_errors
from app.registries.paths import content_root


class LessonLoadError(ValueError):
    pass


def lessons_dir(root: Path | None = None) -> Path:
    return (root or content_root()) / "lessons"


def _files(root: Path | None) -> list[Path]:
    folder = lessons_dir(root)
    return sorted(folder.glob("*.yaml")) if folder.is_dir() else []


def _parse(path: Path) -> tuple[Lesson | None, list[str]]:
    """The lesson (when it parses) and rule-code errors, each prefixed with the file name."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        lesson = Lesson.model_validate(data)
    except (yaml.YAMLError, ValidationError) as exc:
        first = str(exc).splitlines()[0] if str(exc) else "invalid"
        return None, [f"lesson {path.name}: schema.invalid ({first})"]
    return lesson, [f"lesson {path.name}: {code}" for code in lesson_rule_errors(lesson)]


def load_lessons(root: Path | None = None) -> dict[str, Lesson]:
    """All lessons by id. Raises `LessonLoadError` naming the file when one is invalid."""
    out: dict[str, Lesson] = {}
    for path in _files(root):
        lesson, errors = _parse(path)
        if lesson is None or errors:
            raise LessonLoadError("; ".join(errors))
        out[lesson.id] = lesson
    return out


def lesson_errors(root: Path, skill_ids: set[str], sources: set[str] | None = None) -> list[str]:
    """Every problem in the lessons folder, for `content validate` and `content load`.

    With `sources` (the approved source ids), every lesson and scene `source_ref` must be in it.
    """
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    by_skill: dict[str, list[str]] = {}
    for path in _files(root):
        lesson, file_errors = _parse(path)
        errors.extend(file_errors)
        if lesson is None:
            continue
        if lesson.id in seen_ids:
            errors.append(
                f"lesson {path.name}: duplicate lesson id {lesson.id} ({seen_ids[lesson.id]})"
            )
        seen_ids[lesson.id] = path.name
        by_skill.setdefault(lesson.skill_id, []).append(path.name)
        if lesson.skill_id not in skill_ids:
            errors.append(f"lesson {path.name}: unknown skill {lesson.skill_id}")
        if sources is not None and lesson.source_ref not in sources:
            errors.append(f"lesson {path.name}: source.unknown ({lesson.source_ref})")
        for scene in lesson.scenes():
            if sources is not None and scene.source_ref not in sources:
                errors.append(
                    f"lesson {path.name}: scene {scene.id} source.unknown ({scene.source_ref})"
                )
            rate = scene_kb_per_minute(scene)
            if rate > MAX_KB_PER_MINUTE:
                errors.append(
                    f"lesson {path.name}: scene {scene.id} is {rate:.0f} KB per minute "
                    f"(limit {MAX_KB_PER_MINUTE})"
                )
    for skill_id, names in by_skill.items():
        if len(names) > 1:
            errors.append(f"more than one lesson for skill {skill_id}: {', '.join(sorted(names))}")
    return errors


def servable(lesson: Lesson) -> bool:
    """Same content gate as items: approved, or drafts only when ALLOW_DRAFT_CONTENT is on."""
    return lesson.status.value == "approved" or settings.allow_draft_content


_CACHE: dict[tuple[str, tuple[tuple[str, float], ...]], dict[str, Lesson]] = {}


def _cached(root: Path | None) -> dict[str, Lesson]:
    folder = lessons_dir(root)
    signature = tuple((p.name, p.stat().st_mtime) for p in _files(root))
    key = (str(folder), signature)
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = load_lessons(root)
    return _CACHE[key]


def lesson_for_skill(skill_id: str, root: Path | None = None) -> Lesson | None:
    for lesson in _cached(root).values():
        if lesson.skill_id == skill_id:
            return lesson
    return None


def lesson_by_id(lesson_id: str, root: Path | None = None) -> Lesson | None:
    return _cached(root).get(lesson_id)


def all_lessons(root: Path | None = None) -> list[Lesson]:
    return sorted(_cached(root).values(), key=lambda lesson: lesson.id)
