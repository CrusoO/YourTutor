"""Every wrong option of a multiple-choice item should name the idea that makes it tempting."""

from __future__ import annotations

from pathlib import Path

from app.content.schema import Item
from app.content.validator import format_report, load_bundle, unnamed_options, validate_bundle
from tests.content.conftest import minimal_item
from tests.content.test_live_roles import _approve


def _mcq(rules: list[dict] | None = None, item_id: str = "ITEM.MCQ.1") -> Item:
    data = minimal_item(item_id, stem=f"[{item_id}] Which is x in x + 7 = 12?", answer="five")
    data["type"] = "mcq"
    data["options"] = [
        {"id": "five", "en": "5"},
        {"id": "nineteen", "en": "19"},
        {"id": "minus5", "en": "-5"},
    ]
    data["answer"] = {"sympy": "five", "accept": []}
    data["solution_steps"] = [{"en": "Subtract 7."}, {"en": "x is five."}]
    data["misconception_rules"] = rules or []
    return Item.model_validate(data)


def test_a_wrong_option_that_names_no_idea_is_listed() -> None:
    assert unnamed_options(_mcq()) == ("nineteen", "minus5")


def test_options_named_by_a_rule_are_not_listed_by_id_or_by_text() -> None:
    rules = [
        {"id": "MC.ADD", "when_answer_equals": ["nineteen"]},
        {"id": "MC.SIGN", "when_answer_equals": ["-5"]},
    ]
    assert unnamed_options(_mcq(rules)) == ()


def test_the_right_answer_never_needs_a_rationale_and_other_types_are_skipped() -> None:
    assert "five" not in unnamed_options(_mcq())
    plain = Item.model_validate(minimal_item("ITEM.PLAIN"))
    assert unnamed_options(plain) == ()


def test_the_report_warns_and_lists_the_item(content_root: Path) -> None:
    bundle = load_bundle(content_root)
    bundle.items.append(_mcq())
    report = validate_bundle(bundle)
    assert any("ITEM.MCQ.1 wrong options name no misconception" in w for w in report.warnings)
    assert report.unnamed_distractors == [("ITEM.MCQ.1", ("nineteen", "minus5"))]
    assert "ITEM.MCQ.1: nineteen, minus5" in format_report(report)


def test_a_live_chapter_may_not_have_unnamed_wrong_options(content_root: Path) -> None:
    bundle = load_bundle(content_root)
    for item in bundle.items:
        _approve(item)
    overlay = bundle.overlays[0]
    overlay.live = True
    flawed = _mcq()
    flawed.skill_ids = [overlay.skill_ids[0]]
    _approve(flawed)
    bundle.items.append(flawed)
    errors = validate_bundle(bundle).errors
    assert any("wrong options that name no misconception: ITEM.MCQ.1" in e for e in errors)
