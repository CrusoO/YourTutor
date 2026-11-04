"""Helplines config: nothing is verified, no number is invented, and the prod hook sees it."""

from __future__ import annotations

from pathlib import Path

from app.helplines import all_helplines, helplines_for, load_helplines, unverified_helplines


def test_only_the_two_known_lines_exist_and_both_are_unverified() -> None:
    rows = {h.id: h for h in all_helplines()}
    assert {r.number for r in rows.values()} == {"14416", "1098"}
    assert all(h.verified is False for h in rows.values())
    assert sorted(unverified_helplines()) == ["childline", "tele_manas"]


def test_exam_counselling_has_a_place_but_no_invented_numbers() -> None:
    assert helplines_for(("exam_counselling",)) == []


def test_an_entry_without_a_number_is_never_shown_or_counted(tmp_path: Path) -> None:
    (tmp_path / "helplines.yaml").write_text(
        "default_region: XX\n"
        "helplines: []\n"
        "exam_counselling:\n"
        "  - {id: board_line, region: XX, name: Board line, number: null, verified: false}\n"
        '  - {id: ok_line, region: XX, name: OK line, number: "123", verified: true}\n',
        encoding="utf-8",
    )
    _, rows = load_helplines(tmp_path)
    assert [r.id for r in rows] == ["ok_line"]
    assert unverified_helplines(tmp_path) == []


def test_a_flag_other_than_true_counts_as_unverified(tmp_path: Path) -> None:
    (tmp_path / "helplines.yaml").write_text(
        "default_region: XX\n"
        "helplines:\n"
        '  - {id: a, region: XX, name: A, number: "1", verified: "yes"}\n'
        '  - {id: b, region: XX, name: B, number: "2"}\n',
        encoding="utf-8",
    )
    assert unverified_helplines(tmp_path) == ["a", "b"]
