"""Teacher review sheet export / import."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

import yaml

from app.ask.passages import Passage, load_passages, passages_dir
from app.config import settings
from app.content.approval import _dump, _header, lesson_hash, passage_hash
from app.content.generate import sample_instances
from app.content.schema import Item
from app.content.signatures import item_content_hash
from app.content.templates import GENERATOR_VERSION, template_hash
from app.content.validator import validate_bundle, validate_path
from app.lessons.loader import load_lessons
from app.lessons.schema import Lesson

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
        sample_text = " || ".join(f"{item.stem.en} → {item.answer.sympy}" for item in samples)
        rows.append(
            {
                "item_id": template.id,
                "kind": "template",
                "content_hash": template_hash(template),
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
    rows.extend(_lesson_row(lesson) for lesson in load_lessons(root).values())
    rows.extend(_passage_row(passage) for passage in load_passages(root))
    _write_csv(csv_path, rows)
    _write_html(html_path, rows)
    return len(rows)


@dataclass
class ImportReport:
    approved: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)  # content changed since the sheet was exported
    refused: list[str] = field(default_factory=list)  # failed validation or not found


def import_sheet(csv_path: Path, root: Path, reviewer_id: str) -> list[str]:
    return import_sheet_report(csv_path, root, reviewer_id).approved


def import_sheet_report(csv_path: Path, root: Path, reviewer_id: str) -> ImportReport:
    """Approve the rows marked Y. A row is approved only if its `content_hash` still matches the
    object on disk, so a sheet reviewed against old text can never approve newer text."""
    if reviewer_id not in reviewer_allowlist():
        raise PermissionError(f"{reviewer_id} is not an allowlisted reviewer")
    report = validate_path(root)
    if report.bundle is None:
        raise RuntimeError("cannot import: " + "; ".join(report.errors))
    items = {item.id: item for item in report.bundle.items}
    templates = {tpl.id: tpl for tpl in report.bundle.templates}
    lessons = load_lessons(root)
    passages = {p.id: p for p in load_passages(root)}
    out = ImportReport()
    pending: list[Item] = []
    pending_templates: list = []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if "content_hash" not in (reader.fieldnames or []):
            raise RuntimeError("the sheet has no content_hash column; export it again")
        rows = list(reader)
    for row in rows:
        if (row.get("approve") or "").strip().upper() != "Y":
            continue
        ident, kind, seen = row["item_id"], row.get("kind") or "item", row.get("content_hash")
        if kind == "template" or ident in templates:
            template = templates.get(ident)
            if template is None:
                out.refused.append(ident)
            elif seen != template_hash(template):
                out.stale.append(ident)
            else:
                pending_templates.append(template)
        elif kind == "lesson":
            lesson = lessons.get(ident)
            if lesson is None:
                out.refused.append(ident)
            elif seen != lesson_hash(lesson):
                out.stale.append(ident)
            else:
                _approve_lesson(root, lesson, reviewer_id)
                out.approved.append(ident)
        elif kind == "passage":
            passage = passages.get(ident)
            if passage is None:
                out.refused.append(ident)
            elif seen != passage_hash(passage):
                out.stale.append(ident)
            else:
                _approve_passage(root, passage, reviewer_id)
                out.approved.append(ident)
        else:
            target = items.get(ident)
            if target is None:
                out.refused.append(ident)
            elif seen != item_content_hash(target):
                out.stale.append(ident)
            else:
                pending.append(target)
    _approve_templates(report.bundle, pending_templates, root, reviewer_id, out)
    _approve_items(report.bundle, pending, root, reviewer_id, out)
    return out


def _approve_templates(
    bundle, pending: list, root: Path, reviewer_id: str, out: ImportReport
) -> None:  # noqa: ANN001
    """Approve many templates (and the items generated from them) with one validation pass."""
    if len(pending) < 2:
        for template in pending:
            _approve_template(bundle, template, root, reviewer_id, out)
        return
    for template in pending:
        template.status = type(template.status)("approved")
        template.reviewed_by = reviewer_id
        template.content_hash = template_hash(template)
    cascaded = []
    for template in pending:
        for item in bundle.items:
            if (
                item.template_id == template.id
                and item.template_hash == template.content_hash
                and item.generator_version == GENERATOR_VERSION
            ):
                cascaded.append((item, item.status, item.reviewed_by, item.content_hash))
                item.status = type(item.status)("approved")
                item.reviewed_by = reviewer_id
                item.content_hash = item_content_hash(item)
    if validate_bundle(bundle).ok:
        for template in pending:
            _write_template(root, template)
            out.approved.append(template.id)
        for item, *_ in cascaded:
            _write_item(root, item)
            out.approved.append(item.id)
        return
    for item, status, who, digest in cascaded:
        item.status, item.reviewed_by, item.content_hash = status, who, digest
    for template in pending:
        template.status = type(template.status)("draft")
        template.reviewed_by = None
        template.content_hash = None
    for template in pending:
        _approve_template(bundle, template, root, reviewer_id, out)


def _approve_items(
    bundle, pending: list[Item], root: Path, reviewer_id: str, out: ImportReport
) -> None:  # noqa: ANN001
    """Approve many items with one validation pass; if it fails, one by one to find the culprit."""
    if not pending:
        return
    for target in pending:
        target.status = type(target.status)("approved")
        target.reviewed_by = reviewer_id
        target.content_hash = item_content_hash(target)
    if validate_bundle(bundle).ok:
        for target in pending:
            _write_item(root, target)
            out.approved.append(target.id)
        return
    for target in pending:
        target.status = type(target.status)("draft")
        target.reviewed_by = None
        target.content_hash = None
    for target in pending:
        _approve_item(bundle, target, root, reviewer_id, out)


def _approve_item(bundle, target: Item, root: Path, reviewer_id: str, out: ImportReport) -> None:  # noqa: ANN001
    target.status = type(target.status)("approved")
    target.reviewed_by = reviewer_id
    target.content_hash = item_content_hash(target)
    if not validate_bundle(bundle).ok:
        target.status = type(target.status)("draft")
        target.reviewed_by = None
        target.content_hash = None
        out.refused.append(target.id)
        return
    _write_item(root, target)
    out.approved.append(target.id)


def _approve_template(bundle, template, root: Path, reviewer_id: str, out: ImportReport) -> None:  # noqa: ANN001
    template.status = type(template.status)("approved")
    template.reviewed_by = reviewer_id
    template.content_hash = template_hash(template)
    if not validate_bundle(bundle).ok:
        template.status = type(template.status)("draft")
        template.reviewed_by = None
        template.content_hash = None
        out.refused.append(template.id)
        return
    _write_template(root, template)
    for item in bundle.items:
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
            out.approved.append(item.id)
    out.approved.append(template.id)


def _approve_lesson(root: Path, lesson: Lesson, reviewer_id: str) -> None:
    for path in sorted((root / "lessons").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("id") == lesson.id:
            data.update(
                status="approved", reviewed_by=reviewer_id, content_hash=lesson_hash(lesson)
            )
            _dump(path, _header(path), data)
            return
    raise FileNotFoundError(lesson.id)


def _approve_passage(root: Path, passage: Passage, reviewer_id: str) -> None:
    for path in sorted(passages_dir(root).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for row in data.get("passages", []):
            if isinstance(row, dict) and row.get("id") == passage.id:
                row.update(
                    status="approved", reviewer=reviewer_id, approved_hash=passage_hash(passage)
                )
                _dump(path, _header(path), data)
                return
    raise FileNotFoundError(passage.id)


def _row(item: Item) -> dict[str, str]:
    hints = {h.level: h.en for h in item.hints}
    notes = ", ".join(rule.id for rule in item.misconception_rules)
    return {
        "item_id": item.id,
        "kind": "item",
        "content_hash": item_content_hash(item),
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


def _en_strings(node: Any) -> list[str]:
    """Every English string under an `en` key, in reading order."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "en" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_en_strings(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_en_strings(value))
    return found


