from __future__ import annotations

from pathlib import Path

from app.content.math_parse import ParseError, normalize, parse_math
from app.content.leak import hint_leaks_answer
from app.content.validator import (
    LIVE_MIN_CHECKPOINT,
    last_step_matches_answer,
    validate_path,
)
from tests.content.conftest import loc, minimal_item, minimal_skill, write_yaml


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


def test_hint_leak_uses_tokens_not_substrings() -> None:
    assert hint_leaks_answer("The answer is 5", "5")
    assert not hint_leaks_answer("Add 10 to both sides.", "0")
    assert not hint_leaks_answer("Add 10 to both sides.", "1")
    assert not hint_leaks_answer("Do both sides become the same?", "one")
    assert hint_leaks_answer("Undo the 8 on both sides.", "8")


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
        minimal_item("ITEM.P0", pool="checkpoint"),
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


def test_stem_answer_mismatch_is_error(content_root: Path) -> None:
    write_yaml(
        content_root / "items" / "wrongpair.yaml",
        minimal_item("ITEM.WRONG", answer="19", last_step="x = 19"),
    )
    report = validate_path(content_root)
    assert any("does not match answer.sympy" in e for e in report.errors)


def test_unsolvable_stem_is_manual_review(content_root: Path) -> None:
    data = minimal_item("ITEM.WORD")
    data["stem"] = {
        "en": "A number plus seven is twelve. What is the number?",
        "ne": "<Nepali — to be filled by reviewer>",
        "as": "<Assamese — to be filled by reviewer>",
    }
    write_yaml(content_root / "items" / "word.yaml", data)
    report = validate_path(content_root)
    assert report.ok, report.errors
    assert "ITEM.WORD" in report.manual_review
    assert "ITEM.WORD" in report.needs_teacher_check


def test_verify_equation_matches_answer(content_root: Path) -> None:
    data = minimal_item("ITEM.WORD.OK")
    data["stem"] = {
        "en": "A number plus seven is twelve. What is the number?",
        "ne": "<Nepali — to be filled by reviewer>",
        "as": "<Assamese — to be filled by reviewer>",
    }
    data["verify"] = "x + 7 = 12"
    write_yaml(content_root / "items" / "word_ok.yaml", data)
    report = validate_path(content_root)
    assert report.ok, report.errors
    assert "ITEM.WORD.OK" not in report.manual_review
    assert "ITEM.WORD.OK" not in report.needs_teacher_check


def test_verify_mismatch_is_error(content_root: Path) -> None:
    data = minimal_item("ITEM.WORD.BAD", answer="19", last_step="x = 19")
    data["stem"] = {
        "en": "A number plus seven is twelve. What is the number?",
        "ne": "<Nepali — to be filled by reviewer>",
        "as": "<Assamese — to be filled by reviewer>",
    }
    data["verify"] = "x + 7 = 12"
    write_yaml(content_root / "items" / "word_bad.yaml", data)
    report = validate_path(content_root)
    assert any("verify solves to" in e for e in report.errors)


def test_live_blocked_by_unapproved_needs_teacher_check(content_root: Path) -> None:
    write_yaml(
        content_root / "overlays" / "live.yaml",
        {
            "id": "live_ch",
            "board": "bhutan",
            "grade": 9,
            "chapter": "lin",
            "skill_ids": ["MATH.S1"],
            "live": True,
        },
    )
    data = minimal_item("ITEM.WORD.LIVE")
    data["stem"] = {
        "en": "How old is the sister?",
        "ne": "<Nepali — to be filled by reviewer>",
        "as": "<Assamese — to be filled by reviewer>",
    }
    write_yaml(content_root / "items" / "word_live.yaml", data)
    report = validate_path(content_root)
    assert any("needs_teacher_check" in e and "live_ch" in e for e in report.errors)


def test_validator_report_counts(content_root: Path) -> None:
    report = validate_path(content_root)
    assert report.stats["by_pool"]["practice"] >= 1
    assert "MATH.S1" in report.stats["by_skill"]
    assert report.stats["distinct_stems_by_pool"]["practice"] >= 5
    assert report.stats["needs_teacher_check_count"] == len(report.needs_teacher_check)


