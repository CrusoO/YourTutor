from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.bookcheck import coverage, facts, ingest, toc
from app.bookcheck.check import run_check
from app.bookcheck.overlap import find_runs, run_overlap, shingle_map
from app.bookcheck.settings import Settings
from app.bookcheck.store import books_for, load_books, read_json, read_jsonl
from app.bookcheck.text import BM25, words
from tests.bookcheck.conftest import BOOK_RUN, item, minimal_pdf, write_book, write_drafts


def findings(settings: Settings) -> dict[str, dict]:
    rows = read_jsonl(settings.out_dir / "findings" / "9-physics.jsonl")
    return {r["item_id"]: r for r in rows}


# --- toc -----------------------------------------------------------------------------------------


def test_toc_heuristics_find_chapters_sections_and_skip_the_contents_page(
    settings: Settings,
) -> None:
    write_book(settings)
    toc.run_toc(settings)
    data = read_json(settings.out_dir / "toc" / f"{'a' * 64}.json")
    titles = [(e["level"], e["title"], e["start_page"]) for e in data["entries"]]
    assert (1, "Motion", 2) in titles
    assert (2, "Speed and velocity", 2) in titles
    assert (1, "Force and Laws of Motion", 4) in titles
    assert not any(page == 1 for _, _, page in titles)  # contents page entries dropped
    assert data["method"] == "text" and data["confidence"] in ("low", "medium")


def test_toc_caps_titles_and_running_headers() -> None:
    pages = [(n, f"RUNNING HEADER\nbody {n}") for n in range(1, 8)]
    pages.append((8, "WORK AND ENERGY\nsome text"))
    entries = toc.detect_by_text(pages)
    assert [e["title"] for e in entries] == ["Work And Energy"]


# --- coverage ------------------------------------------------------------------------------------


def test_coverage_matches_and_reports_in_our_words(settings: Settings, content: Path) -> None:
    write_book(settings)
    toc.run_toc(settings)
    summary = coverage.run_coverage(settings, content, 9, "physics")
    assert summary is not None
    assert summary["topics_without_match"] == ["echo"]
    assert "motion" not in summary["chapters_low_match"]
    assert summary["chapters_low_match"] == ["sound"]
    assert summary["low_confidence_chapters_matched"] == ["force"]
    assert summary["low_confidence_chapters_unmatched"] == ["sound"]
    private = read_json(settings.out_dir / "coverage" / "9-physics.json")
    assert private["topics"][0]["match"]["title"] == "Speed and velocity"


def test_coverage_without_a_syllabus_map_returns_none(settings: Settings, content: Path) -> None:
    assert coverage.run_coverage(settings, content, 9, "chemistry") is None


def test_science_book_serves_all_three_subjects_in_class_9(settings: Settings) -> None:
    write_book(settings, subject="science")
    books = load_books(settings)
    assert books_for(books, 9, "physics") and books_for(books, 9, "biology")
    assert not books_for(books, 9, "maths") and not books_for(books, 11, "physics")


# --- facts and check -----------------------------------------------------------------------------


def test_facts_extract_constants_formulas_and_terms(settings: Settings) -> None:
    write_book(settings)
    facts.run_facts(settings)
    data = read_json(settings.out_dir / "facts" / f"{'a' * 64}.json")["facts"]
    consts = [f for f in data if f["kind"] == "const"]
    assert any(
        "speed" in f["keywords"] and f["value"] == 3e8 and f["unit"] == "m/s" for f in consts
    )
    assert any(
        "gravity" in f["keywords"] and f["value"] == 9.8 and f["unit"] == "m/s2" for f in consts
    )
    assert any(f["kind"] == "term" and f["term"] == "speed" for f in data)


def test_constants_mismatch_is_a_possible_conflict(settings: Settings, content: Path) -> None:
    write_book(settings)
    write_drafts(
        content,
        [
            item(
                "speed_and_velocity",
                "Take the speed of light as 2 x 10^8 m/s. Light covers?",
                "distance",
            ),
            item(
                "speed_and_velocity",
                "Taking gravity to have a value of 9.8 m/s2, find the pull?",
                "distance",
            ),
        ],
    )
    run_check(settings, content, 9, "physics", "drafts")
    rows = findings(settings)
    assert rows["motion#1"]["verdict"] == "possible_conflict"
    assert rows["motion#1"]["reason"] == "constant_mismatch"
    assert rows["motion#2"]["verdict"] != "possible_conflict"


def test_bm25_not_found_and_agree(settings: Settings, content: Path) -> None:
    write_book(settings)
    write_drafts(
        content,
        [
            item(
                "speed_and_velocity",
                "What is average speed of a cyclist?",
                "distance divided by time",
            ),
            item(
                "speed_and_velocity",
                "Which pigment absorbs light in leaves?",
                "chlorophyll in chloroplasts",
            ),
        ],
    )
    counts = run_check(settings, content, 9, "physics", "drafts")
    rows = findings(settings)
    assert rows["motion#1"]["verdict"] == "agree"
    assert rows["motion#2"]["verdict"] == "not_found"
    assert rows["motion#2"]["reason"] == "key_terms_not_in_book"
    assert counts is not None and counts["agree"] == 1 and counts["not_found"] == 1


def test_distractor_also_stated_is_flagged(settings: Settings, content: Path) -> None:
    write_book(settings)
    write_drafts(
        content,
        [
            item(
                "speed_and_velocity",
                "What does the average speed of a cyclist measure?",
                "distance divided by time",
                wrong=["mass divided by volume"],
            )
        ],
    )
    run_check(settings, content, 9, "physics", "drafts")
    row = findings(settings)["motion#1"]
    assert row["verdict"] == "possible_conflict" and row["reason"] == "distractor_also_stated"
    assert len(row["snippet"].split()) <= 25 and row["page"] == 3


