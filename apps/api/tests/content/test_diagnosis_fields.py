"""G2: item fields for diagnosis and the stuck-point picker, their drafts, and the leak check."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.content.diagnosis_fields import draft_fields
from app.content.leak import hint_leaks_answer
from app.content.schema import Item
from app.content.signatures import item_content_hash
from app.content.validator import validate_path
from app.registries.paths import content_root


def _payload(**extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "ITEM.T.1",
        "skill_ids": ["S.TWO"],
        "difficulty": 0.5,
        "type": "expression",
        "pool": "practice",
        "role": "procedure",
        "stem": {"en": "Solve for x: 3x + 2 = 14"},
        "answer": {"sympy": "4", "accept": ["4", "x=4"]},
        "solution_steps": [
            {"en": "Subtract 2 from both sides."},
            {"en": "3x = 14 - 2"},
            {"en": "Divide both sides by 3."},
            {"en": "x = 4"},
        ],
        "hints": [
            {"level": 1, "en": "Which operation do you undo first?"},
            {"level": 2, "en": "Undo the plus, then the times."},
            {"level": 3, "en": "Subtract first, then divide."},
        ],
        "prediction_prompt": {"en": "Will x be a whole number?"},
    }
    base.update(extra)
    return base


# ---- schema -------------------------------------------------------------------------------


def test_all_new_fields_are_optional() -> None:
    item = Item.model_validate(_payload())
    assert item.step_hints == [] and item.hint_restate is None
    assert item.slip_patterns == [] and item.prereq_signatures == []
    assert item.intermediate_values == [] and item.min_plausible_ms is None


def test_step_hints_must_line_up_with_the_solution_steps() -> None:
    steps = [{"en": "a"}, {"en": "b"}, {"en": "c"}, {"en": "d"}]
    assert Item.model_validate(_payload(step_hints=steps)).step_hints
    with pytest.raises(ValidationError, match="step_hints"):
        Item.model_validate(_payload(step_hints=steps[:2]))


def test_slip_pattern_kinds_are_closed() -> None:
    ok = [
        {"kind": "sign_flip"},
        {"kind": "off_by", "max_distance": 2},
        {"kind": "values", "values": ["9"]},
    ]
    assert len(Item.model_validate(_payload(slip_patterns=ok)).slip_patterns) == 3
    with pytest.raises(ValidationError):
        Item.model_validate(_payload(slip_patterns=[{"kind": "magic"}]))
    with pytest.raises(ValidationError):
        Item.model_validate(_payload(slip_patterns=[{"kind": "values"}]))  # values need values


def test_prereq_signature_needs_a_skill_and_values() -> None:
    sig = [{"skill_id": "S.INTEGERS", "values": ["-4x"]}]
    assert Item.model_validate(_payload(prereq_signatures=sig)).prereq_signatures
    with pytest.raises(ValidationError):
        Item.model_validate(_payload(prereq_signatures=[{"skill_id": "S.INTEGERS", "values": []}]))


def test_min_plausible_ms_has_a_floor() -> None:
    assert Item.model_validate(_payload(min_plausible_ms=2500)).min_plausible_ms == 2500
    with pytest.raises(ValidationError):
        Item.model_validate(_payload(min_plausible_ms=100))


def test_editing_a_step_hint_changes_the_approval_hash() -> None:
    steps = [{"en": "a"}, {"en": "b"}, {"en": "c"}, {"en": "d"}]
    one = Item.model_validate(_payload(step_hints=steps, hint_restate={"en": "Read it again."}))
    two = Item.model_validate(
        _payload(step_hints=[*steps[:3], {"en": "changed"}], hint_restate={"en": "Read it again."})
    )
    assert item_content_hash(one) != item_content_hash(two)
    three = Item.model_validate(_payload(step_hints=steps, hint_restate={"en": "Changed."}))
    assert item_content_hash(one) != item_content_hash(three)


# ---- drafts -------------------------------------------------------------------------------


def test_draft_step_hints_cover_every_step_and_never_leak_the_answer() -> None:
    item = Item.model_validate(_payload())
    fields = draft_fields(item)
    hints = [h["en"] for h in fields["step_hints"]]
    assert len(hints) == len(item.solution_steps)
    for text in hints:
        assert not hint_leaks_answer(text, item.answer.sympy), text
        assert not any(ch.isdigit() for ch in text), text  # no numbers at all in a draft step hint


def test_draft_step_hints_do_not_leak_when_the_answer_is_small() -> None:
    item = Item.model_validate(
        _payload(
            answer={"sympy": "2", "accept": ["2"]},
            solution_steps=[{"en": f"Step {i}."} for i in range(1, 5)],
        )
    )
    for hint in draft_fields(item)["step_hints"]:
        assert not hint_leaks_answer(hint["en"], "2")


def test_a_coefficient_next_to_a_letter_is_not_glued_to_the_mask() -> None:
    item = Item.model_validate(
        _payload(
            solution_steps=[
                {"en": "Subtract 2x from both sides."},
                {"en": "x + 2 = 9"},
                {"en": "x = 4"},
            ]
        )
    )
    first = draft_fields(item)["step_hints"][0]["en"]
    assert "numberx" not in first and "x term" in first


def test_the_first_equation_step_has_no_step_before_it() -> None:
    item = Item.model_validate(_payload(solution_steps=[{"en": "x + 4 = 14"}, {"en": "x = 10"}]))
    first = draft_fields(item)["step_hints"][0]["en"]
    assert "step before" not in first and "equation" in first


def test_sentences_are_not_intermediate_values() -> None:
    item = Item.model_validate(
        _payload(
            solution_steps=[
                {"en": "The sentence becomes x + 4 = 22"},
                {"en": "x + 4 = 22"},
                {"en": "x = 18"},
            ]
        )
    )
    values = draft_fields(item)["intermediate_values"]
    assert not any("sentence" in v for v in values)
    assert "x + 4 = 22" in values


def test_draft_restate_repeats_the_question_and_asks_what_is_wanted() -> None:
    fields = draft_fields(Item.model_validate(_payload()))
    text = fields["hint_restate"]["en"]
    assert "3x + 2 = 14" in text
    assert "?" in text


def test_numeric_answers_get_slip_patterns_and_others_do_not() -> None:
    assert draft_fields(Item.model_validate(_payload()))["slip_patterns"] == [
        {"kind": "sign_flip"},
        {"kind": "off_by", "max_distance": 1},
    ]
    mcq = Item.model_validate(
        _payload(
            type="mcq",
            answer={"sympy": "a", "accept": ["a"]},
            options=[{"id": "a", "en": "x"}, {"id": "b", "en": "y"}],
        )
    )
    assert draft_fields(mcq)["slip_patterns"] == []


def test_intermediate_values_come_from_the_non_final_equations() -> None:
    values = draft_fields(Item.model_validate(_payload()))["intermediate_values"]
    assert "12" in values and "3x = 14 - 2" in values
    assert "4" not in values and "x = 4" not in values


def test_min_plausible_ms_scales_with_the_stem_and_stays_in_range() -> None:
    short = draft_fields(Item.model_validate(_payload(stem={"en": "1 + 1?"})))["min_plausible_ms"]
    long = draft_fields(Item.model_validate(_payload(stem={"en": "word " * 80})))[
        "min_plausible_ms"
    ]
    assert 2000 <= short < long <= 8000


def test_drafts_are_deterministic() -> None:
    item = Item.model_validate(_payload())
    assert draft_fields(item) == draft_fields(item)


# ---- the seed content ---------------------------------------------------------------------


def test_every_seed_practice_item_has_clean_diagnosis_fields() -> None:
    report = validate_path(content_root())
    assert report.bundle is not None
    problems: list[str] = []
    practice = [i for i in report.bundle.items if i.pool.value == "practice"]
    assert practice
    for item in practice:
        if len(item.step_hints) != len(item.solution_steps):
            problems.append(f"{item.id}: step_hints missing")
            continue
        if item.hint_restate is None:
            problems.append(f"{item.id}: hint_restate missing")
        for hint in item.step_hints:
            if hint_leaks_answer(hint.en, item.answer.sympy):
                problems.append(f"{item.id}: step hint leaks")
    assert not problems, problems[:10]
    assert not [e for e in report.errors if "step hint" in e or "restate" in e], report.errors[:5]


def test_validator_reports_a_leaking_step_hint(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.content.validator import _check_diagnosis_fields

    leaky = Item.model_validate(
        _payload(
            step_hints=[{"en": "x"}, {"en": "x"}, {"en": "x"}, {"en": "The answer is 4"}],
            hint_restate={"en": "Read: the answer is 4"},
        )
    )
    errors: list[str] = []
    _check_diagnosis_fields(leaky, errors)
    assert any("step hint" in e for e in errors)
    assert any("restate" in e for e in errors)
