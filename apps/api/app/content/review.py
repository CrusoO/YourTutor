"""Teacher review sheet export / import."""

from __future__ import annotations

import csv
from html import escape
from pathlib import Path

import yaml

from app.config import settings
from app.content.generate import sample_instances
from app.content.schema import Item
from app.content.signatures import item_content_hash
from app.content.templates import GENERATOR_VERSION, template_hash
from app.content.validator import validate_bundle, validate_path

DEFAULT_REVIEWERS = ("curriculum.lead", "teacher.demo")


def reviewer_allowlist() -> set[str]:
    raw = settings.reviewer_allowlist
    if raw:
        return {part.strip() for part in raw.split(",") if part.strip()}
    return set(DEFAULT_REVIEWERS)


def export_sheet(root: Path, csv_path: Path, html_path: Path) -> int:
    report = validate_path(root)
    if report.bundle is None:
        raise RuntimeError("cannot export: " + "; ".join(report.errors))
    rows = [_row(item) for item in report.bundle.items]
    for template in report.bundle.templates:
        samples = sample_instances(template, seed=1, n=10)
        sample_text = " || ".join(
            f"{item.stem.en} → {item.answer.sympy}" for item in samples
        )
        rows.append(
            {
                "item_id": template.id,
                "kind": "template",
                "skill": template.skill_id,
                "stem": sample_text,
                "answer": "",
                "hint_1": "",
                "hint_2": "",
                "hint_3": "",
                "misconception_notes": template.structure,
                "solution_steps": f"samples={len(samples)} generator={GENERATOR_VERSION}",
                "approve": "",
                "comment": "",
                "corrected_text": "",
            }
        )
    _write_csv(csv_path, rows)
    _write_html(html_path, rows)
    return len(rows)


def import_sheet(csv_path: Path, root: Path, reviewer_id: str) -> list[str]:
    if reviewer_id not in reviewer_allowlist():
        raise PermissionError(f"{reviewer_id} is not an allowlisted reviewer")
    report = validate_path(root)
    if report.bundle is None:
        raise RuntimeError("cannot import: " + "; ".join(report.errors))
    items = {item.id: item for item in report.bundle.items}
    templates = {tpl.id: tpl for tpl in report.bundle.templates}
    approved: list[str] = []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("approve") or "").strip().upper() != "Y":
                continue
            template = templates.get(row["item_id"])
            if template is not None or row.get("kind") == "template":
                if template is None:
                    continue
                template.status = type(template.status)("approved")
                template.reviewed_by = reviewer_id
                template.content_hash = template_hash(template)
                check = validate_bundle(report.bundle)
                if not check.ok:
                    template.status = type(template.status)("draft")
                    template.reviewed_by = None
                    template.content_hash = None
                    continue
                _write_template(root, template)
                for item in report.bundle.items:
                    if item.template_id != template.id:
                        continue
                    if (
                        item.template_hash == template.content_hash
                        and item.generator_version == GENERATOR_VERSION
                    ):
                        item.status = type(item.status)("approved")
                        item.reviewed_by = reviewer_id
                        item.content_hash = item_content_hash(item)
                        _write_item(root, item)
                        approved.append(item.id)
                approved.append(template.id)
                continue
            item = items.get(row["item_id"])
            if item is None:
                continue
            item.status = type(item.status)("approved")
            item.reviewed_by = reviewer_id
            item.content_hash = item_content_hash(item)
            check = validate_bundle(report.bundle)
            if not check.ok:
                item.status = type(item.status)("draft")
                item.reviewed_by = None
                item.content_hash = None
                continue
            _write_item(root, item)
            approved.append(item.id)
    return approved


def _row(item: Item) -> dict[str, str]:
    hints = {h.level: h.en for h in item.hints}
    notes = ", ".join(rule.id for rule in item.misconception_rules)
    return {
        "item_id": item.id,
        "kind": "item",
        "skill": item.primary_skill,
        "stem": item.stem.en,
        "answer": item.answer.sympy,
        "hint_1": hints.get(1, ""),
        "hint_2": hints.get(2, ""),
        "hint_3": hints.get(3, ""),
        "misconception_notes": notes,
        "solution_steps": " | ".join(step.en for step in item.solution_steps),
        "approve": "",
        "comment": "",
        "corrected_text": "",
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_html(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cells = "".join(
        "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row.values()) + "</tr>"
        for row in rows
    )
    header = "".join(f"<th>{escape(key)}</th>" for key in (rows[0].keys() if rows else []))
    path.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Review sheet</title>"
        "<style>td,th{border:1px solid #444;padding:4px;font-size:12px}"
        "table{border-collapse:collapse}</style></head><body>"
        f"<table><thead><tr>{header}</tr></thead><tbody>{cells}</tbody></table>"
        "</body></html>",
        encoding="utf-8",
    )


def _write_item(root: Path, item: Item) -> None:
    for path in (root / "items").rglob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("id") != item.id:
            continue
        data["status"] = "approved"
        data["reviewed_by"] = item.reviewed_by
        data["content_hash"] = item.content_hash
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return
    raise FileNotFoundError(item.id)


def _write_template(root: Path, template) -> None:  # noqa: ANN001
    for path in (root / "templates").rglob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("id") != template.id:
            continue
        data["status"] = "approved"
        data["reviewed_by"] = template.reviewed_by
        data["content_hash"] = template.content_hash
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return
    raise FileNotFoundError(template.id)