def test_duplicate_stem_in_pool_fails(content_root: Path) -> None:
    shared = "Two pens cost the same amount in this shared stem."
    write_yaml(content_root / "items" / "dup_a.yaml", minimal_item("ITEM.DUPA", stem=shared))
    write_yaml(content_root / "items" / "dup_b.yaml", minimal_item("ITEM.DUPB", stem=shared))
    report = validate_path(content_root)
    assert any("duplicate stem" in e for e in report.errors)


def test_bkt_params_must_be_open_unit_interval(content_root: Path) -> None:
    data = minimal_skill("MATH.S2")
    data["bkt"] = {"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.6, "p_guess": 0.5}
    write_yaml(content_root / "skills" / "s2.yaml", data)
    report = validate_path(content_root)
    assert any("p_slip + p_guess" in e for e in report.errors)


def test_substitution_and_solution_count_verify(content_root: Path) -> None:
    yes = minimal_item("ITEM.CHECK.YES", answer="yes", last_step="The correct option is yes.")
    yes["type"] = "mcq"
    yes["options"] = [
        {"id": "yes", "en": "Yes"},
        {"id": "no", "en": "No"},
    ]
    yes["stem"] = loc("Does x = 4 solve 2x + 1 = 9?")
    yes["verify"] = {"kind": "substitution", "equation": "2x + 1 = 9", "value": "4"}
    yes["answer"] = {"sympy": "yes", "accept": ["yes"]}
    write_yaml(content_root / "items" / "check_yes.yaml", yes)

    count = minimal_item("ITEM.ID.EVERY", answer="every", last_step="The correct option is every.")
    count["type"] = "mcq"
    count["options"] = [
        {"id": "none", "en": "No solution"},
        {"id": "one", "en": "One solution"},
        {"id": "every", "en": "Every x works"},
    ]
    count["stem"] = loc("How many solutions does 2(x + 3) = 2x + 6 have?")
    count["verify"] = {"kind": "solution_count", "equation": "2(x + 3) = 2x + 6"}
    count["answer"] = {"sympy": "every", "accept": ["every"]}
    write_yaml(content_root / "items" / "id_every.yaml", count)

    report = validate_path(content_root)
    assert report.ok, report.errors
    assert "ITEM.CHECK.YES" not in report.needs_teacher_check
    assert "ITEM.ID.EVERY" not in report.needs_teacher_check


def test_one_x_banned(content_root: Path) -> None:
    write_yaml(
        content_root / "items" / "onex.yaml",
        minimal_item("ITEM.ONEX", stem="Solve for x: 1x + 4 = 10"),
    )
    report = validate_path(content_root)
    assert any("1x" in e for e in report.errors)


def test_hint1_diversity_and_reuse(content_root: Path) -> None:
    for index in range(5):
        data = minimal_item(f"ITEM.P{index}", pool="practice", stem=_stem(index))
        data["hints"][0]["en"] = "Same first hint for every practice item."
        data["hints"][1]["en"] = "Same second hint for every practice item."
        write_yaml(content_root / "items" / f"p{index}.yaml", data)
    report = validate_path(content_root)
    assert any("distinct hint-1" in e for e in report.errors)
    assert any("hint reused" in w for w in report.warnings)


def test_practice_structure_minimum(content_root: Path) -> None:
    for index in range(5):
        write_yaml(
            content_root / "items" / f"p{index}.yaml",
            minimal_item(
                f"ITEM.P{index}",
                pool="practice",
                stem=f"Solve for x: x + {7 + index} = {12 + index}",
            ),
        )
    report = validate_path(content_root)
    assert any("stem structures" in e for e in report.errors)


def _stem(index: int) -> str:
    templates = (
        "Solve for x: x + {n} = {m}",
        "Find x if x - {n} = {m}",
        "What number plus {n} is {m}?",
        "x + {n} equals {m}. Solve.",
        "Compute x in x - {n} = {m}.",
    )
    return templates[index].format(n=7 + index, m=12 + index)


def test_malicious_strings_rejected() -> None:
    for raw in ("__import__('os')", "os.system('id')", "x" * 80, "(" * 12 + "1" + ")" * 12):
        try:
            parse_math(raw)
            raise AssertionError(f"should reject {raw!r}")
        except ParseError:
            pass
