"""check: local, deterministic comparison of our items with the cached book text. No model.

Verdicts: agree | not_found | possible_conflict | needs_human. Reasons:
  constant_mismatch      a constant in our item differs (>1%) from every value the book gives
  topic_absent           our topic has no matching book heading
  key_terms_not_in_book  the correct answer's content words are not in the best-matching passages
  distractor_also_stated a wrong option's words sit with the question's terms in one book passage
  numeric_answer         the answer is a bare number; only the constants check could apply
  nothing_checkable      no check could be run
Limits: this is word matching, not understanding. Paraphrase, synonyms, tables, diagrams and
formulas laid out in several lines will give not_found or needs_human. Treat verdicts as a
to-read list for a person, never as proof either way.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bookcheck.coverage import CHAPTER_LOW, MATCH
from app.bookcheck.facts import extract_consts, extract_page
from app.bookcheck.items import OurItem, load_items, load_syllabus
from app.bookcheck.settings import Settings
from app.bookcheck.store import (
    Book,
    books_for,
    iter_pages,
    load_books,
    read_json,
    write_jsonl,
)
from app.bookcheck.text import BM25, content_words, snippet, stem, words

WINDOW_WORDS = 60
WINDOW_STRIDE = 30
TERM_COVERAGE_MIN = 0.5
DISTRACTOR_WORD_COVERAGE = 0.8
DISTRACTOR_STEM_COVERAGE = 0.5
TOP_K = 5
CONST_TOLERANCE = 0.01

Passage = tuple[str, int, list[str]]  # (sha, page, words)


def build_passages(settings: Settings, books: list[Book]) -> list[Passage]:
    passages: list[Passage] = []
    for book in books:
        for page, text in iter_pages(settings, book.sha):
            tokens = words(text)
            if not tokens:
                continue
            for start in range(0, max(1, len(tokens) - WINDOW_STRIDE), WINDOW_STRIDE):
                passages.append((book.sha, page, tokens[start : start + WINDOW_WORDS]))
    return passages


class Searcher:
    """BM25 over passages, optionally limited to a page range of one book. Indexes are cached."""

    def __init__(self, passages: list[Passage]) -> None:
        self.passages = passages
        self._cache: dict[tuple[str, int, int] | None, tuple[BM25, list[Passage]]] = {}

    def _index(self, scope: tuple[str, int, int] | None) -> tuple[BM25, list[Passage]]:
        if scope not in self._cache:
            if scope is None:
                subset = self.passages
            else:
                sha, start, end = scope
                subset = [p for p in self.passages if p[0] == sha and start <= p[1] <= end]
            self._cache[scope] = (BM25([[stem(w) for w in p[2]] for p in subset]), subset)
        return self._cache[scope]

    def top(
        self, query: list[str], scope: tuple[str, int, int] | None, k: int = TOP_K
    ) -> list[Passage]:
        bm25, subset = self._index(scope)
        return [subset[i] for i, _ in bm25.top([stem(w) for w in query], k)]


def _coverage(terms: list[str], passages: list[Passage]) -> float:
    wanted = {stem(t) for t in terms}
    if not wanted:
        return 1.0
    present = {stem(w) for _, _, tokens in passages for w in tokens}
    return len(wanted & present) / len(wanted)


def book_consts(settings: Settings, books: list[Book]) -> list[dict[str, Any]]:
    consts: list[dict[str, Any]] = []
    for book in books:
        stored = read_json(settings.out_dir / "facts" / f"{book.sha}.json")
        if stored is not None:
            facts = stored["facts"]
        else:
            facts = [
                f for page, text in iter_pages(settings, book.sha) for f in extract_page(page, text)
            ]
        consts.extend(f for f in facts if f["kind"] == "const")
    return consts


def constants_verdict(item: OurItem, book_facts: list[dict[str, Any]]) -> tuple[str, int]:
    """('mismatch' | 'ok' | 'none', number compared)."""
    text = " ".join([item.stem, item.correct, *item.texts.values()])
    compared, bad = 0, 0
    for ours in extract_consts(text):
        theirs = [
            f["value"]
            for f in book_facts
            if set(f.get("keywords", [])) & set(ours["keywords"]) and f["unit"] == ours["unit"]
        ]
        if not theirs:
            continue
        compared += 1
        if not any(abs(ours["value"] - v) <= CONST_TOLERANCE * max(abs(v), 1e-12) for v in theirs):
            bad += 1
    if bad:
        return "mismatch", compared
    return ("ok" if compared else "none"), compared


def _scope_for(item: OurItem, coverage: dict[str, Any] | None, chapter_of: dict[str, str]) -> Any:
    """(scope, topic_absent). Scope limits the search to the matched chapter or section."""
    if coverage is None:
        return None, False
    topic = next((t for t in coverage["topics"] if t["key"] == item.topic), None)
    if topic is None:
        return None, False  # topic not in the map: search the whole book
    chapter_key = chapter_of.get(item.topic, topic["chapter_key"])
    chapter = next((c for c in coverage["chapters"] if c["key"] == chapter_key), None)
    cmatch = chapter["match"] if chapter else None
    tmatch = topic["match"]
    if cmatch and cmatch["score"] >= CHAPTER_LOW:
        return (cmatch["sha"], cmatch["start_page"], cmatch["end_page"]), False
    if tmatch and tmatch["score"] >= MATCH:
        return (tmatch["sha"], tmatch["start_page"], tmatch["end_page"]), False
    return None, True


def check_item(
    item: OurItem,
    searcher: Searcher,
    book_facts: list[dict[str, Any]],
    coverage: dict[str, Any] | None,
    chapter_of: dict[str, str],
) -> dict[str, Any]:
    reasons: list[str] = []
    passed = False
    evidence: Passage | None = None
    scope, absent = _scope_for(item, coverage, chapter_of)
    stem_terms = content_words(item.stem)
    answer_terms = content_words(item.correct)

    state, _ = constants_verdict(item, book_facts)
    if state == "mismatch":
        reasons.append("constant_mismatch")
    elif state == "ok":
        passed = True

    conflict_found = False
    if absent:
        reasons.append("topic_absent")
    else:
        hits = searcher.top(stem_terms + answer_terms, scope)
        evidence = hits[0] if hits else None
        if answer_terms and not all(t.isdigit() for t in answer_terms):
            if _coverage(answer_terms, hits) < TERM_COVERAGE_MIN:
                reasons.append("key_terms_not_in_book")
            else:
                passed = True
        elif answer_terms:
            reasons.append("numeric_answer")
        stem_hits = searcher.top(stem_terms, scope) if stem_terms else []
        correct_set = {stem(t) for t in answer_terms}
        for wrong in item.wrong:
            wrong_terms = [t for t in content_words(wrong) if stem(t) not in correct_set]
            if not wrong_terms:
                continue
            for passage in stem_hits:
                if (
                    _coverage(wrong_terms, [passage]) >= DISTRACTOR_WORD_COVERAGE
                    and _coverage(stem_terms, [passage]) >= DISTRACTOR_STEM_COVERAGE
                ):
                    conflict_found = True
                    evidence = passage
                    break
            if conflict_found:
                break
    if conflict_found:
        reasons.append("distractor_also_stated")

    hard = {"constant_mismatch", "distractor_also_stated"}
    if hard & set(reasons):
        verdict = "possible_conflict"
    elif {"topic_absent", "key_terms_not_in_book"} & set(reasons):
        verdict = "not_found"
    elif passed:
        verdict = "agree"
    else:
        verdict = "needs_human"
        if not reasons:
            reasons.append("nothing_checkable")
    row: dict[str, Any] = {
        "item_id": item.id,
        "topic": item.topic,
        "verdict": verdict,
        "reason": reasons[0] if reasons else "ok",
        "reasons": reasons,
    }
    if evidence is not None and verdict != "agree":
        row.update(sha=evidence[0], page=evidence[1], snippet=snippet(" ".join(evidence[2])))
    return row


def run_check(
    settings: Settings, content_root: Path, grade: int, subject: str, which: str = "all"
) -> dict[str, int] | None:
    """Write OUT/findings/N-S.jsonl; return verdict counts, or None when there is no book."""
    books = books_for(load_books(settings), grade, subject)
    if not books:
        return None
    items = load_items(content_root, grade, subject, which)
    chapters = load_syllabus(content_root, grade, subject) or []
    chapter_of = {t.key: c.key for c in chapters for t in c.topics}
    coverage = read_json(settings.out_dir / "coverage" / f"{grade}-{subject}.json")
    searcher = Searcher(build_passages(settings, books))
    facts = book_consts(settings, books)
    rows = []
    for item in items:
        row = check_item(item, searcher, facts, coverage, chapter_of)
        row.update({"class": grade, "subject": subject})
        rows.append(row)
    write_jsonl(settings.out_dir / "findings" / f"{grade}-{subject}.jsonl", rows)
    counts = {
        "items": len(rows),
        "agree": 0,
        "not_found": 0,
        "possible_conflict": 0,
        "needs_human": 0,
    }
    for row in rows:
        counts[row["verdict"]] += 1
    return counts
