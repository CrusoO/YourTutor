"""A hint that gives the answer away is never shown before hint 3 (FIX-PLAN B1-6)."""

from __future__ import annotations

from dataclasses import replace

from app.orchestrator.policy import GENERIC_SOCRATIC, policy
from app.orchestrator.types import Event
from app.verifier.check import leak_check
from tests.orchestrator.conftest import ask_hint, catalog_item, make_learner, make_session

SAFE_1 = "What undoes the operation?"
SAFE_2 = "Do the same to both sides."
LEAKS = "Just so you know, x is 5."
THIRD = "Subtract 7 from both sides."


def _with(**fields):  # type: ignore[no-untyped-def]
    return replace(catalog_item(), **fields)


def _practice(item):  # type: ignore[no-untyped-def]
    session = make_session(item)
    learner = make_learner()
    action = policy(learner, session, None)
    if action.type == "predict":
        policy(learner, session, Event(type="predict_response", text="maybe 5"))
        policy(learner, session, Event(type="continue"))
    return learner, session


def _hint_text(item) -> str:  # type: ignore[no-untyped-def]
    learner, session = _practice(item)
    action = ask_hint(learner, session)
    assert action.type == "hint", action
    return action.text or ""


def test_a_leaking_first_hint_is_replaced_by_the_next_authored_hint() -> None:
    item = _with(hints=((1, LEAKS), (2, SAFE_2), (3, THIRD)))
    text = _hint_text(item)
    assert text == SAFE_2
    assert not leak_check(text, "5", level=1)


def test_when_every_early_hint_leaks_a_neutral_question_is_shown() -> None:
    item = _with(hints=((1, LEAKS), (2, "So it equals 5."), (3, THIRD)))
    text = _hint_text(item)
    assert text == GENERIC_SOCRATIC
    assert text != THIRD  # never jump to the hint that may reveal


def test_a_safe_first_hint_is_unchanged() -> None:
    item = _with(hints=((1, SAFE_1), (2, SAFE_2), (3, THIRD)))
    assert _hint_text(item) == SAFE_1


def test_a_leaking_step_hint_is_replaced_too() -> None:
    item = _with(
        hints=((1, SAFE_1), (2, SAFE_2), (3, THIRD)),
        step_hints=("The value is 5.",),
    )
    learner, session = _practice(item)
    picker = policy(learner, session, Event(type="request_help"))
    assert picker.type == "ask_stuck_point"
    shown = policy(learner, session, Event(type="stuck_choice", response="0"))
    if shown.type == "hint":
        assert not leak_check(shown.text or "", "5", level=1), shown.text
