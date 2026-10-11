"""G8 step 2: the review sheet covers lessons and passages and refuses stale rows."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest
import yaml

from app.ask.passages import load_passages
from app.content.review import export_sheet, import_sheet, import_sheet_report
from app.lessons.loader import load_lessons
from app.registries.paths import content_root as shipped_root

REVIEWER = "teacher.demo"


@pytest.fixture
def root(content_root: Path) -> Path:
    (content_root / "lessons").mkdir()
    shutil.copy(shipped_root() / "lessons" / "brackets.yaml", content_root / "lessons")
    (content_root / "passages").mkdir()
    shutil.copy(shipped_root() / "passages" / "linear_equations.yaml", content_root / "passages")
    return content_root


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _export(root: Path, tmp_path: Path) -> Path:
    sheet = tmp_path / "sheet.csv"
    export_sheet(root, sheet, tmp_path / "sheet.html")
    return sheet


def _mark(sheet: Path, *ids: str) -> None:
    rows = _rows(sheet)
    for row in rows:
        if row["item_id"] in ids:
            row["approve"] = "Y"
    _write(sheet, rows)


def test_every_row_carries_a_content_hash_and_lessons_and_passages_are_listed(
    root: Path, tmp_path: Path
) -> None:
    rows = _rows(_export(root, tmp_path))
    assert all(len(r["content_hash"]) == 64 for r in rows)
    kinds = {r["kind"] for r in rows}
    assert {"item", "lesson", "passage"} <= kinds
    lesson = next(r for r in rows if r["kind"] == "lesson")
    assert lesson["item_id"] == "LESSON.LIN1.BRACKETS"
    assert "3(x + 4)" in lesson["solution_steps"]  # the scene and beat text is on the sheet
    assert sum(r["kind"] == "passage" for r in rows) == len(load_passages(root))


def test_approving_a_lesson_row_writes_the_reviewer_and_hash(root: Path, tmp_path: Path) -> None:
    sheet = _export(root, tmp_path)
    _mark(sheet, "LESSON.LIN1.BRACKETS")
    report = import_sheet_report(sheet, root, REVIEWER)
    assert report.approved == ["LESSON.LIN1.BRACKETS"] and not report.stale
    lesson = load_lessons(root)["LESSON.LIN1.BRACKETS"]
    assert lesson.status.value == "approved" and lesson.reviewed_by == REVIEWER
    assert lesson.content_hash


def test_approving_a_passage_row_keeps_the_other_passages_as_they_were(
    root: Path, tmp_path: Path
) -> None:
    sheet = _export(root, tmp_path)
    _mark(sheet, "PSG.LIN1.INVERSE.1")
    assert import_sheet(sheet, root, REVIEWER) == ["PSG.LIN1.INVERSE.1"]
    status = {p.id: (p.status, p.reviewer) for p in load_passages(root)}
    assert status["PSG.LIN1.INVERSE.1"] == ("approved", REVIEWER)
    assert status["PSG.LIN1.ONE_STEP.1"] == ("draft", None)


def test_a_row_reviewed_against_old_text_cannot_approve_new_text(
    root: Path, tmp_path: Path
) -> None:
    sheet = _export(root, tmp_path)
    _mark(sheet, "PSG.LIN1.INVERSE.1", "LESSON.LIN1.BRACKETS", "ITEM.P0")
    path = root / "passages" / "linear_equations.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["passages"][0]["text"] += " Changed after the sheet was printed."
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    lesson_path = root / "lessons" / "brackets.yaml"
    lesson = yaml.safe_load(lesson_path.read_text(encoding="utf-8"))
    lesson["title"]["en"] = "A new title"
    lesson_path.write_text(yaml.safe_dump(lesson, sort_keys=False, allow_unicode=True), "utf-8")
    item_path = next(p for p in (root / "items").rglob("p0.yaml"))
    item = yaml.safe_load(item_path.read_text(encoding="utf-8"))
    item["stem"]["en"] += " (edited)"
    item_path.write_text(yaml.safe_dump(item, sort_keys=False, allow_unicode=True), "utf-8")

    report = import_sheet_report(sheet, root, REVIEWER)
    assert report.approved == []
    assert sorted(report.stale) == ["ITEM.P0", "LESSON.LIN1.BRACKETS", "PSG.LIN1.INVERSE.1"]
    assert load_lessons(root)["LESSON.LIN1.BRACKETS"].status.value == "draft"


def test_a_sheet_from_before_hashes_is_refused(root: Path, tmp_path: Path) -> None:
    sheet = _export(root, tmp_path)
    rows = _rows(sheet)
    for row in rows:
        del row["content_hash"]
    old = tmp_path / "old.csv"
    _write(old, rows)
    with pytest.raises(RuntimeError, match="content_hash"):
        import_sheet(old, root, REVIEWER)


def test_an_unlisted_reviewer_cannot_approve_a_lesson(root: Path, tmp_path: Path) -> None:
    sheet = _export(root, tmp_path)
    _mark(sheet, "LESSON.LIN1.BRACKETS")
    with pytest.raises(PermissionError):
        import_sheet(sheet, root, "stranger")
    assert load_lessons(root)["LESSON.LIN1.BRACKETS"].status.value == "draft"


def test_an_unknown_row_id_is_reported_not_silently_ignored(root: Path, tmp_path: Path) -> None:
    sheet = _export(root, tmp_path)
    rows = _rows(sheet)
    rows[0].update(item_id="ITEM.NOT.THERE", approve="Y")
    _write(sheet, rows)
    assert import_sheet_report(sheet, root, REVIEWER).refused == ["ITEM.NOT.THERE"]


def test_several_templates_are_approved_in_one_pass(root: Path, tmp_path: Path) -> None:
    source = yaml.safe_load((shipped_root() / "templates" / "tpl_one_add.yaml").read_text("utf-8"))
    for name, offset in (("A", 3), ("B", 5)):
        data = {**source, "id": f"TPL.T.{name}", "skill_id": "MATH.S1", "misconceptions": []}
        data["parameters"] = {"b": {"min": offset, "max": offset + 4}, "x": {"min": 2, "max": 18}}
        folder = root / "templates"
        folder.mkdir(exist_ok=True)
        (folder / f"t_{name}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    sheet = _export(root, tmp_path)
    _mark(sheet, "TPL.T.A", "TPL.T.B")
    report = import_sheet_report(sheet, root, REVIEWER)
    assert {"TPL.T.A", "TPL.T.B"} <= set(report.approved), report
    for name in ("A", "B"):
        data = yaml.safe_load((root / "templates" / f"t_{name}.yaml").read_text("utf-8"))
        assert data["status"] == "approved" and data["reviewed_by"] == REVIEWER
