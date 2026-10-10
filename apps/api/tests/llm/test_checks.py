"""G4 step 2: pure post-checks, in order: schema, leak, grounding, length, tone, moderation,
language. The first failure wins and has a stable code."""

from __future__ import annotations

from typing import Any

import pytest

from app.llm.checks import run_checks
from app.llm.prompt import PromptContext
from app.llm.purposes import Purpose
from app.llm.rules import load_llm_rules
from app.registries.loaders import load_grade_bands

BANDS = {b.id: b for b in load_grade_bands()}
HINT_FIELDS = {
    "item_stem": "Solve x + 4 = 10",
    "hint_level": "1",
    "authored_hint": "Undo the + 4 on both sides.",
}


def _ctx(purpose: Purpose = Purpose.personalise_hint, **over: Any) -> PromptContext:
    base: dict[str, Any] = dict(
        purpose=purpose,
        band=BANDS["lower_secondary"],
        language="en",
        source="Take 4 off both sides to keep the balance.",
        glossary={},
        forbidden_answer="6",
        fields=dict(HINT_FIELDS),
    )
    base.update(over)
    return PromptContext(**base)


def test_a_good_hint_passes_and_is_returned_trimmed() -> None:
    out = run_checks(_ctx(), "  Think about what undoes adding 4.  ")
    assert out.ok and out.code is None
    assert out.text == "Think about what undoes adding 4."


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("", "schema.empty"),
        ("   \n ", "schema.empty"),
        ("# Hint\nUndo the 4.", "schema.format"),
        ("Undo the **4** first.", "schema.format"),
        ("First line.\n\nSecond paragraph.", "schema.format"),
        ("See http://example.org for more.", "schema.format"),
    ],
)
def test_schema_failures(raw: str, code: str) -> None:
    assert run_checks(_ctx(), raw).code == code


@pytest.mark.parametrize("raw", ["The answer is 6.", "So x equals six.", "x = 12 / 2", "Try 6."])
def test_a_reply_that_leaks_the_forbidden_answer_is_refused(raw: str) -> None:
    out = run_checks(_ctx(), raw)
    assert out.code == "leak" and not out.ok


def test_numbers_must_come_from_the_authored_material() -> None:
    assert run_checks(_ctx(forbidden_answer=None), "Take 4 off both sides.").ok
    out = run_checks(_ctx(forbidden_answer=None), "Take 7 off both sides.")
    assert out.code == "grounding.number"


def test_encouragement_may_not_contain_numbers_at_all() -> None:
    ctx = _ctx(Purpose.encourage, source="", forbidden_answer=None, fields={"trigger": "t"})
    assert run_checks(ctx, "That was a hard one and you kept going.").ok
    assert run_checks(ctx, "You got 3 in a row.").code == "grounding.number"


def test_citations_are_required_and_must_be_known_when_passages_are_given() -> None:
    ctx = _ctx(
        Purpose.adapt_explanation,
        forbidden_answer=None,
        fields={"item_stem": "Solve x + 4 = 10", "passage_ids": "P1,P2"},
    )
    assert run_checks(ctx, "Take 4 off both sides [P1].").ok
    assert run_checks(ctx, "Take 4 off both sides.").code == "grounding.citation"
    assert run_checks(ctx, "Take 4 off both sides [P9].").code == "grounding.citation"


def test_length_follows_the_grade_band_word_limit() -> None:
    primary = _ctx(band=BANDS["primary"], forbidden_answer=None)  # 25 words
    ok = " ".join(["word"] * 25)
    assert run_checks(primary, ok).ok
    assert run_checks(primary, ok + " extra").code == "length"
    assert run_checks(_ctx(forbidden_answer=None), ok + " extra").ok  # band C allows 60


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("You are so smart, nice work.", "tone.praise"),
        ("Only a genius would find this.", "tone.praise"),
        ("You should know this by now.", "tone.shaming"),
        ("Your classmates finished faster.", "tone.shaming"),
        ("Stupid mistake, try again.", "tone.shaming"),
    ],
)
def test_tone_rules(raw: str, code: str) -> None:
    assert run_checks(_ctx(forbidden_answer=None), raw).code == code


def test_praise_of_strategy_and_effort_is_fine() -> None:
    ctx = _ctx(Purpose.encourage, source="", forbidden_answer=None, fields={"trigger": "t"})
    assert run_checks(ctx, "You tried a new way when the first one stalled. That takes effort.").ok


def test_moderation_blocks_whole_words_only() -> None:
    ctx = _ctx(forbidden_answer=None)
    assert run_checks(ctx, "That is a hell of a problem.").code == "moderation"
    assert run_checks(ctx, "Undo the shell step first.").ok  # "hell" inside "shell" is fine


@pytest.mark.parametrize(
    ("language", "raw", "ok"),
    [
        ("en", "Undo the step that adds four.", True),
        ("en", "दोनों तिर चार घटाउनुहोस्।", False),
        ("ne", "दुवै तिरबाट चार घटाउनुहोस्।", True),
        ("ne", "Take four off both sides.", False),
        ("ne", "दुवै तिर equation मा चार घटाउनुहोस्।", True),  # one exact term in English is fine
    ],
)
def test_the_reply_must_be_in_the_requested_language_script(
    language: str, raw: str, ok: bool
) -> None:
    out = run_checks(_ctx(language=language, forbidden_answer=None, source=""), raw)
    if ok:
        assert out.ok, out.code
    else:
        assert out.code == "language"


def test_order_is_schema_then_leak_then_length() -> None:
    long_leak = "The answer is 6. " + " ".join(["word"] * 80)
    assert run_checks(_ctx(), long_leak).code == "leak"  # leak before length
    assert run_checks(_ctx(), "").code == "schema.empty"  # schema before everything


def test_explain_back_needs_a_grade_line_and_feedback() -> None:
    ctx = _ctx(
        Purpose.grade_explain_back,
        forbidden_answer="6",
        fields={"student_text": "I took 4 from both sides.", "rubric": "Mentions undoing + 4."},
    )
    good = run_checks(ctx, "GRADE: good\nYou named the step that undoes the + 4. Nice care.")
    assert good.ok and good.grade == "good"
    assert good.text == "You named the step that undoes the + 4. Nice care."
    assert run_checks(ctx, "Looks fine to me.").code == "schema.grade"
    assert run_checks(ctx, "GRADE: excellent\nGreat.").code == "schema.grade"
    assert run_checks(ctx, "GRADE: partly").code == "schema.empty"
    assert run_checks(ctx, "GRADE: partly\nThe answer is 6.").code == "leak"


def test_the_rules_file_loads_and_is_not_empty() -> None:
    rules = load_llm_rules()
    assert "stupid" in rules.shaming_phrases and "idiot" in rules.blocked_terms
