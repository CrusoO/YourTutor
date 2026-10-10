"""Approval hashes for lessons (with their scenes and widgets) and passages.

Items and templates already reset to draft when approved content changes (their hash is stored
with the approval). This module gives lessons and passages the same rule: an approved object
carries `reviewed_by` and the hash of its content at approval time; if the content changes, or the
hash is missing, the next `content validate` or `content load` turns it back into a draft and
rewrites the file. A scene or a widget is part of its lesson, so editing either changes the
lesson's hash.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from app.ask.passages import Passage, passages_dir
from app.lessons.schema import Lesson

APPROVAL_KEYS = ("status", "reviewed_by", "content_hash", "approved_hash", "reviewer")


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _english_only(node: Any) -> Any:
    """Drop every language but English from localized text, so a translation never changes the
    hash of the English the reviewer approved (translations have their own review)."""
    if isinstance(node, dict):
        if isinstance(node.get("en"), str):
            return {"en": node["en"]}
        return {key: _english_only(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_english_only(value) for value in node]
    return node


def lesson_hash(lesson: Lesson) -> str:
    data = _english_only(json.loads(lesson.model_dump_json(by_alias=True, exclude_none=True)))
    for key in APPROVAL_KEYS:
        data.pop(key, None)
    return _digest(data)


def passage_hash(passage: Passage) -> str:
    data = json.loads(passage.model_dump_json(exclude_none=True))
    for key in APPROVAL_KEYS:
        data.pop(key, None)
    return _digest(data)


def _header(path: Path) -> str:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            lines.append(line)
        else:
            break
    return "\n".join(lines) + "\n" if lines else ""


def _dump(path: Path, header: str, data: Any) -> None:
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    path.write_text(header + body, encoding="utf-8")


def _reset(row: dict[str, Any], reviewer_key: str, hash_key: str) -> None:
    row["status"] = "draft"
    row[reviewer_key] = None
    row[hash_key] = None


def reset_stale_approvals(root: Path, *, write: bool = True) -> list[str]:
    """Turn approved lessons and passages whose content no longer matches their hash back into
    drafts. Returns one warning per object reset."""
    warnings: list[str] = []
    for path in sorted((root / "lessons").glob("*.yaml")) if (root / "lessons").is_dir() else []:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("status") != "approved":
            continue
        try:
            lesson = Lesson.model_validate(data)
        except ValueError:
            continue  # a broken lesson is reported by the lesson validator
        if not lesson.reviewed_by or lesson.content_hash != lesson_hash(lesson):
            _reset(data, "reviewed_by", "content_hash")
            warnings.append(f"{lesson.id} approved lesson changed; reset to draft (hash mismatch)")
            if write:
                _dump(path, _header(path), data)
    folder = passages_dir(root)
    for path in sorted(folder.glob("*.yaml")) if folder.is_dir() else []:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        rows = data.get("passages") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            continue
        changed = False
        for row in rows:
            if not isinstance(row, dict) or row.get("status") != "approved":
                continue
            try:
                passage = Passage.model_validate(row)
            except ValueError:
                continue
            if not passage.reviewer or passage.approved_hash != passage_hash(passage):
                _reset(row, "reviewer", "approved_hash")
                changed = True
                warnings.append(
                    f"{passage.id} approved passage changed; reset to draft (hash mismatch)"
                )
        if changed and write:
            _dump(path, _header(path), data)
    return warnings
