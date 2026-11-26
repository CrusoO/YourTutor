"""toc: find chapters and sections in each cached book.

Order of trust: the PDF outline (bookmarks) first, else regex heuristics on page text. Heuristics
are noisy: running headers, contents pages and exercise numbering all look like headings. The
confidence field says how much to trust the result; check a few entries by eye.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.bookcheck.settings import Settings
from app.bookcheck.store import Book, iter_pages, load_books, write_json

CHAPTER = re.compile(r"^(chapter|unit|lesson)\s+(\d{1,2}|[ivxl]{1,5})\b[\s:.\-–]*(.*)$", re.I)
SECTION = re.compile(r"^(\d{1,2}\.\d{1,2})(?:\.\d{1,2})?[\s.)]+([A-Z][^\n]{2,70})$")
CAPS_MIN, CAPS_MAX = 4, 60
RUNNING_HEADER_PAGES = 4
FRONT_MATTER_PAGES = 12


def _is_caps_title(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    if not (CAPS_MIN <= len(line) <= CAPS_MAX) or len(letters) < 4:
        return False
    if not all(c.isupper() for c in letters):
        return False
    return len(line.split()) <= 8 and not any(c in line for c in "=+")


def headings_in_page(text: str) -> list[tuple[int, str, str]]:
    """(level, kind, title) found on one page of text."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    found: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = CHAPTER.match(line)
        if match:
            title = match.group(3).strip()
            if not title and index + 1 < len(lines):
                title = lines[index + 1]
            found.append((1, "chapter", title or f"{match.group(1).title()} {match.group(2)}"))
            continue
        section = SECTION.match(line)
        if section and not line.endswith(".") and len(line.split()) <= 12 and "=" not in line:
            found.append((2, "section", section.group(2).strip()))
            continue
        if index < 3 and _is_caps_title(line):
            found.append((1, "caps", line.title()))
    return found


def _norm(title: str) -> str:
    return " ".join(title.casefold().split())


def detect_by_text(pages: list[tuple[int, str]]) -> list[dict[str, Any]]:
    raw: list[dict[str, Any]] = []
    for number, text in pages:
        for level, kind, title in headings_in_page(text):
            raw.append({"level": level, "kind": kind, "title": title, "start_page": number})
    appearances: dict[str, list[int]] = {}
    for entry in raw:
        appearances.setdefault(_norm(entry["title"]), []).append(entry["start_page"])
    entries = []
    for entry in raw:
        pages_seen = appearances[_norm(entry["title"])]
        if entry["kind"] == "caps" and len(pages_seen) > RUNNING_HEADER_PAGES:
            continue  # a running header, not a heading
        if (
            entry["start_page"] <= FRONT_MATTER_PAGES
            and len(pages_seen) > 1
            and entry["start_page"] == min(pages_seen)
        ):
            continue  # the contents page listing a heading that appears again later
        entries.append(entry)
    seen: set[tuple[str, int]] = set()
    unique = []
    for entry in entries:
        key = (_norm(entry["title"]), entry["start_page"])
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return unique


def detect_by_outline(pdf: Path) -> list[dict[str, Any]]:
    from app.bookcheck.ingest import load_pypdf

    reader = load_pypdf().PdfReader(str(pdf))
    entries: list[dict[str, Any]] = []

    def walk(items: list[Any], level: int) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, level + 1)
                continue
            try:
                page = reader.get_destination_page_number(item) + 1
            except Exception:
                continue
            title = str(getattr(item, "title", "")).strip()
            if title:
                entries.append(
                    {"level": min(level, 2), "kind": "outline", "title": title, "start_page": page}
                )

    walk(list(reader.outline), 1)
    return entries


def add_ranges(entries: list[dict[str, Any]], total_pages: int) -> list[dict[str, Any]]:
    entries = sorted(entries, key=lambda e: (e["start_page"], e["level"]))
    for index, entry in enumerate(entries):
        end = total_pages
        for later in entries[index + 1 :]:
            if later["level"] <= entry["level"]:
                end = max(entry["start_page"], later["start_page"])
                break
        entry["end_page"] = end
    return entries


def confidence_for(method: str, entries: list[dict[str, Any]]) -> str:
    if method == "outline":
        return "high" if len(entries) >= 3 else "medium"
    chapters = [e for e in entries if e["kind"] == "chapter"]
    if len(chapters) >= 3:
        return "medium"
    return "low" if len(entries) < 3 else "medium"


def build_toc(settings: Settings, book: Book) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    method = "text"
    pdf = settings.books_dir / book.file
    if pdf.is_file():
        try:
            entries = detect_by_outline(pdf)
            method = "outline"
        except Exception:  # missing pypdf or a damaged outline: use the text heuristics
            entries = []
    if len(entries) < 2:
        method = "text"
        entries = detect_by_text(list(iter_pages(settings, book.sha)))
    entries = add_ranges(entries, book.pages)
    return {
        "sha": book.sha,
        "method": method,
        "confidence": confidence_for(method, entries),
        "entries": entries,
    }


def run_toc(settings: Settings) -> dict[str, int]:
    counts = {"books": 0, "headings": 0, "low_confidence_books": 0}
    for book in load_books(settings):
        toc = build_toc(settings, book)
        write_json(settings.out_dir / "toc" / f"{book.sha}.json", toc)
        counts["books"] += 1
        counts["headings"] += len(toc["entries"])
        counts["low_confidence_books"] += toc["confidence"] == "low"
    return counts
