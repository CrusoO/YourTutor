from __future__ import annotations

import csv
from pathlib import Path

from app.content.review import export_sheet, import_sheet
from app.content.signatures import item_content_hash
from app.content.validator import load_bundle, validate_path
from tests.content.conftest import content_root  # noqa: F401


def test_review_export_import_and_hash_reset(content_root: Path, tmp_path: Path) -> None:
    csv_path = tmp_path / "sheet.csv"
    html_path = tmp_path / "sheet.html"
    count = export_sheet(content_root, csv_path, html_path)
    assert count >= 5
    assert html_path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    rows[0]["approve"] = "Y"
    target = rows[0]["item_id"]
    out = tmp_path / "approved.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    approved = import_sheet(out, content_root, "teacher.demo")
    assert target in approved
    bundle = load_bundle(content_root)
    item = next(row for row in bundle.items if row.id == target)
    assert item.status.value == "approved"
    assert item.reviewed_by == "teacher.demo"
    assert item.content_hash == item_content_hash(item)

    yaml_path = None
    text = ""
    for path in (content_root / "items").rglob("*.yaml"):
        raw = path.read_text(encoding="utf-8")
        if f"id: {target}" in raw:
            yaml_path = path
            text = raw
            break
    assert yaml_path is not None
    yaml_path.write_text(text.replace(item.stem.en, item.stem.en + " edited"), encoding="utf-8")
    report = validate_path(content_root)
    assert any("reset to draft" in w for w in report.warnings)
    changed = next(row for row in report.bundle.items if row.id == target)
    assert changed.status.value == "draft"
    assert changed.reviewed_by is None
    reloaded = load_bundle(content_root)
    disk = next(row for row in reloaded.items if row.id == target)
    assert disk.status.value == "draft"


def test_unknown_reviewer_rejected(content_root: Path, tmp_path: Path) -> None:
    csv_path = tmp_path / "sheet.csv"
    export_sheet(content_root, csv_path, tmp_path / "s.html")
    try:
        import_sheet(csv_path, content_root, "stranger")
        raise AssertionError("should reject")
    except PermissionError:
        pass
