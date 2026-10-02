from __future__ import annotations

from pathlib import Path

from app.content.math_parse import ParseError, normalize, parse_math
from app.content.validator import (
    LIVE_MIN_CHECKPOINT,
    last_step_matches_answer,
    validate_path,
)
from tests.content.conftest import minimal_item, minimal_skill, write_yaml


def test_valid_bundle_ok(content_root: Path) -> None:
    report = validate_path(content_root)
    assert report.ok, report.errors


def test_duplicate_id(content_root: Path) -> None:
    write_yaml(content_root / "skills" / "dup.yaml", minimal_skill("MATH.S1"))
    report = validate_path(content_root)
    assert any("duplicate" in e for e in report.errors)


def test_broken_skill_ref(content_root: Path) -> None:
    write_yaml(content_root / "items" / "bad.yaml", minimal_item("ITEM.BAD", skill="MATH.MISSING"))
    report = validate_path(content_root)
    assert any("unknown skill" in e for e in report.errors)


def test_prerequisite_cycle(content_root: Path) -> None:
    write_yaml(content_root / "skills" / "s1.yaml", minimal_skill("MATH.S1", ["MATH.S2"]))
    write_yaml(content_root / "skills" / "s2.yaml", minimal_skill("MATH.S2", ["MATH.S1"]))
    report = validate_path(content_root)
    assert any("cycle" in e for e in report.errors)


def test_missing_primary_skill_rejected_by_schema(content_root: Path) -> None:
    data = minimal_item("ITEM.NOSKILL")
    data["skill_ids"] = []
    write_yaml(content_root / "items" / "noskill.yaml", data)
    report = validate_path(content_root)
    assert report.errors


def test_missing_hint_level(content_root: Path) -> None:
    data = minimal_item("ITEM.HINT")
    data["hints"] = data["hints"][:2]
    write_yaml(content_root / "items" / "hint.yaml", data)
    report = validate_path(content_root)
    assert report.errors


def test_solution_step_mismatch(content_root: Path) -> None:
    write_yaml(
        content_root / "items" / "mismatch.yaml",
        minimal_item("ITEM.MIS", answer="5", last_step="x = 19"),
    )
    report = validate_path(content_root)
    assert any("not equivalent" in e for e in report.errors)


def test_last_step_matches_answer() -> None:
    assert last_step_matches_answer("x = 5", "5")
    assert not last_step_matches_answer("x = 19", "5")


def test_hint_leak(content_root: Path) -> None:
    write_yaml(
        content_root / "items" / "leak.yaml",
        minimal_item("ITEM.LEAK", answer="5", hint1="The answer is 5"),
    )
    report = validate_path(content_root)
    assert any("leaks" in e for e in report.errors)


def test_bad_sympy_answer(content_root: Path) -> None:
    data = minimal_item("ITEM.BADANS")
    data["answer"]["sympy"] = "__import__('os')"
    write_yaml(content_root / "items" / "badans.yaml", data)
    report = validate_path(content_root)
    assert any("allowlist" in e for e in report.errors)


def test_checkpoint_item_cannot_be_practice_id(content_root: Path) -> None:
    write_yaml(
        content_root / "items" / "cp.yaml",
        minimal_item("ITEM.1", pool="checkpoint"),
    )
    report = validate_path(content_root)
    assert any("checkpoint" in e.lower() for e in report.errors)


def test_live_chapter_errors_when_flagged_live(content_root: Path) -> None:
    write_yaml(
        content_root / "overlays" / "ov.yaml",
        {
            "id": "ov1",
            "board": "bhutan",
            "grade": 9,
            "chapter": "linear_equations",
            "skill_ids": ["MATH.S1"],
            "live": True,
        },
    )
    report = validate_path(content_root)
    assert any("live" in e for e in report.errors)


def test_checkpoint_form_below_hard_min(content_root: Path) -> None:
    write_yaml(
        content_root / "items" / "c1.yaml",
        minimal_item("ITEM.C1", pool="checkpoint"),
    )
    write_yaml(
        content_root / "checkpoints" / "forms.yaml",
        {
            "id": "CP.TEST",
            "checkpoint_id": "CP.TEST",
            "A": ["ITEM.C1"],
            "B": ["ITEM.C1"],
            "match_map": {"ITEM.C1": "ITEM.C1"},
        },
    )
    report = validate_path(content_root)
    assert any(str(LIVE_MIN_CHECKPOINT) in e for e in report.errors)


def test_normalize_digits_and_signs() -> None:
    assert normalize("५") == "5"
    assert normalize("৫") == "5"
    assert normalize("x = 5") == "x = 5"
    assert int(parse_math("x = 5")) == 5
    assert int(parse_math("−3")) == -3


def test_malicious_strings_rejected() -> None:
    for raw in ("__import__('os')", "os.system('id')", "x" * 80, "(" * 12 + "1" + ")" * 12):
        try:
            parse_math(raw)
            raise AssertionError(f"should reject {raw!r}")
        except ParseError:
            pass
