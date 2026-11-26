"""The private output folder: manifest, page cache and per-stage files (all private)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.bookcheck.settings import (
    COMBINED_SCIENCE_CLASSES,
    SCIENCE_PARTS,
    Settings,
)

STAGE_DIRS = ("cache", "toc", "coverage", "facts", "findings", "overlap")


def ensure_out(settings: Settings) -> None:
    for name in STAGE_DIRS:
        (settings.out_dir / name).mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
    tmp.replace(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


@dataclass(frozen=True)
class Book:
    sha: str
    file: str
    grade: int
    subject: str
    pages: int


def load_books(settings: Settings) -> list[Book]:
    manifest = read_json(settings.out_dir / "manifest.json", {"books": []})
    books = []
    for row in manifest.get("books", []):
        if row.get("status", "ok") != "ok":
            continue
        books.append(
            Book(row["sha"], row.get("file", ""), int(row["class"]), row["subject"], row["pages"])
        )
    return books


def books_for(books: list[Book], grade: int, subject: str) -> list[Book]:
    """Books of this class and subject. A combined science book (classes 9, 10) serves the three
    science subjects."""
    out = []
    for book in books:
        if book.grade != grade:
            continue
        if book.subject == subject:
            out.append(book)
        elif (
            book.subject == "science"
            and subject in SCIENCE_PARTS
            and grade in COMBINED_SCIENCE_CLASSES
        ):
            out.append(book)
    return out


def iter_pages(settings: Settings, sha: str) -> Iterator[tuple[int, str]]:
    """Stream (page number, text) one page at a time."""
    path = settings.out_dir / "cache" / sha / "pages.jsonl"
    if not path.is_file():
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                yield int(row["p"]), row["t"]
