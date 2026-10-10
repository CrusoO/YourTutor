"""G8 step 3: the locale review workflow. A human fills and approves; machines never do."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest
import yaml

from app.content.__main__ import main
from app.content.approval import lesson_hash
from app.content.locale_review import (
    SIDECAR,
    en_hash,
    export_locale_review,
    import_locale_review,
    locale_report,
)
from app.lessons.loader import load_lessons
from app.registries.paths import content_root as shipped_root

REVIEWER = "teacher.demo"
COPY = "copy/encouragement.yaml"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "copy").mkdir()
    shutil.copy(shipped_root() / COPY, tmp_path / COPY)
    (tmp_path / "lessons").mkdir()
    shutil.copy(shipped_root() / "lessons" / "brackets.yaml", tmp_path / "lessons")
    return tmp_path


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _first(root: Path, tmp_path: Path, locale: str = "ne") -> tuple[Path, list[dict[str, str]]]:
    sheet = tmp_path / "ne.csv"
    export_locale_review(root, locale, sheet)
    return sheet, _rows(sheet)


def test_the_export_lists_every_string_that_lacks_a_real_translation(
    root: Path, tmp_path: Path
) -> None:
    _, rows = _first(root, tmp_path)
    assert rows and all(r["status"] == "missing" for r in rows)
    assert all(r["origin"] == "human" and r["approve"] == "" for r in rows)
    files = {r["file"] for r in rows}
    assert files == {COPY, "lessons/brackets.yaml"}
    assert all(r["en_hash"] == en_hash(r["en"]) for r in rows)
    lesson_row = next(r for r in rows if r["file"].startswith("lessons"))
    assert lesson_row["object_id"] == "LESSON.LIN1.BRACKETS"


def test_a_reviewer_fills_and_approves_a_string_and_it_leaves_the_sheet(
    root: Path, tmp_path: Path
) -> None:
    sheet, rows = _first(root, tmp_path)
    target = next(r for r in rows if r["file"] == COPY)
    target.update(translation="काम जारी राख्नुभयो।", approve="Y")
    _write(sheet, rows)
    result = import_locale_review(sheet, root, "ne", REVIEWER)
    assert len(result.approved) == 1 and not result.refused
    data = yaml.safe_load((root / COPY).read_text(encoding="utf-8"))
    assert data["variants"][0]["text"]["ne"] == "काम जारी राख्नुभयो।"
    assert data["variants"][0]["text"]["as"].startswith("<Assamese")  # other languages untouched
    ledger = yaml.safe_load((root / SIDECAR).read_text(encoding="utf-8"))
    entry = ledger[f"{COPY}#{target['path']}"]["ne"]
    assert entry["reviewed_by"] == REVIEWER and entry["en_hash"] == target["en_hash"]
    counts = locale_report(root, "ne")
    assert counts["approved"] == 1 and counts["missing"] == len(rows) - 1
    again = tmp_path / "again.csv"
    export_locale_review(root, "ne", again)
    assert len(_rows(again)) == len(rows) - 1


@pytest.mark.parametrize(
    ("origin", "translation", "why"),
    [
        ("machine", "some machine text", "machine drafts"),
        ("human", "", "no translation"),
        ("human", "<Nepali — to be filled by reviewer>", "no translation"),
    ],
)
def test_machine_drafts_blanks_and_placeholders_are_never_approved(
    root: Path, tmp_path: Path, origin: str, translation: str, why: str
) -> None:
    sheet, rows = _first(root, tmp_path)
    rows[0].update(origin=origin, translation=translation, approve="Y")
    _write(sheet, rows)
    result = import_locale_review(sheet, root, "ne", REVIEWER)
    assert result.approved == [] and why in result.refused[0]
    assert not (root / SIDECAR).exists()
    assert locale_report(root, "ne")["approved"] == 0


def test_a_change_to_the_english_text_makes_the_sheet_row_stale(root: Path, tmp_path: Path) -> None:
    sheet, rows = _first(root, tmp_path)
    first = next(r for r in rows if r["file"] == COPY)
    first.update(translation="अनुवाद", approve="Y")
    _write(sheet, rows)
    path = root / COPY
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["variants"][0]["text"]["en"] += " Changed."
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    result = import_locale_review(sheet, root, "ne", REVIEWER)
    assert result.approved == [] and "English text changed" in result.refused[0]


def test_changing_the_english_afterwards_makes_an_approved_translation_unreviewed(
    root: Path, tmp_path: Path
) -> None:
    sheet, rows = _first(root, tmp_path)
    first = next(r for r in rows if r["file"] == COPY)
    first.update(translation="अनुवाद", approve="Y")
    _write(sheet, rows)
    import_locale_review(sheet, root, "ne", REVIEWER)
    path = root / COPY
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["variants"][0]["text"]["en"] += " Changed."
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    counts = locale_report(root, "ne")
    assert counts["approved"] == 0 and counts["unreviewed"] == 1


def test_an_existing_translation_can_be_confirmed_without_retyping_it(
    root: Path, tmp_path: Path
) -> None:
    path = root / COPY
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["variants"][0]["text"]["ne"] = "पहिले नै लेखिएको"
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    sheet, rows = _first(root, tmp_path)
    row = next(r for r in rows if r["status"] == "unreviewed")
    row["approve"] = "Y"  # translation column left blank: confirm what is there
    _write(sheet, rows)
    assert len(import_locale_review(sheet, root, "ne", REVIEWER).approved) == 1
    assert locale_report(root, "ne")["approved"] == 1


def test_an_unlisted_reviewer_and_english_are_refused(root: Path, tmp_path: Path) -> None:
    sheet, rows = _first(root, tmp_path)
    rows[0].update(translation="x", approve="Y")
    _write(sheet, rows)
    with pytest.raises(PermissionError):
        import_locale_review(sheet, root, "ne", "stranger")
    with pytest.raises(ValueError):
        export_locale_review(root, "en", tmp_path / "en.csv")
    with pytest.raises(ValueError):
        export_locale_review(root, "xx", tmp_path / "xx.csv")


def test_translating_a_lesson_does_not_reset_the_approved_english(
    root: Path, tmp_path: Path
) -> None:
    lesson = next(iter(load_lessons(root).values()))
    before = lesson_hash(lesson)
    path = root / "lessons" / "brackets.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["title"]["ne"] = "कोष्ठक खोल्ने"
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    assert lesson_hash(next(iter(load_lessons(root).values()))) == before


def test_the_command_line_runs_the_workflow(root: Path, tmp_path: Path, capsys) -> None:
    sheet = tmp_path / "cli.csv"
    assert main(["export-locale-review", str(root), "--locale", "ne", "--csv", str(sheet)]) == 0
    rows = _rows(sheet)
    rows[0].update(translation="अनुवाद", approve="Y")
    _write(sheet, rows)
    assert (
        main(
            [
                "import-locale-review",
                str(sheet),
                str(root),
                "--locale",
                "ne",
                "--reviewer",
                REVIEWER,
            ]
        )
        == 0
    )
    assert main(["locale-status", str(root), "--locale", "ne"]) == 0
    assert "approved: 1" in capsys.readouterr().out
