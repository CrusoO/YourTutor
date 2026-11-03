"""The interactive lesson: how the model's JSON is cleaned, and the gates and retries around it."""

from __future__ import annotations

import json
from typing import Any

from app.explain import service_lesson as sl
from app.explain.service import Gate
from app.llm.provider import FakeProvider, ProviderError

OPEN = Gate(enabled=True, allowed=True)


def _blocks() -> list[dict[str, Any]]:
    return [
        {"kind": "hook", "text": "A surprising fact.", "question": "How can that be?"},
        {
            "kind": "predict",
            "prompt": "What happens?",
            "options": ["A", "B"],
            "correct": 1,
            "reveal_after": "B happens.",
        },
        {
            "kind": "widget",
            "widget_kind": "slider_sim",
            "spec": {
                "variable": "width",
                "unit": "nm",
                "min": 0,
                "max": 4,
                "step": 0.5,
                "formula": "exp(-2*width)",
                "output_label": "chance",
                "output_unit": "",
            },
            "controls": [],
            "what_to_notice": "notice how it falls",
        },
        {"kind": "explain", "text": "Because waves leak."},
        {
            "kind": "check",
            "question": "Thicker?",
            "options": ["a", "b", "c", "d"],
            "correct": 2,
            "feedback_per_option": ["1", "2", "3", "4"],
            "hint_ladder": ["h1", "h2", "h3"],
        },
        {
            "kind": "recap",
            "three_bullets": ["one", "two", "three"],
            "spaced_review_question": "Why?",
        },
    ]


def _lesson_json(blocks: list[dict[str, Any]] | None = None) -> str:
    return json.dumps(
        {"level": "school", "objectives": ["Explain it"], "blocks": blocks or _blocks()}
    )


def test_a_well_formed_lesson_is_kept_in_order() -> None:
    out = sl.build_lesson("what is tunnelling", "en", OPEN, FakeProvider([_lesson_json()]), "m")
    assert out["kind"] == "lesson"
    assert [b["kind"] for b in out["blocks"]] == [
        "hook",
        "predict",
        "widget",
        "explain",
        "check",
        "recap",
    ]


def test_type_is_accepted_when_a_model_writes_it_instead_of_kind() -> None:
    renamed = [{("type" if k == "kind" else k): v for k, v in b.items()} for b in _blocks()]
    cleaned = sl.clean_lesson({"blocks": renamed})
    assert cleaned is not None
    assert [b["kind"] for b in cleaned["blocks"]] == [
        "hook",
        "predict",
        "widget",
        "explain",
        "check",
        "recap",
    ]
    assert cleaned["blocks"][2]["widget_kind"] == "slider_sim"


def test_a_widget_named_by_its_subtype_in_kind_or_type_is_still_a_widget() -> None:
    steps = {"steps": [{"label": "a", "description": "x"}, {"label": "b", "description": "y"}]}
    for key in ("kind", "type"):
        raw = {key: "step_through", "spec": steps, "what_to_notice": "n"}
        cleaned = sl.clean_lesson({"blocks": [*_blocks()[:2], raw, *_blocks()[3:]]})
        assert cleaned is not None
        assert cleaned["blocks"][2]["widget_kind"] == "step_through"


def test_unknown_and_malformed_blocks_are_dropped_and_too_few_rejects_the_lesson() -> None:
    junk: list[Any] = [
        {"kind": "quiz"},
        "text",
        {"kind": "hook"},
        {"kind": "predict", "prompt": ""},
    ]
    assert sl.clean_lesson({"blocks": junk}) is None
    assert sl.clean_lesson({"blocks": "nope"}) is None
    assert sl.clean_lesson(None) is None


def test_the_token_budget_leaves_room_for_thinking_except_on_groq() -> None:
    assert sl._max_tokens("anthropic/claude-haiku-5-5") == 8000
    assert sl._max_tokens("openrouter/x/y") == 8000
    assert sl._max_tokens("groq/openai/gpt-oss-120b") == 4000


def test_the_prompt_names_the_block_key() -> None:
    system = sl.build_prompt("q", "en", restricted=False).system
    assert 'Never write "type" instead of "kind"' in system
    assert "widget_kind" in system


def test_gate_off_and_no_consent_call_nothing() -> None:
    provider = FakeProvider([_lesson_json()])
    off = sl.build_lesson("q about maths", "en", Gate(enabled=False, allowed=True), provider, "m")
    no = sl.build_lesson("q about maths", "en", Gate(enabled=True, allowed=False), provider, "m")
    assert off == {"kind": "unavailable", "reason": "off"}
    assert no == {"kind": "unavailable", "reason": "consent"}
    assert provider.calls == []


def test_cut_off_json_is_retried_once_then_unavailable() -> None:
    cut = _lesson_json()[:120]
    provider = FakeProvider([cut, cut])
    out = sl.build_lesson("what is tunnelling", "en", OPEN, provider, "m")
    assert out == {"kind": "unavailable", "reason": "checks"}
    assert len(provider.calls) == sl.MAX_ATTEMPTS


def test_a_cut_off_first_try_is_recovered_by_the_second() -> None:
    provider = FakeProvider([_lesson_json()[:120], _lesson_json()])
    out = sl.build_lesson("what is tunnelling", "en", OPEN, provider, "m")
    assert out["kind"] == "lesson"
    assert len(provider.calls) == 2


def test_a_provider_error_is_retried_then_unavailable() -> None:
    provider = FakeProvider([ProviderError("down"), ProviderError("down")])
    out = sl.build_lesson("what is tunnelling", "en", OPEN, provider, "m")
    assert out == {"kind": "unavailable", "reason": "provider_error"}


def test_the_refuse_signal_becomes_out_of_scope() -> None:
    out = sl.build_lesson("what is tunnelling", "en", OPEN, FakeProvider(['{"refuse": true}']), "m")
    assert out["kind"] == "out_of_scope"


def test_the_question_travels_inside_student_text_tags() -> None:
    provider = FakeProvider([_lesson_json()])
    sl.build_lesson("what is tunnelling", "en", OPEN, provider, "m")
    assert "<student_text>" in provider.calls[0].user
    assert "what is tunnelling" in provider.calls[0].user
