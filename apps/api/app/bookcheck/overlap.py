"""overlap: the copy detector. Finds runs of n or more identical consecutive words shared by our
item text and the book text (casefolded, punctuation stripped).

Memory: one hash set of n-word shingles per book, built page by page and dropped before the next
book. The shingle map holds a hash and a page number, not text. Words are matched per field, so a
run never crosses from one of our fields into another.
Limits: a copy with one word changed every few words is not caught; neither is a close paraphrase.
Text from scanned pages (no text layer) is invisible to this check.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bookcheck.items import OurItem, load_items
from app.bookcheck.settings import Settings
from app.bookcheck.store import Book, books_for, iter_pages, load_books, write_jsonl
from app.bookcheck.text import snippet, words

DEFAULT_N = 8


def shingle_map(settings: Settings, book: Book, n: int) -> dict[int, int]:
    """hash of every n-word window in the book -> first page it appears on."""
    seen: dict[int, int] = {}
    carry: list[str] = []
    for page, text in iter_pages(settings, book.sha):
        tokens = carry + words(text)
        for start in range(0, len(tokens) - n + 1):
            seen.setdefault(hash(tuple(tokens[start : start + n])), page)
        carry = tokens[-(n - 1) :] if n > 1 else []
    return seen


def find_runs(tokens: list[str], shingles: dict[int, int], n: int) -> list[tuple[int, int, int]]:
    """(start word, length in words, page) of each maximal run of matching windows."""
    runs: list[tuple[int, int, int]] = []
    start: int | None = None
    page = 0
    last = -2
    for index in range(0, len(tokens) - n + 1):
        found = shingles.get(hash(tuple(tokens[index : index + n])))
        if found is None:
            continue
        if start is not None and index == last + 1:
            last = index
            continue
        if start is not None:
            runs.append((start, last - start + n, page))
        start, last, page = index, index, found
    if start is not None:
        runs.append((start, last - start + n, page))
    return runs


def run_overlap(
    settings: Settings,
    content_root: Path,
    scopes: list[tuple[int, str]],
    n: int = DEFAULT_N,
    all_books: bool = False,
) -> dict[str, Any]:
    """Check each (class, subject) scope. Writes OUT/overlap/N-S.jsonl per scope with books."""
    manifest = load_books(settings)
    result: dict[str, Any] = {"scopes_checked": 0, "items": 0, "flagged_items": [], "no_books": 0}
    for grade, subject in scopes:
        books = manifest if all_books else books_for(manifest, grade, subject)
        items = load_items(content_root, grade, subject)
        if not books:
            result["no_books"] += 1
            continue
        result["scopes_checked"] += 1
        result["items"] += len(items)
        rows: list[dict[str, Any]] = []
        token_cache: list[tuple[OurItem, str, list[str]]] = [
            (item, name, words(text)) for item in items for name, text in item.texts.items()
        ]
        for book in books:
            shingles = shingle_map(settings, book, n)
            for item, name, tokens in token_cache:
                for start, length, page in find_runs(tokens, shingles, n):
                    rows.append(
                        {
                            "item_id": item.id,
                            "topic": item.topic,
                            "field": name,
                            "run_words": length,
                            "sha": book.sha,
                            "page": page,
                            "snippet": snippet(" ".join(tokens[start : start + length])),
                        }
                    )
            del shingles
        write_jsonl(settings.out_dir / "overlap" / f"{grade}-{subject}.jsonl", rows)
        result["flagged_items"].extend(sorted({r["item_id"] for r in rows}))
    return result
