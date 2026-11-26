"""Our side: syllabus maps and our items (drafts and compiled), read tolerantly from YAML.

Nothing here validates content; the authoring and content tools do that. This only reads enough
to compare against a book.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.bookcheck.settings import BOARD_DIR


@dataclass
class OurItem:
    id: str
    topic: str
    chapter: str
    stem: str
    correct: str
    wrong: list[str]
    texts: dict[str, str] = field(default_factory=dict)  # field name -> text, for the copy check


@dataclass
class Topic:
    key: str
    title: str
    chapter_key: str


@dataclass
class Chapter:
    key: str
    title: str
    confidence: str
    topics: list[Topic]


def load_syllabus(content_root: Path, grade: int, subject: str) -> list[Chapter] | None:
    path = content_root / "syllabus" / BOARD_DIR / str(grade) / f"{subject}.yaml"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    chapters = []
    for raw in data.get("chapters", []):
        key = str(raw.get("key", ""))
        topics = [
            Topic(str(t.get("key", "")), str(t.get("title", "")), key)
            for t in raw.get("topics", [])
        ]
        chapters.append(
            Chapter(key, str(raw.get("title", "")), raw.get("confidence", "high"), topics)
        )
    return chapters


def _en(value: Any) -> str:
    if isinstance(value, dict):
        return _en(value.get("en", ""))
    return "" if value is None else str(value)


def _placeholder(text: str) -> bool:
    return text.startswith("<") and text.endswith(">")


def _strings(value: Any, path: str = "") -> list[tuple[str, str]]:
    """Every English string in a structure, with a dotted field path. Translations are skipped."""
    out: list[tuple[str, str]] = []
    if isinstance(value, str):
        if value.strip() and not _placeholder(value):
            out.append((path, value))
    elif isinstance(value, dict):
        if "en" in value and isinstance(value["en"], str):
            out.extend(_strings(value["en"], path))
        else:
            for key, sub in value.items():
                if key in ("id", "skill_ids", "type", "pool", "role", "status", "reviewed_by"):
                    continue
                out.extend(_strings(sub, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, sub in enumerate(value):
            out.extend(_strings(sub, f"{path}[{index}]"))
    return out


def _draft_items(path: Path) -> list[OurItem]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    chapter = str(data.get("chapter", ""))
    items = []
    for index, raw in enumerate(data.get("items", []) or []):
        wrong = [_en(w.get("text") if isinstance(w, dict) else w) for w in raw.get("wrong") or []]
        items.append(
            OurItem(
                id=f"{path.stem}#{index + 1}",
                topic=str(raw.get("topic", "")),
                chapter=chapter,
                stem=_en(raw.get("stem")),
                correct=_en(raw.get("correct")),
                wrong=[w for w in wrong if w],
                texts=dict(_strings({k: v for k, v in raw.items() if k != "topic"})),
            )
        )
    return items


def _compiled_item(path: Path) -> list[OurItem]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return []
    answer = raw.get("answer") or raw.get("correct") or ""
    if isinstance(answer, dict):
        accept = answer.get("accept") or [answer.get("text") or answer.get("sympy") or ""]
        correct = _en(accept[0]) if accept else ""
    else:
        correct = _en(answer)
    options = raw.get("wrong") or raw.get("distractors") or []
    wrong = [_en(w.get("text") if isinstance(w, dict) else w) for w in options]
    skills = raw.get("skill_ids") or []
    topic = str(raw.get("topic") or (skills[0] if skills else ""))
    return [
        OurItem(
            id=str(raw.get("id") or path.stem),
            topic=topic,
            chapter=str(raw.get("chapter", "")),
            stem=_en(raw.get("stem")),
            correct=correct,
            wrong=[w for w in wrong if w],
            texts=dict(_strings(raw)),
        )
    ]


def load_items(content_root: Path, grade: int, subject: str, which: str = "all") -> list[OurItem]:
    items: list[OurItem] = []
    if which in ("drafts", "all"):
        folder = content_root / "authoring" / "drafts" / str(grade) / subject
        for path in sorted(folder.glob("*.yaml")) if folder.is_dir() else []:
            items.extend(_draft_items(path))
    if which in ("compiled", "all"):
        folder = content_root / BOARD_DIR / str(grade) / subject / "items"
        for path in sorted(folder.rglob("*.yaml")) if folder.is_dir() else []:
            items.extend(_compiled_item(path))
    return items


def discover_scopes(content_root: Path) -> list[tuple[int, str]]:
    """(class, subject) pairs that have drafts or compiled items."""
    found: set[tuple[int, str]] = set()
    for pattern in ("authoring/drafts/*/*/*.yaml", f"{BOARD_DIR}/*/*/items/**/*.yaml"):
        for path in content_root.glob(pattern):
            parts = path.relative_to(content_root).parts
            grade_index = 2 if parts[0] == "authoring" else 1
            if parts[grade_index].isdigit():
                found.add((int(parts[grade_index]), parts[grade_index + 1]))
    return sorted(found)
