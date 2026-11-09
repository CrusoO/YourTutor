"""A lesson quiz's marked answer is checked by the maths verifier, not taken on the model's word."""

from __future__ import annotations

from typing import Any

import pytest

from app.explain.quiz_verify import math_spans, verify_choice
from app.explain.service_lesson import clean_lesson, clean_opening, clean_rest


@pytest.mark.parametrize(
    ("text", "spans"),
    [
        ("Solve 3x + 5 = 20 for x.", ["3x + 5 = 20"]),
        ("What is 15 - 3?", ["15 - 3"]),
        ("What is 7 × 8?", ["7 × 8"]),
        ("Which step is first for the two-step equation 2x - 4 = 10?", ["2x - 4 = 10"]),
        ("Why is balance useful?", []),
        ("Solve 2x + 3 = 11 and then x + y = 4", ["2x + 3 = 11", "x + y = 4"]),
    ],
)
def test_math_spans(text: str, spans: list[str]) -> None:
    assert math_spans(text) == spans


@pytest.mark.parametrize(
    ("question", "options", "marked", "status"),
    [
        ("Solve 3x + 5 = 20 for x.", ["x = 4", "x = 5", "x = 15", "x = 25"], 1, "verified"),
        ("Solve 3x + 5 = 20 for x.", ["4", "5", "15", "25"], 1, "verified"),
        ("What is 15 - 3?", ["10", "11", "12", "13"], 2, "verified"),
        ("What is 7 × 8?", ["54", "56", "58", "64"], 1, "verified"),
        ("What is 1/2 + 1/4?", ["1/4", "2/6", "3/4", "1"], 2, "verified"),
        # the mark is wrong
        ("Solve 3x + 5 = 20 for x.", ["4", "5", "15", "25"], 0, "conflict"),
        ("What is 15 - 3?", ["10", "11", "13", "14"], 0, "conflict"),
        # two options are worth the same
        ("What is 15 - 3?", ["10", "11", "12", "12"], 2, "conflict"),
        # the right value is there but "none of these" was marked
        ("What is 2 + 2?", ["4", "none of these", "5", "6"], 1, "conflict"),
        # nothing the solver can read: kept, not machine-checked
        (
            "Which step comes first in 2x + 3 = 11?",
            ["Subtract 3", "Divide by 2", "Add 3", "Multiply"],
            0,
            "unverified",
        ),
        ("What does balance mean?", ["equal", "bigger", "smaller", "none"], 0, "unverified"),
        (
            "A train goes 60 km in 2 hours. What is its speed?",
            ["20", "30", "40", "60"],
            1,
            "unverified",
        ),
        ("Solve 2x + 3 = 11 and x + y = 4", ["4", "5", "6", "7"], 0, "unverified"),
        # a number outside the sum: never guess from part of a question
        ("What is 3/4 of 8?", ["4", "6", "8", "12"], 1, "unverified"),
        ("What is 3x when 3x + 5 = 17?", ["4", "12", "17", "5"], 1, "unverified"),
        # fewer than two options are plain values
        ("What is 2 + 2?", ["four", "five", "six", "seven"], 0, "unverified"),
        ("What is 2 + 2?", ["4", "none of these", "all of them", "n/a"], 0, "unverified"),
    ],
)
def test_verify_choice(question: str, options: list[str], marked: int, status: str) -> None:
    assert verify_choice(question, options, marked).status == status


def test_a_marked_option_that_is_not_a_value_is_unverified_when_no_value_matches() -> None:
    options = ["10", "11", "none of these", "13"]
    assert verify_choice("What is 15 - 3?", options, 2).status == "unverified"


def _check(question: str, options: list[str], correct: int) -> dict[str, Any]:
    return {
        "kind": "check",
        "question": question,
        "options": options,
        "correct": correct,
        "feedback_per_option": ["a", "b", "c", "d"],
        "hint_ladder": ["h1", "h2", "h3"],
    }


def _hook() -> dict[str, Any]:
    return {"kind": "hook", "text": "A story about balance.", "question": "What is balance?"}


def _explain() -> dict[str, Any]:
    return {"kind": "explain", "text": "Equal things stay equal when you treat both sides alike."}


def _blocks(*checks: dict[str, Any]) -> list[dict[str, Any]]:
    return [_hook(), _explain(), *checks, _explain(), {"kind": "recap", "points": ["p1", "p2"]}]


def test_a_verified_check_is_kept_and_marked_verified() -> None:
    good = _check("What is 15 - 3?", ["10", "11", "12", "13"], 2)
    lesson = clean_lesson({"blocks": _blocks(good)})
    assert lesson is not None
    check = next(b for b in lesson["blocks"] if b["kind"] == "check")
    assert check["verified"] is True and check["correct"] == 2


def test_a_check_with_a_wrong_mark_is_dropped_not_corrected() -> None:
    wrong = _check("What is 15 - 3?", ["10", "11", "12", "13"], 0)
    ok = _check("Why do we balance equations?", ["a", "b", "c", "d"], 1)
    lesson = clean_lesson({"blocks": _blocks(wrong, ok)})
    assert lesson is not None
    checks = [b for b in lesson["blocks"] if b["kind"] == "check"]
    assert [c["question"] for c in checks] == ["Why do we balance equations?"]


def test_a_check_the_solver_cannot_read_is_kept_and_marked_unverified() -> None:
    concept = _check("Why do we balance equations?", ["a", "b", "c", "d"], 1)
    lesson = clean_lesson({"blocks": _blocks(concept)})
    assert lesson is not None
    check = next(b for b in lesson["blocks"] if b["kind"] == "check")
    assert check["verified"] is False and check["correct"] == 1


def test_a_lesson_whose_only_check_is_wrong_has_no_check_to_land_on() -> None:
    wrong = _check("What is 15 - 3?", ["10", "11", "12", "13"], 0)
    assert clean_rest({"blocks": [_explain(), _explain(), wrong]}) is None


def test_a_prediction_with_a_wrong_mark_is_dropped_so_the_opening_is_unusable() -> None:
    predict = {
        "kind": "predict",
        "prompt": "What is 15 - 3?",
        "options": ["10", "11", "12", "13"],
        "correct": 0,
    }
    assert clean_opening({"blocks": [_hook(), predict]}) is None


def test_a_conceptual_prediction_is_kept_and_unverified() -> None:
    predict = {
        "kind": "predict",
        "prompt": "Will the scale tip if you add weight to one side?",
        "options": ["Yes", "No"],
        "correct": 0,
    }
    opening = clean_opening({"blocks": [_hook(), predict]})
    assert opening is not None and opening["blocks"][1]["verified"] is False


def test_a_free_text_prediction_has_nothing_to_verify() -> None:
    predict = {"kind": "predict", "prompt": "What do you think?", "free_text": True}
    opening = clean_opening({"blocks": [_hook(), predict]})
    assert opening is not None and "verified" not in opening["blocks"][1]