def _blank_row(item_id: str, kind: str, digest: str, skill: str) -> dict[str, str]:
    return {
        "item_id": item_id,
        "kind": kind,
        "content_hash": digest,
        "skill": skill,
        "stem": "",
        "answer": "",
        "hint_1": "",
        "hint_2": "",
        "hint_3": "",
        "misconception_notes": "",
        "solution_steps": "",
        "approve": "",
        "comment": "",
        "corrected_text": "",
    }


def _lesson_row(lesson: Lesson) -> dict[str, str]:
    """A lesson is reviewed with its scenes and widgets: all their English text is in one row."""
    row = _blank_row(lesson.id, "lesson", lesson_hash(lesson), lesson.skill_id)
    data = lesson.model_dump(mode="json", by_alias=True, exclude_none=True)
    row["stem"] = lesson.title.en
    row["misconception_notes"] = f"source={lesson.source_ref}; scenes={len(lesson.scenes())}"
    row["solution_steps"] = " | ".join(_en_strings(data["beats"]))
    return row


def _passage_row(passage: Passage) -> dict[str, str]:
    row = _blank_row(passage.id, "passage", passage_hash(passage), ",".join(passage.skill_ids))
    row["stem"] = passage.text.strip()
    row["misconception_notes"] = (
        f"{passage.chapter_id}.{passage.section_key}; {passage.source_type}; "
        f"licence={passage.licence_status}"
    )
    return row


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
