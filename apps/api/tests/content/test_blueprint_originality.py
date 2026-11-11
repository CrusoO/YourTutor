"""Blueprint importer, drift report and originality gate. Invented data only; no database."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from app.content import blueprint as bp
from app.content import originality as og
from app.content.__main__ import main
from app.db.models import ItemRow
from app.player.runtime import _item_labels
from tests.content.conftest import loc, minimal_skill, write_yaml

HEADER = (
    "year,paper,section,question_number,marks,question_type,chapter,skill_id,competency,"
    "internal_choice"
)
CHAPTER = "cbse.10.maths.ch02"
SKILL = "MATH.S1"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    write_yaml(tmp_path / "skills" / "s1.yaml", minimal_skill(SKILL))
    write_yaml(
        tmp_path / "curricula" / "cbse" / "curriculum.yaml",
        {
            "id": "cbse",
            "default_timezone": "Asia/Kolkata",
            "jurisdiction_profile": "default_strict",
            "legacy_board": "CBSE",
            "books": [
                {
                    "id": "cbse.10.maths",
                    "grade": 10,
                    "subject": "maths",
                    "default_chapter_id": CHAPTER,
                    "chapters": [
                        {
                            "id": CHAPTER,
                            "overlay_id": CHAPTER,
                            "chapter_key": "invented",
                            "titles": {"en": "Invented chapter"},
                            "sections": [],
                        }
                    ],
                }
            ],
        },
    )
    return tmp_path


def csv_file(tmp_path: Path, lines: list[str], header: str = HEADER) -> Path:
    path = tmp_path / "rows.csv"
    path.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")
    return path


def line(
    year: int = 2024, number: str = "1", marks: int = 1, qtype: str = "mcq", **over: str
) -> str:
    cells = {
        "year": str(year),
        "paper": "cbse-10-maths-standard",
        "section": "A",
        "number": number,
        "marks": str(marks),
        "type": qtype,
        "chapter": CHAPTER,
        "skill": SKILL,
        "comp": "apply",
        "choice": "false",
    }
    cells.update(over)
    return ",".join(cells.values())


# --- importer --------------------------------------------------------------------------------


def test_import_writes_yaml_and_audit_line(root: Path, tmp_path: Path) -> None:
    src = csv_file(tmp_path, [line(number="1"), line(number="2", marks=3, qtype="short")])
    result = bp.import_csv(src, root, source_deleted=True, today=date(2026, 11, 11))
    assert result.ok and result.added == 2
    assert len(bp.load_blueprint(root)) == 2
    audit = json.loads((root / "blueprint" / "audit.jsonl").read_text(encoding="utf-8"))
    assert audit == {
        "date": "2026-11-11",
        "rows_added": 2,
        "source_file": "rows.csv",
        "sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "source_deleted": True,
    }


def test_second_import_appends_and_duplicates_are_refused(root: Path, tmp_path: Path) -> None:
    assert bp.import_csv(csv_file(tmp_path, [line(number="1")]), root).ok
    assert bp.import_csv(csv_file(tmp_path, [line(number="2")]), root).ok
    again = bp.import_csv(csv_file(tmp_path, [line(number="2")]), root)
    assert not again.ok and "duplicate" in again.errors[0]
    assert len(bp.load_blueprint(root)) == 2
    assert len((root / "blueprint" / "audit.jsonl").read_text().splitlines()) == 2


@pytest.mark.parametrize("column", ["stem", "question", "Question_Text"])
def test_text_columns_are_refused(root: Path, tmp_path: Path, column: str) -> None:
    src = csv_file(tmp_path, [line() + ",invented words"], header=HEADER + "," + column)
    result = bp.import_csv(src, root)
    assert not result.ok and "facts only" in result.errors[0]
    assert not (root / "blueprint").exists()


def test_unknown_column_refused(root: Path, tmp_path: Path) -> None:
    src = csv_file(tmp_path, [line() + ",x"], header=HEADER + ",colour")
    assert "unknown column" in bp.import_csv(src, root).errors[0]


def test_long_or_questionlike_note_refused(root: Path, tmp_path: Path) -> None:
    for note in ("what is the value of the invented thing", "n" * 61, "is 3 + 4 = 7"):
        src = csv_file(tmp_path, [line() + f",{note}"], header=HEADER + ",note")
        result = bp.import_csv(src, root)
        assert not result.ok, note
        assert "note" in result.errors[0]
    ok = csv_file(tmp_path, [line() + ",two parts"], header=HEADER + ",note")
    assert bp.import_csv(ok, root).ok


def test_unknown_chapter_skill_type_and_bad_values_refused_whole_file(
    root: Path, tmp_path: Path
) -> None:
    src = csv_file(
        tmp_path,
        [
            line(number="1"),
            line(number="2", chapter="cbse.10.maths.ch99"),
            line(number="3", skill="MATH.NOPE"),
            line(number="4", qtype="essay"),
            line(number="5", comp="evaluate"),
            line(number="6", marks=0),
            line(number="7", choice="maybe"),
        ],
    )
    result = bp.import_csv(src, root)
    text = "\n".join(result.errors)
    for needle in ("ch99", "MATH.NOPE", "question_type", "competency", "marks", "internal_choice"):
        assert needle in text
    assert not result.ok and bp.load_blueprint(root) == []


# --- report and drift ------------------------------------------------------------------------


def make_rows() -> list[bp.BlueprintRow]:
    def row(year: int, number: str, marks: int, qtype: str) -> bp.BlueprintRow:
        return bp.BlueprintRow(
            year=year,
            paper="p-1",
            section="A",
            question_number=number,
            marks=marks,
            question_type=bp.QuestionType(qtype),
            chapter=CHAPTER,
            skill_id=SKILL,
            competency=bp.Competency.apply,
        )

    def year_rows(year: int, case_based: int, short: int) -> list[bp.BlueprintRow]:
        made = [row(year, f"{n}", 10, "case_based") for n in range(case_based // 10)]
        return made + [row(year, f"{n + 20}", 10, "short") for n in range(short // 10)]

    rows: list[bp.BlueprintRow] = []
    for year in (2021, 2022, 2023):  # 80 marks: 10 case_based, 70 short
        rows += year_rows(year, 10, 70)
    rows += year_rows(2024, 30, 50)  # case_based 12.5 percent to 37.5 percent
    return rows


def test_drift_flags_a_type_that_moved_more_than_five_points() -> None:
    drifts = bp.type_drift(make_rows())
    flagged = {(d.year, d.question_type) for d in drifts}
    assert flagged == {(2024, "case_based"), (2024, "short")}
    case = next(d for d in drifts if d.question_type == "case_based")
    assert round(case.delta, 1) == 25.0
    assert case.baseline_years == (2021, 2022, 2023)


def test_drift_quiet_when_stable_and_uses_only_three_prior_years() -> None:
    rows = make_rows()[:24]  # three identical years
    assert bp.type_drift(rows) == []
    older = [
        r.model_copy(update={"year": 2018, "question_type": bp.QuestionType.long})
        for r in make_rows()[:8]
    ]
    drifts = bp.type_drift([*older, *make_rows()])
    assert all(2018 not in d.baseline_years for d in drifts if d.year == 2024)


def test_report_prints_chapter_marks_and_flag() -> None:
    text = bp.format_report(make_rows())
    assert f"{CHAPTER}: 80 marks (case_based 10, short 70)" in text
    assert "FLAG p-1 2024 case_based" in text
    assert bp.format_report([]) == "No blueprint rows."


def test_pattern_for_skill_and_tag(root: Path, tmp_path: Path) -> None:
    rows = make_rows()
    found = bp.pattern_for_skill(rows, SKILL)
    assert found is not None and found[1] == "short" and found[2] == [2021, 2022, 2023, 2024]
    assert bp.pattern_for_skill(rows, "OTHER") is None
    assert bp.pattern_tag_for_skill(SKILL, root) is None  # no blueprint rows in this root
    bp.import_csv(csv_file(tmp_path, [line(year=2023, marks=3, qtype="short")]), root)
    bp._cached_blueprint.cache_clear()
    assert bp.pattern_tag_for_skill(SKILL, root) == (
        "Question type seen in CBSE Class 10 board papers: 3-mark short (2023)."
    )
    bp._cached_blueprint.cache_clear()


def test_cli_import_and_report(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = csv_file(tmp_path, [line()])
    assert main(["blueprint-import", str(src), "--root", str(root)]) == 0
    assert "Imported 1 rows" in capsys.readouterr().out
    assert main(["blueprint-report", "--root", str(root)]) == 0
    assert CHAPTER in capsys.readouterr().out
    bad = csv_file(tmp_path, [line()], header=HEADER)
    bad.write_text(HEADER + ",stem\n" + line() + ",x\n", encoding="utf-8")
    assert main(["blueprint-import", str(bad), "--root", str(root)]) == 1


# --- originality -----------------------------------------------------------------------------

REF = (
    "A tank holds 240 litres of water and a tap fills it at 12 litres every minute until "
    "the water reaches the top of the tank.\n\n"
    "Neha buys 7 pens and 3 notebooks for 95 rupees in the invented market."
)


def index_of(*texts: str) -> og.ReferenceIndex:
    index = og.ReferenceIndex()
    for text in texts:
        index.add_text(text)
    return index


def test_canonical_form_hides_numbers_and_variable_letters() -> None:
    assert og.canonicalise("Find x if 3x + 12 = 45!") == "find <v> if <n> <v> <n> <n>"
    assert og.canonicalise("A is 5, i is 6") == "a is <n> i is <n>"


def test_shingles_hashed_and_ordered() -> None:
    grams = og.shingles(["a", "b", "c", "d", "e", "f"])
    assert len(grams) == 2 and all(len(g) == 16 for g in grams)
    assert og.shingles(["a", "b"]) == []


def test_index_json_holds_no_reference_text() -> None:
    blob = og.ReferenceIndex().to_json()
    index = index_of(REF)
    blob = index.to_json()
    for word in ("tank", "litres", "notebooks", "invented", "market"):
        assert word not in blob
    round_trip = og.ReferenceIndex.from_json(blob)
    assert round_trip.shingle_hashes == index.shingle_hashes
    with pytest.raises(ValueError):
        og.ReferenceIndex.from_json('{"version": 99, "n": 5}')


def test_copy_with_changed_numbers_blocks() -> None:
    copied = (
        "A tank holds 500 litres of water and a tap fills it at 25 litres every minute until "
        "the water reaches the top of the tank."
    )
    score = og.score_text(copied, index_of(REF))
    assert score.status is og.OriginalityStatus.block
    assert score.containment >= og.BLOCK_CONTAINMENT


def test_unrelated_text_passes() -> None:
    score = og.score_text("Ravi walks 4 km each morning. How far in 6 days?", index_of(REF))
    assert score.status is og.OriginalityStatus.passed
    assert score.containment == 0.0 and score.longest_run == 0


def test_long_shared_run_goes_to_review_not_block() -> None:
    # 9 shared tokens inside a long invented sentence: containment stays under the block line.
    item = (
        "Consider the following unrelated opening words, then a tap fills it at 12 litres every "
        "minute, followed by a long and entirely different ending about birds, rivers and hills "
        "that has nothing to do with the reference at all."
    )
    score = og.score_text(item, index_of(REF))
    assert score.longest_run >= og.RUN_TOKENS
    assert score.containment < og.BLOCK_CONTAINMENT
    assert score.status is og.OriginalityStatus.review


def test_stock_phrase_runs_are_ignored() -> None:
    reference = (
        "which of the following is equal to the sum of the product of the difference between"
    )
    item = "Which of the following is equal to the sum of the product of the difference between?"
    score = og.score_text(item, index_of(reference))
    assert score.longest_run < og.RUN_TOKENS
    assert score.status is not og.OriginalityStatus.review or score.structure_match


def test_structure_match_same_numbers_and_unknowns_goes_to_review() -> None:
    reference = "Solve for x and y: the line meets 4 and 9 and 15."
    item = "Ravi picks 15, 4 and 9 marbles; find x and y for his bag."
    score = og.score_text(item, index_of(reference))
    assert score.structure_match and score.status is og.OriginalityStatus.review
    assert og.structure_hash("no numbers here") is None
    assert og.structure_hash("only 3 here with x") is None  # fewer than two numbers


def test_short_text_has_no_containment() -> None:
    score = og.score_text("Find x.", index_of(REF))
    assert score.containment == 0.0 and score.status is og.OriginalityStatus.passed


def test_embedding_stub_interface() -> None:
    class Fixed:
        def __init__(self, value: float) -> None:
            self.value = value

        def similarity(self, text: str) -> float | None:
            return self.value

    index = index_of(REF)
    other = "Ravi walks 4 km each morning."
    assert og.score_text(other, index, embedder=Fixed(0.93)).status is og.OriginalityStatus.block
    assert og.score_text(other, index, embedder=Fixed(0.86)).status is og.OriginalityStatus.review
    assert og.score_text(other, index, embedder=Fixed(0.5)).status is og.OriginalityStatus.passed
    assert og.NoEmbeddingScorer().similarity(other) is None
    assert (og.EMBED_BLOCK_THRESHOLD, og.EMBED_REVIEW_THRESHOLD) == (0.92, 0.85)


def test_cli_index_and_check_never_print_reference_text(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    refs = tmp_path / "refs"
    refs.mkdir()
    (refs / "a.txt").write_text(REF, encoding="utf-8")
    out = tmp_path / "index.json"
    assert main(["originality-index", "--from", str(refs), "--out", str(out)]) == 0
    assert "hashes only" in capsys.readouterr().out
    assert "tank" not in out.read_text(encoding="utf-8")

    item = {
        "id": "ITEM.COPY",
        "skill_ids": [SKILL],
        "difficulty": 0.3,
        "type": "numeric",
        "pool": "practice",
        "role": "procedure",
        "stem": loc(
            "A tank holds 500 litres of water and a tap fills it at 25 litres every minute until "
            "the water reaches the top of the tank."
        ),
        "answer": {"sympy": "20"},
        "solution_steps": [loc("20")],
        "hints": [{"level": n, "en": f"hint {n}"} for n in (1, 2, 3)],
        "prediction_prompt": loc("Guess?"),
    }
    write_yaml(root / "items" / "copy.yaml", item)
    code = main(["originality-check", "--index", str(out), "--root", str(root)])
    shown = capsys.readouterr().out
    assert code == 1 and "block" in shown and "ITEM.COPY" in shown
    assert "tank" not in shown and "litres" not in shown


# --- labels on a served row ------------------------------------------------------------------


def row(**over: object) -> ItemRow:
    base: dict[str, object] = {
        "id": "ITEM.1",
        "skill_ids": [SKILL],
        "pool": "practice",
        "status": "draft",
        "reviewed_by": None,
        "tier": "A",
        "provenance": {"original": True},
    }
    base.update(over)
    return ItemRow(**base)


def test_row_labels_follow_the_rule() -> None:
    labels = _item_labels(row())
    assert labels is not None and set(labels) == {"question", "badge"}
    reviewed = _item_labels(row(status="approved", reviewed_by="t1"))
    assert reviewed is not None and "reviewed" in reviewed
    assert _item_labels(row(tier="B")) is None
    assert _item_labels(row(tier=None)) is None
    assert _item_labels(row(provenance={"original": False})) is None
    assert _item_labels(row(provenance=None)) is None
    assert _item_labels(row(pool="diagnostic")) is None
