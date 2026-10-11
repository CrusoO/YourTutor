"""G8 step 1: editing an approved lesson, scene, widget or passage resets its approval."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from app.ask.passages import load_passages
from app.content.approval import lesson_hash, passage_hash, reset_stale_approvals
from app.lessons.loader import load_lessons
from app.registries.paths import content_root

LESSON_FILE = "brackets.yaml"


def _approve_lesson(path: Path, reviewer: str = "curriculum.lead") -> None:
    lesson = next(iter(load_lessons(path.parent.parent).values()))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.update(status="approved", reviewed_by=reviewer, content_hash=lesson_hash(lesson))
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _lesson_root(tmp_path: Path) -> tuple[Path, Path]:
    (tmp_path / "lessons").mkdir()
    path = tmp_path / "lessons" / LESSON_FILE
    shutil.copy(content_root() / "lessons" / LESSON_FILE, path)
    return tmp_path, path


def test_an_approved_lesson_with_a_matching_hash_stays_approved(tmp_path: Path) -> None:
    root, path = _lesson_root(tmp_path)
    _approve_lesson(path)
    assert reset_stale_approvals(root) == []
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["status"] == "approved"


def test_editing_the_lesson_text_resets_it_to_draft(tmp_path: Path) -> None:
    root, path = _lesson_root(tmp_path)
    _approve_lesson(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["title"]["en"] = "Opening brackets, edited"
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    warnings = reset_stale_approvals(root)
    assert len(warnings) == 1 and "reset to draft" in warnings[0]
    after = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert after["status"] == "draft" and after["reviewed_by"] is None
    assert after["content_hash"] is None
    assert reset_stale_approvals(root) == []  # nothing left to reset


def test_editing_a_scene_caption_or_a_widget_changes_the_lesson_hash(tmp_path: Path) -> None:
    root, path = _lesson_root(tmp_path)
    original = lesson_hash(next(iter(load_lessons(root).values())))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    scene = next(b for b in data["beats"] if b["kind"] == "explain_scene")
    scene["scene"]["steps"][0]["caption"]["en"] = "A different caption."
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    assert lesson_hash(next(iter(load_lessons(root).values()))) != original


def test_approved_without_a_reviewer_or_hash_is_reset(tmp_path: Path) -> None:
    root, path = _lesson_root(tmp_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["status"] = "approved"
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    assert len(reset_stale_approvals(root)) == 1
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["status"] == "draft"


def test_drafts_are_left_alone(tmp_path: Path) -> None:
    root, path = _lesson_root(tmp_path)
    before = path.read_text(encoding="utf-8")
    assert reset_stale_approvals(root) == []
    assert path.read_text(encoding="utf-8") == before


def _passage_root(tmp_path: Path) -> Path:
    (tmp_path / "passages").mkdir()
    shutil.copy(
        content_root() / "passages" / "linear_equations.yaml",
        tmp_path / "passages" / "linear_equations.yaml",
    )
    return tmp_path


def _approve_passage(root: Path, passage_id: str) -> None:
    path = root / "passages" / "linear_equations.yaml"
    passage = next(p for p in load_passages(root) if p.id == passage_id)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    row = next(r for r in data["passages"] if r["id"] == passage_id)
    row.update(status="approved", reviewer="curriculum.lead", approved_hash=passage_hash(passage))
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def test_editing_an_approved_passage_resets_only_that_passage(tmp_path: Path) -> None:
    root = _passage_root(tmp_path)
    _approve_passage(root, "PSG.LIN1.INVERSE.1")
    _approve_passage(root, "PSG.LIN1.ONE_STEP.1")
    assert reset_stale_approvals(root) == []
    path = root / "passages" / "linear_equations.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    row = next(r for r in data["passages"] if r["id"] == "PSG.LIN1.INVERSE.1")
    row["text"] = row["text"] + " Edited."
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    warnings = reset_stale_approvals(root)
    assert len(warnings) == 1 and "PSG.LIN1.INVERSE.1" in warnings[0]
    status = {p.id: p.status for p in load_passages(root)}
    assert status["PSG.LIN1.INVERSE.1"] == "draft"
    assert status["PSG.LIN1.ONE_STEP.1"] == "approved"


def test_the_passage_file_keeps_its_header_comment_after_a_reset(tmp_path: Path) -> None:
    root = _passage_root(tmp_path)
    _approve_passage(root, "PSG.LIN1.INVERSE.1")  # rewrites the file without its comment
    path = root / "passages" / "linear_equations.yaml"
    path.write_text("# Authored notes for the Ask feature.\n" + path.read_text("utf-8"), "utf-8")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["passages"][0]["text"] += " Edited."
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    path.write_text("# Authored notes for the Ask feature.\n" + body, encoding="utf-8")
    reset_stale_approvals(root)
    assert path.read_text(encoding="utf-8").startswith("# Authored notes for the Ask feature.")