def test_topic_absent_when_coverage_has_no_match(settings: Settings, content: Path) -> None:
    write_book(settings)
    write_drafts(content, [item("echo", "What is an echo of sound?", "reflected sound")])
    toc.run_toc(settings)
    coverage.run_coverage(settings, content, 9, "physics")
    run_check(settings, content, 9, "physics", "drafts")
    row = findings(settings)["motion#1"]
    assert row["verdict"] == "not_found" and row["reason"] == "topic_absent"


def test_check_without_books_returns_none(settings: Settings, content: Path) -> None:
    assert run_check(settings, content, 9, "physics") is None


def test_compiled_items_are_read(settings: Settings, content: Path) -> None:
    write_book(settings)
    folder = content / "cbse" / "9" / "physics" / "items"
    folder.mkdir(parents=True)
    (folder / "ITEM.X.1.yaml").write_text(
        "id: ITEM.X.1\nskill_ids: [speed_and_velocity]\nstem:\n"
        "  en: What is average speed of a cyclist?\n"
        "  ne: <Nepali>\nanswer:\n  accept:\n  - distance divided by time\n",
        encoding="utf-8",
    )
    run_check(settings, content, 9, "physics", "compiled")
    assert findings(settings)["ITEM.X.1"]["verdict"] == "agree"


# --- overlap -------------------------------------------------------------------------------------


def test_find_runs_unit() -> None:
    book = words("alpha beta gamma delta epsilon zeta eta theta iota kappa")
    shingles = {hash(tuple(book[i : i + 4])): 1 for i in range(len(book) - 3)}
    assert find_runs(words("x alpha beta gamma delta epsilon y"), shingles, 4) == [(1, 5, 1)]
    assert find_runs(words("alpha beta gamma y"), shingles, 4) == []


def test_overlap_flags_nine_words_but_not_seven(settings: Settings, content: Path) -> None:
    write_book(settings)
    book = BOOK_RUN.split()
    write_drafts(
        content,
        [
            item(
                "speed_and_velocity", "stem one", "a", expl="Intro. " + " ".join(book[:9]) + " end."
            ),
            item(
                "speed_and_velocity",
                "stem two",
                "a",
                expl="Intro. " + ", ".join(book[:7]) + " end.",
            ),
        ],
    )
    result = run_overlap(settings, content, [(9, "physics")], n=8)
    assert result["flagged_items"] == ["motion#1"]
    rows = read_jsonl(settings.out_dir / "overlap" / "9-physics.jsonl")
    assert rows[0]["run_words"] == 9 and rows[0]["page"] == 2


def test_overlap_catches_a_copy_in_a_hint_and_option(settings: Settings, content: Path) -> None:
    write_book(settings)
    book = BOOK_RUN.split()
    write_drafts(content, [item("t", "s", "a", wrong=[" ".join(book[:8])])])
    result = run_overlap(settings, content, [(9, "physics")], n=8)
    assert result["flagged_items"] == ["motion#1"]


def test_overlap_same_subject_only_unless_all_books(settings: Settings, content: Path) -> None:
    write_book(settings, subject="chemistry", sha="b" * 64)
    write_drafts(content, [item("t", "s", "a", expl=" ".join(BOOK_RUN.split()[:9]))])
    assert run_overlap(settings, content, [(9, "physics")], n=8)["no_books"] == 1
    assert run_overlap(settings, content, [(9, "physics")], n=8, all_books=True)["flagged_items"]


def test_shingle_map_spans_page_boundaries(settings: Settings) -> None:
    write_book(settings, pages=["one two three four", "five six seven eight"])
    book = load_books(settings)[0]
    assert len(shingle_map(settings, book, 4)) == 5


# --- ingest --------------------------------------------------------------------------------------


def test_bm25_ranks_the_matching_passage_first() -> None:
    docs = [["red", "apple"], ["blue", "sea", "water"], ["green", "leaf"]]
    assert BM25(docs).top(["sea"], 1)[0][0] == 1


def test_ingest_reads_a_pdf_and_is_resumable(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("pypdf", reason="pypdf (optional extra bookcheck) is not installed")
    folder = settings.books_dir / "9" / "physics"
    folder.mkdir(parents=True)
    (folder / "fixture.pdf").write_bytes(minimal_pdf(["Hello fixture sentence", ""]))
    (settings.books_dir / "stray.pdf").write_bytes(minimal_pdf(["x"]))
    first = ingest.ingest(settings)
    assert first["new"] == 1 and first["misplaced"] == 1 and first["needs_ocr_pages"] == 1
    manifest = json.loads((settings.out_dir / "manifest.json").read_text())
    book = manifest["books"][0]
    assert book["pages"] == 2 and book["needs_ocr"] == [2] and len(book["sha"]) == 64
    pages = read_jsonl(settings.out_dir / "cache" / book["sha"] / "pages.jsonl")
    assert "Hello fixture sentence" in pages[0]["t"]

    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("a cached book must not be read again")

    monkeypatch.setattr(ingest, "_extract", boom)
    second = ingest.ingest(settings)
    assert second["new"] == 0 and second["skipped"] == 1


def test_ingest_without_pypdf_prints_a_hint(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = settings.books_dir / "9" / "physics"
    folder.mkdir(parents=True)
    (folder / "fixture.pdf").write_bytes(b"%PDF-1.4")

    def missing() -> None:
        raise ingest.PypdfMissing(ingest.INSTALL_HINT)

    monkeypatch.setattr(ingest, "load_pypdf", missing)
    with pytest.raises(ingest.PypdfMissing, match="pip install"):
        ingest.ingest(settings)
