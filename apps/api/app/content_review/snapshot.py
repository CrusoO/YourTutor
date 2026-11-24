"""Build-time snapshot of what the review routes read from the content folder.

Parsing about 2,300 YAML files takes 15-20 seconds, which a short-lived serverless function would
pay on every cold start (and the content folder may not even be inside the deployed function). The
snapshot holds the validated items, the misconception titles, the Hindi strings each item carries
and the chapter each item belongs to, in one small gzip JSON file inside `apps/api`.

Which one is used (see `service.load_review_data`):
  * the content folder exists and its source signature equals the one recorded here: the snapshot;
  * the content folder exists and differs (or there is no snapshot): parse the YAML, as always;
  * the content folder does not exist (a deployed function without it): the snapshot is
    authoritative.

The source signature is content based (relative path plus SHA-256 of the text with line endings
normalised), so it is the same on Windows and Linux checkouts. It never changes what an item is:
items are stored with `model_dump` and loaded with `model_validate`, and a test proves every item
has the identical `item_content_hash` both ways.

Regenerate with `PYTHONPATH=. python scripts/write_review_snapshot.py`.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.content.factory_roots import content_roots
from app.content.schema import Item, Misconception, Overlay

SNAPSHOT_VERSION = 1
SNAPSHOT_PATH = Path(__file__).resolve().parent / "review_snapshot.json.gz"
UNMAPPED_ID = "unmapped"
_FOLDERS = ("items", "misconceptions", "overlays")


@dataclass(frozen=True)
class Chapter:
    """One filter group. `in_curriculum` is False when no curriculum entry names the chapter."""

    chapter_id: str
    grade: int | None
    subject: str | None
    title: str
    in_curriculum: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "grade": self.grade,
            "subject": self.subject,
            "title": self.title,
            "in_curriculum": self.in_curriculum,
        }


@dataclass(frozen=True)
class ReviewData:
    items: list[Item]
    labels: dict[str, str]
    # item id -> Hindi strings; None means "not known, read the YAML" (the YAML path)
    hindi: dict[str, dict[str, Any]] | None
    chapters: dict[str, Chapter]  # chapter id -> chapter
    item_chapter: dict[str, str]  # item id -> chapter id
    source: str  # "snapshot" or "yaml"


def _folder_files(root: Path) -> list[Path]:
    found: dict[str, Path] = {}
    for base in content_roots(root):
        for name in _FOLDERS:
            for path in sorted((base / name).rglob("*.yaml")):
                found[path.relative_to(root).as_posix()] = path
    curricula = root / "curricula"
    if curricula.is_dir():
        for path in sorted(curricula.glob("*/curriculum.yaml")):
            found[path.relative_to(root).as_posix()] = path
    return [found[key] for key in sorted(found)]


def source_signature(root: Path) -> str:
    """SHA-256 over every file the snapshot is built from: relative path and normalised text."""
    digest = hashlib.sha256()
    for path in _folder_files(root):
        text = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(text).digest())
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    return data


def hindi_of(raw: dict[str, Any]) -> dict[str, Any]:
    """The Hindi strings an item's YAML carries (same rule as `service.hindi_texts`)."""
    from app.content.locale import is_missing_translation

    def pick(node: Any) -> str | None:
        value = node.get("hi") if isinstance(node, dict) else None
        return None if is_missing_translation(value) else str(value)

    options = {str(o.get("id")): pick(o) for o in raw.get("options") or [] if isinstance(o, dict)}
    return {"stem": pick(raw.get("stem")), "options": {k: v for k, v in options.items() if v}}


