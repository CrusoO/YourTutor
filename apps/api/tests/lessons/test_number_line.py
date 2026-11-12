"""Number-line figures on lesson beats: schema, range and authored-result rules."""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from app.lessons.loader import load_lessons
from app.lessons.schema import (
    NUMBER_LINE_LIMIT,
    FadedExampleBeat,
    Lesson,
    PredictBeat,
    WorkedExampleBeat,
    validate_lesson_dict,
)
from app.registries.paths import content_root, repo_root

FIXTURES = repo_root() / "packages" / "shared" / "fixtures" / "lessons"
FIXTURE = FIXTURES / "valid_number_line_lesson.json"


def _lesson() -> dict[str, Any]:
    return copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8"))["lesson"])


def _beat(lesson: dict[str, Any], kind: str) -> dict[str, Any]:
    return next(b for b in lesson["beats"] if b["kind"] == kind)


def test_a_valid_figure_on_predict_worked_and_faded_beats_is_accepted() -> None:
    lesson = _lesson()
    assert validate_lesson_dict(lesson) == []
    model = Lesson.model_validate(lesson)
    with_figure = [b.kind for b in model.beats if getattr(b, "number_line", None) is not None]
    assert with_figure == ["predict", "worked_example", "faded_example"]


def test_a_lesson_without_any_figure_is_unchanged() -> None:
    lesson = _lesson()
    for beat in lesson["beats"]:
        beat.pop("number_line", None)
        beat.pop("more_number_lines", None)
    assert validate_lesson_dict(lesson) == []


def test_a_subtraction_figure_moves_left_and_is_accepted() -> None:
    lesson = _lesson()
    extra = _beat(lesson, "worked_example")["more_number_lines"][0]
    assert extra["delta"] < 0 and extra["answer"] == extra["start"] + extra["delta"]
    assert validate_lesson_dict(lesson) == []


def test_answer_that_is_not_start_plus_delta_is_rejected() -> None:
    lesson = _lesson()
    _beat(lesson, "worked_example")["number_line"]["answer"] = -2
    assert "figure.answer_mismatch" in validate_lesson_dict(lesson)


@pytest.mark.parametrize(
    ("start", "delta"),
    [(NUMBER_LINE_LIMIT + 1, -2), (0, NUMBER_LINE_LIMIT + 1), (15, 10), (-15, -10), (4, 0)],
)
def test_out_of_range_or_empty_move_is_rejected(start: int, delta: int) -> None:
    lesson = _lesson()
    fig = _beat(lesson, "worked_example")["number_line"]
    fig.update(start=start, delta=delta, answer=start + delta)
    assert validate_lesson_dict(lesson) == ["figure.out_of_range"]


def test_unknown_kind_is_a_schema_error() -> None:
    lesson = _lesson()
    _beat(lesson, "worked_example")["number_line"]["kind"] = "bar_model"
    assert validate_lesson_dict(lesson) == ["schema.invalid"]


def test_extra_keys_and_non_integers_are_a_schema_error() -> None:
    lesson = _lesson()
    _beat(lesson, "worked_example")["number_line"]["colour"] = "red"
    assert validate_lesson_dict(lesson) == ["schema.invalid"]
    lesson = _lesson()
    _beat(lesson, "worked_example")["number_line"]["start"] = -8.5
    assert validate_lesson_dict(lesson) == ["schema.invalid"]


def test_figure_must_agree_with_the_authored_faded_answer() -> None:
    lesson = _lesson()
    _beat(lesson, "faded_example")["answer"] = "-4"
    assert validate_lesson_dict(lesson) == ["figure.result_mismatch"]


def test_figure_must_agree_with_the_worked_examples_last_step() -> None:
    lesson = _lesson()
    _beat(lesson, "worked_example")["steps"][-1]["en"] = "-8 → -2, so -8 + 5 = -2."
    assert validate_lesson_dict(lesson) == ["figure.result_mismatch"]


def test_predict_figure_answer_must_be_one_of_the_choices() -> None:
    lesson = _lesson()
    _beat(lesson, "predict")["choices"][0]["value"] = "8"
    assert validate_lesson_dict(lesson) == ["figure.result_mismatch"]


def test_the_typographic_minus_counts_as_a_minus() -> None:
    lesson = _lesson()
    faded = _beat(lesson, "faded_example")
    faded["answer"] = "−5"
    assert validate_lesson_dict(lesson) == []


def test_the_pilot_lesson_carries_checked_figures() -> None:
    lessons = load_lessons(content_root())  # raises when a rule fails
    pilot = lessons["LESSON.INTEGERS.OPERATIONS"]
    figs = [
        fig
        for b in pilot.beats
        if isinstance(b, PredictBeat | WorkedExampleBeat | FadedExampleBeat)
        and (fig := b.number_line) is not None
    ]
    got = [(f.start, f.delta, f.answer) for f in figs]
    assert got == [(-6, 15, 9), (-8, 5, -3), (-9, 4, -5)]
    worked = next(b for b in pilot.beats if isinstance(b, WorkedExampleBeat))
    sub = [f for f in worked.more_number_lines if f.delta < 0]
    assert sub and sub[0].start + sub[0].delta == sub[0].answer


def test_the_served_lesson_json_carries_the_figure() -> None:
    pilot = load_lessons(content_root())["LESSON.INTEGERS.OPERATIONS"]
    served = pilot.model_dump(mode="json", by_alias=True, exclude_none=True)
    worked = next(b for b in served["beats"] if b["kind"] == "worked_example")
    assert worked["number_line"] == {"kind": "number_line", "start": -8, "delta": 5, "answer": -3}
