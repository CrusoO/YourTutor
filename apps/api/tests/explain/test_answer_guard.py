"""The tutor chat never gives away the answer to the item on screen (FIX-PLAN B1-7)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ItemRow, SessionRow
from app.explain import service_chat
from app.explain.answer_guard import (
    STRICT_RULE,
    WITHHOLD_RULE,
    ActiveItem,
    enforce_no_leak,
    leaks,
)
from tests.conftest import World, auth_header

ANSWER = "12"
SAFE = "What do you do to both sides first?"


def _active(
    hints: tuple[tuple[int, dict[str, str]], ...] = ((1, {"en": SAFE}),),
    *,
    may_reveal: bool = False,
) -> ActiveItem:
    return ActiveItem("ITEM.G.1", (ANSWER, "x=12"), hints, may_reveal)


class Scripted:
    """A model stand-in that returns the next scripted result and records the rule it was given."""

    def __init__(self, *results: dict[str, Any]) -> None:
        self.results = list(results)
        self.rules: list[str | None] = []

    def __call__(self, rule: str | None) -> dict[str, Any]:
        self.rules.append(rule)
        return self.results.pop(0)


def _reply(text: str) -> dict[str, Any]:
    return {"kind": "reply", "text": text, "language": "en"}


# -- the guard itself ---------------------------------------------------------------------------


def test_with_no_active_item_the_model_is_called_once_with_no_extra_rule() -> None:
    call = Scripted(_reply("the answer is 12"))
    out = enforce_no_leak(call, None, "en")
    assert out["text"] == "the answer is 12" and call.rules == [None]


def test_once_the_answer_may_be_revealed_nothing_is_checked() -> None:
    call = Scripted(_reply("so x is 12"))
    out = enforce_no_leak(call, _active(may_reveal=True), "en")
    assert out["text"] == "so x is 12" and call.rules == [None]


def test_a_clean_reply_passes_and_the_model_was_told_to_withhold() -> None:
    call = Scripted(_reply("What do you notice about the 5?"))
    out = enforce_no_leak(call, _active(), "en")
    assert out["text"].startswith("What do you notice") and call.rules == [WITHHOLD_RULE]


@pytest.mark.parametrize("leak", ["The answer is 12.", "So x = 12", "It comes to twelve? no, 12"])
def test_a_leaking_reply_is_regenerated_once_with_a_stricter_rule(leak: str) -> None:
    call = Scripted(_reply(leak), _reply("Try undoing the +5 first."))
    out = enforce_no_leak(call, _active(), "en")
    assert out["text"] == "Try undoing the +5 first."
    assert call.rules == [WITHHOLD_RULE, f"{WITHHOLD_RULE} {STRICT_RULE}"]


def test_a_second_leak_falls_back_to_the_lowest_safe_authored_hint() -> None:
    hints = ((1, {"en": "It is 12, go on"}), (2, {"en": SAFE}), (3, {"en": "Take 7 away."}))
    call = Scripted(_reply("12!"), _reply("It is 12."))
    out = enforce_no_leak(call, _active(hints), "en")
    assert out["kind"] == "reply" and out["text"] == SAFE
    assert out["source"] == "authored_hint"


def test_the_fallback_never_uses_hint_three_or_an_unwritten_translation() -> None:
    hints = ((1, {"en": "x is 12"}), (2, {"ne": "<Nepali to be filled>"}), (3, {"en": "Subtract."}))
    call = Scripted(_reply("12"), _reply("12"))
    out = enforce_no_leak(call, _active(hints), "en")
    assert out == {"kind": "unavailable", "reason": "checks"}


def test_the_fallback_uses_the_students_language_when_it_is_written() -> None:
    hints = ((1, {"en": SAFE, "hi": "पहले दोनों तरफ़ क्या करें?"}),)
    call = Scripted(_reply("12"), _reply("12"))
    out = enforce_no_leak(call, _active(hints), "hi")
    assert out["text"] == "पहले दोनों तरफ़ क्या करें?" and out["language"] == "hi"


def test_a_reply_that_is_not_a_reply_passes_through_untouched() -> None:
    call = Scripted({"kind": "unavailable", "reason": "provider_error"})
    out = enforce_no_leak(call, _active(), "en")
    assert out["reason"] == "provider_error" and len(call.rules) == 1


def test_a_failed_retry_still_ends_safely() -> None:
    call = Scripted(_reply("12"), {"kind": "unavailable", "reason": "provider_error"})
    out = enforce_no_leak(call, _active(), "en")
    assert out["kind"] == "reply" and out["text"] == SAFE


def test_the_number_inside_a_longer_number_is_not_a_leak() -> None:
    assert not leaks("You have 120 apples and 3 boxes.", _active())
    assert leaks("You end up with 12 in total.", _active())


# -- through the endpoint -----------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model_strong", "groq/test-model")
    monkeypatch.setattr(settings, "explain_enabled", True)


def _model(monkeypatch: pytest.MonkeyPatch, *replies: str) -> list[str]:
    """Replace the provider call; returns the system prompts it was given, in order."""
    systems: list[str] = []
    queue = list(replies)

    def complete(system: str, history: Any, user: str, model: str, key: str) -> str:
        systems.append(system)
        return queue.pop(0)

    monkeypatch.setattr(service_chat, "_chat_complete", complete)
    return systems


def _session_on_item(client: TestClient, world: World, db: Session, **plan: Any) -> str:
    started = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "practice"},
        headers=auth_header(world.student_token),
    )
    assert started.status_code == 200, started.text
    sid = started.json()["id"]
    db.merge(
        ItemRow(
            id="ITEM.G.1",
            skill_ids=["MATH.ALG.LIN1.SOLVE_TWO_STEP"],
            primary_skill="MATH.ALG.LIN1.SOLVE_TWO_STEP",
            difficulty=0.5,
            type="typed",
            pool="practice",
            stem={"en": "Solve 3x + 5 = 41"},
            answer={"sympy": ANSWER, "accept": [ANSWER, "x=12"]},
            solution_steps=[],
            hints=[{"level": 1, "en": SAFE}],
            prediction_prompt={},
            misconception_rules=[],
            status="draft",
            content_hash="x",
        )
    )
    row = db.get(SessionRow, uuid.UUID(sid))
    assert row is not None
    row.ended_at = None  # the test database has no content, so the session ended at once
    row.plan = {**(row.plan or {}), "current_item_id": "ITEM.G.1", **plan}
    db.commit()
    return sid


def _chat(client: TestClient, world: World, session_id: str | None) -> Any:
    body: dict[str, Any] = {"prompt": "what is x", "history": []}
    if session_id is not None:
        body["session_id"] = session_id
    return client.post("/explain/chat", json=body, headers=auth_header(world.student_token))


def test_a_leaking_model_reply_never_reaches_the_student(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sid = _session_on_item(client, world, db)
    systems = _model(monkeypatch, "Easy, x is 12.", "Think about undoing the +5 first.")
    out = _chat(client, world, sid).json()
    assert out["kind"] == "reply" and "12" not in out["text"]
    assert len(systems) == 2
    assert WITHHOLD_RULE in systems[0] and STRICT_RULE in systems[1]


def test_after_two_hints_and_an_attempt_the_answer_may_be_said(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sid = _session_on_item(client, world, db, hint_level_shown=2, attempt_after_hint2=True)
    systems = _model(monkeypatch, "Yes, x is 12.")
    out = _chat(client, world, sid).json()
    assert out["text"] == "Yes, x is 12." and len(systems) == 1
    assert WITHHOLD_RULE not in systems[0]


def test_two_hints_without_an_attempt_still_withhold(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sid = _session_on_item(client, world, db, hint_level_shown=2)
    _model(monkeypatch, "x is 12", "x is 12")
    out = _chat(client, world, sid).json()
    assert out["kind"] == "reply" and out["text"] == SAFE


def test_without_a_session_the_chat_behaves_as_before(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    systems = _model(monkeypatch, "x is 12")
    out = _chat(client, world, None).json()
    assert out["text"] == "x is 12" and len(systems) == 1
    assert WITHHOLD_RULE not in systems[0]


def test_another_students_session_is_a_404(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sid = _session_on_item(client, world, db)
    _model(monkeypatch, "fine")
    other = client.post(
        "/explain/chat",
        json={"prompt": "what is x", "history": [], "session_id": sid},
        headers=auth_header(world.other_parent_token),
    )
    assert other.status_code in (403, 404)  # a parent is not a student; never the item


def test_an_unknown_session_is_a_404(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    _model(monkeypatch, "fine")
    assert _chat(client, world, str(uuid.uuid4())).status_code == 404


def test_an_ended_session_applies_no_guard(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.auth.security import now_utc
    from app.db.models import SessionRow as Row

    sid = _session_on_item(client, world, db)
    row = db.get(Row, uuid.UUID(sid))
    assert row is not None
    row.ended_at = now_utc()
    db.commit()
    systems = _model(monkeypatch, "x is 12")
    assert _chat(client, world, sid).json()["text"] == "x is 12" and len(systems) == 1