def chapter_map(
    root: Path, overlays: list[Overlay], items: list[Item]
) -> tuple[dict[str, Chapter], dict[str, str]]:
    """Chapter of each item: its first skill that an overlay lists names the overlay, and the
    curriculum entry with that overlay id gives class, subject and title. A chapter with no
    curriculum entry falls back to the overlay (class from `grade`, subject from the overlay id,
    title from the chapter key) and is marked `in_curriculum: False`. An item no overlay lists goes
    to the `unmapped` group. Deterministic: overlays are tried in id order."""
    curriculum: dict[str, tuple[int | None, str | None, str]] = {}
    for path in sorted((root / "curricula").glob("*/curriculum.yaml")):
        data = _read(path)
        for book in data.get("books") or []:
            for chapter in book.get("chapters") or []:
                key = str(chapter.get("overlay_id") or chapter.get("id"))
                title = (chapter.get("titles") or {}).get("en") or str(chapter.get("id"))
                curriculum[key] = (book.get("grade"), book.get("subject"), str(title))
    by_skill: dict[str, str] = {}
    chapters: dict[str, Chapter] = {}
    for overlay in sorted(overlays, key=lambda o: o.id):
        if overlay.id in curriculum:
            grade, subject, title = curriculum[overlay.id]
            chapters[overlay.id] = Chapter(overlay.id, grade, subject, title, True)
        else:
            parts = overlay.id.split(".")
            subject = parts[2] if len(parts) >= 4 else None
            title = overlay.chapter.replace("_", " ").strip().capitalize()
            chapters[overlay.id] = Chapter(overlay.id, overlay.grade, subject, title, False)
        for skill in overlay.skill_ids:
            by_skill.setdefault(skill, overlay.id)
    item_chapter: dict[str, str] = {}
    for item in items:
        chapter_id = next((by_skill[s] for s in item.skill_ids if s in by_skill), UNMAPPED_ID)
        item_chapter[item.id] = chapter_id
    if UNMAPPED_ID in item_chapter.values():
        chapters[UNMAPPED_ID] = Chapter(UNMAPPED_ID, None, None, "Not in any chapter", False)
    return chapters, item_chapter


def build(root: Path) -> dict[str, Any]:
    """The snapshot as a plain dict, deterministic: sorted, no timestamps."""
    paths = sorted(p for base in content_roots(root) for p in (base / "items").rglob("*.yaml"))
    items: list[Item] = []
    hindi: dict[str, dict[str, Any]] = {}
    for path in paths:
        raw = _read(path)
        item = Item.model_validate(raw)
        items.append(item)
        found = hindi_of(raw)
        if found["stem"] or found["options"]:
            hindi[item.id] = found
    items.sort(key=lambda i: i.id)
    misconception_paths = [
        p for base in content_roots(root) for p in sorted((base / "misconceptions").rglob("*.yaml"))
    ]
    labels = {}
    for path in misconception_paths:
        m = Misconception.model_validate(_read(path))
        labels[m.id] = m.title.en
    overlays = [
        Overlay.model_validate(_read(p))
        for base in content_roots(root)
        for p in sorted((base / "overlays").rglob("*.yaml"))
    ]
    chapters, item_chapter = chapter_map(root, overlays, items)
    return {
        "version": SNAPSHOT_VERSION,
        "source_signature": source_signature(root),
        "items": [i.model_dump(mode="json", by_alias=True) for i in items],
        "labels": dict(sorted(labels.items())),
        "hindi": dict(sorted(hindi.items())),
        "chapters": {k: chapters[k].as_dict() for k in sorted(chapters)},
        "item_chapter": dict(sorted(item_chapter.items())),
    }


def render(data: dict[str, Any]) -> bytes:
    blob = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return gzip.compress(blob.encode("utf-8"), compresslevel=9, mtime=0)


def write(path: Path, data: dict[str, Any]) -> None:
    path.write_bytes(render(data))


def read(path: Path) -> dict[str, Any] | None:
    """The snapshot, or None when the file is missing, unreadable or from another version."""
    try:
        data = json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
    except (OSError, ValueError, EOFError):
        return None
    if not isinstance(data, dict) or data.get("version") != SNAPSHOT_VERSION:
        return None
    return data


def to_review_data(data: dict[str, Any]) -> ReviewData:
    items = [Item.model_validate(raw) for raw in data["items"]]
    chapters = {
        key: Chapter(
            c["chapter_id"], c["grade"], c["subject"], c["title"], bool(c["in_curriculum"])
        )
        for key, c in data["chapters"].items()
    }
    return ReviewData(
        items=items,
        labels=dict(data["labels"]),
        hindi=dict(data["hindi"]),
        chapters=chapters,
        item_chapter=dict(data["item_chapter"]),
        source="snapshot",
    )


def from_bundle(
    root: Path, items: list[Item], labels: dict[str, str], overlays: list[Overlay]
) -> ReviewData:
    """The YAML path: the loaded bundle plus the chapter map (Hindi is read from the files)."""
    chapters, item_chapter = chapter_map(root, overlays, items)
    return ReviewData(items, labels, None, chapters, item_chapter, "yaml")
