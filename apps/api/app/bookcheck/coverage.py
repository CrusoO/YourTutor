"""coverage: match book headings to our syllabus map (difflib + token overlap, deterministic)."""

from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.bookcheck.items import load_syllabus
from app.bookcheck.settings import Settings
from app.bookcheck.store import books_for, load_books, read_json, write_json
from app.bookcheck.text import content_words, stem

MATCH = 0.5  # at or above: a book heading matches our topic
CHAPTER_LOW = 0.6  # a chapter whose best score is below this is reported as weak


def _tokens(text: str) -> set[str]:
    return {stem(w) for w in content_words(text)}


def score(ours: str, heading: str) -> float:
    a, b = _tokens(ours), _tokens(heading)
    overlap = len(a & b) / min(len(a), len(b)) if a and b else 0.0
    ratio = SequenceMatcher(None, " ".join(sorted(a)), " ".join(sorted(b))).ratio()
    return round(max(overlap * 0.9, ratio), 3)


def best_heading(ours: str, headings: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for heading in headings:
        value = score(ours, heading["title"])
        if best is None or value > best["score"]:
            best = {
                "score": value,
                "title": heading["title"],
                "sha": heading["sha"],
                "start_page": heading["start_page"],
                "end_page": heading["end_page"],
                "level": heading["level"],
            }
    return best


def book_headings(settings: Settings, grade: int, subject: str) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    for book in books_for(load_books(settings), grade, subject):
        toc = read_json(settings.out_dir / "toc" / f"{book.sha}.json", {"entries": []})
        for entry in toc["entries"]:
            headings.append({**entry, "sha": book.sha})
    return headings


def run_coverage(
    settings: Settings, content_root: Path, grade: int, subject: str
) -> dict[str, Any] | None:
    """Write OUT/coverage/N-S.json and return the repo-safe summary (our words, counts only)."""
    chapters = load_syllabus(content_root, grade, subject)
    if chapters is None:
        return None
    headings = book_headings(settings, grade, subject)
    out_chapters: list[dict[str, Any]] = []
    out_topics: list[dict[str, Any]] = []
    for chapter in chapters:
        match = best_heading(chapter.title, [h for h in headings if h["level"] == 1] or headings)
        out_chapters.append({"key": chapter.key, "confidence": chapter.confidence, "match": match})
        for topic in chapter.topics:
            tmatch = best_heading(topic.title, headings)
            out_topics.append({"key": topic.key, "chapter_key": chapter.key, "match": tmatch})
    matched_titles = {
        (m["match"]["sha"], m["match"]["start_page"])
        for m in out_chapters + out_topics
        if m["match"] and m["match"]["score"] >= MATCH
    }
    unmatched = sum(1 for h in headings if (h["sha"], h["start_page"]) not in matched_titles)
    write_json(
        settings.out_dir / "coverage" / f"{grade}-{subject}.json",
        {"chapters": out_chapters, "topics": out_topics, "unmatched_book_headings": unmatched},
    )

    def weak(row: dict[str, Any], limit: float) -> bool:
        return row["match"] is None or row["match"]["score"] < limit

    return {
        "headings": len(headings),
        "topics_without_match": [t["key"] for t in out_topics if weak(t, MATCH)],
        "chapters_low_match": [c["key"] for c in out_chapters if weak(c, CHAPTER_LOW)],
        "unmatched_book_headings": unmatched,
        "low_confidence_chapters_matched": [
            c["key"] for c in out_chapters if c["confidence"] == "low" and not weak(c, CHAPTER_LOW)
        ],
        "low_confidence_chapters_unmatched": [
            c["key"] for c in out_chapters if c["confidence"] == "low" and weak(c, CHAPTER_LOW)
        ],
    }
