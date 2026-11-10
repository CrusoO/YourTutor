"""The streamed tutor chat: sentence by sentence, never showing what the guard would hold back."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.conversation.voice import register_for_grade
from app.explain import service_chat
from app.explain.answer_guard import ActiveItem
from app.explain.chat_stream import stream_reply
from app.explain.service_chat import ChatCall
from app.llm.provider import ProviderError
from app.safety_classifier import Classification, use_classifier
from tests.conftest import World, auth_header
from tests.explain.test_answer_guard import SAFE, _session_on_item

CALL = ChatCall("sys", [], "hi", "anthropic/test", "key", "en")
ACTIVE = ActiveItem("ITEM.G.1", ("12", "x=12"), ((1, {"en": SAFE}),), False)


class Wire:
    """A stand-in for the provider's stream. Records whether the reader closed it early."""

    def __init__(self, pieces: list[str], error: bool = False) -> None:
        self.pieces = pieces
        self.error = error
        self.closed_early = False

    def __call__(self, *_a: Any) -> Iterator[str]:
        try:
            yield from self.pieces
            if self.error:
                raise ProviderError("down")
        except GeneratorExit:
            self.closed_early = True
            raise


def _run(
    monkeypatch: pytest.MonkeyPatch,
    wire: Wire,
    *,
    call: ChatCall = CALL,
    active: ActiveItem | None = None,
    retry: str | None = None,
) -> tuple[list[str], dict[str, Any]]:
    monkeypatch.setattr(service_chat, "_chat_stream", wire)
    if retry is not None:
        monkeypatch.setattr(service_chat, "_chat_complete", lambda *a: retry)
    events = list(stream_reply(call, active))
    assert [e["type"] for e in events[:-1]] == ["delta"] * (len(events) - 1)
    assert events[-1]["type"] == "final"
    return [e["text"] for e in events[:-1]], events[-1]["result"]


def test_sentences_arrive_in_order_and_the_final_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    pieces = ["You are close. ", "What happens ", "to both sides? ", "Try it."]
    deltas, result = _run(monkeypatch, Wire(pieces))
    assert "".join(deltas) == "You are close. What happens to both sides? Try it."
    assert result == {"kind": "reply", "text": "".join(deltas), "language": "en"}


def test_a_sentence_is_never_sent_half_finished(monkeypatch: pytest.MonkeyPatch) -> None:
    deltas, _ = _run(monkeypatch, Wire(["Half a sen", "tence that ends. ", "Next"]))
    assert deltas == ["Half a sentence that ends.", " Next"]


def test_a_sentence_that_gives_the_answer_is_never_shown(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = Wire(["Good start. ", "So x is 1", "2. ", "Done."])  # the number arrives in two pieces
    deltas, result = _run(monkeypatch, wire, active=ACTIVE, retry="Undo the +5 first.")
    assert deltas == ["Good start."]
    assert "12" not in "".join(deltas)
    assert wire.closed_early  # we stopped reading as soon as it leaked
    assert result == {"kind": "reply", "text": "Undo the +5 first.", "language": "en"}


def test_a_retry_that_still_leaks_ends_on_an_authored_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    _, result = _run(monkeypatch, Wire(["It is 12."]), active=ACTIVE, retry="Yes, 12.")
    assert result["text"] == SAFE and result["source"] == "authored_hint"


def test_once_the_answer_may_be_said_nothing_is_held_back(monkeypatch: pytest.MonkeyPatch) -> None:
    free = ActiveItem("ITEM.G.1", ("12",), (), True)
    deltas, result = _run(monkeypatch, Wire(["Yes, x is 12."]), active=free)
    assert deltas == ["Yes, x is 12."] and result["text"] == "Yes, x is 12."


def test_the_reply_is_cut_at_the_grade_bands_word_limit_while_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call = ChatCall("sys", [], "hi", "anthropic/test", "key", "en", register_for_grade(3))
    limit = call.register.max_words  # type: ignore[union-attr]
    sentence = "One two three four five six seven eight. "
    wire = Wire([sentence] * 10)
    deltas, result = _run(monkeypatch, wire, call=call)
    assert 0 < len(" ".join(deltas).split()) <= limit
    assert result["text"] == "".join(deltas).strip() or result["text"] == " ".join(deltas).strip()
    assert wire.closed_early


def test_a_failure_before_any_text_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    deltas, result = _run(monkeypatch, Wire([], error=True))
    assert deltas == [] and result == {"kind": "unavailable", "reason": "provider_error"}


def test_a_failure_after_some_text_keeps_the_finished_sentences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deltas, result = _run(monkeypatch, Wire(["First idea. ", "Second"], error=True))
    assert deltas == ["First idea."] and result["text"] == "First idea."


def test_an_empty_stream_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    _, result = _run(monkeypatch, Wire(["  "]))
    assert result == {"kind": "unavailable", "reason": "checks"}


# -- the route ----------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model_strong", "anthropic/test-model")
    monkeypatch.setattr(settings, "explain_enabled", True)


def _events(response: Any) -> list[dict[str, Any]]:
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    lines = [ln for ln in response.text.split("\n\n") if ln.strip()]
    assert all(ln.startswith("data: ") for ln in lines)
    return [json.loads(ln[6:]) for ln in lines]


def _stream(
    client: TestClient, world: World, prompt: str = "what is x", **extra: Any
) -> list[dict[str, Any]]:
    response = client.post(
        "/explain/chat/stream",
        json={"prompt": prompt, "history": [], **extra},
        headers=auth_header(world.student_token),
    )
    return _events(response)


def _no_model(monkeypatch: pytest.MonkeyPatch) -> None:
    def streamed(*_a: Any) -> Iterator[str]:
        raise AssertionError("no model may be called")
        yield ""  # pragma: no cover

    def complete(*_a: Any) -> str:
        raise AssertionError("no model may be called")

    monkeypatch.setattr(service_chat, "_chat_stream", streamed)
    monkeypatch.setattr(service_chat, "_chat_complete", complete)


def test_the_route_streams_deltas_then_a_final_with_the_same_text(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service_chat, "_chat_stream", Wire(["Think about it. ", "What is x?"]))
    events = _stream(client, world)
    assert [e["type"] for e in events] == ["delta", "delta", "final"]
    final = events[-1]["result"]
    assert final["kind"] == "reply"
    assert "".join(e["text"] for e in events[:-1]) == final["text"]


def test_distress_is_one_final_event_and_no_model_is_called(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_model(monkeypatch)
    events = _stream(client, world, "I want to kill myself")
    assert len(events) == 1 and events[0]["type"] == "final"
    result = events[0]["result"]
    assert result["kind"] == "distress" and result["helplines"]


def test_after_a_flag_the_stream_is_the_paused_reply(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_model(monkeypatch)
    _stream(client, world, "I want to kill myself")
    events = _stream(client, world, "what is a quadratic")
    assert len(events) == 1 and events[0]["result"]["risk"] == "paused"


def test_with_the_output_classifier_on_the_reply_is_not_streamed(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Quiet:
        def classify(self, text: str, source: str) -> Classification:
            return Classification("none", "none")

    monkeypatch.setattr(service_chat, "_chat_complete", lambda *a: "A calm reply.")
    with use_classifier(Quiet()):  # type: ignore[arg-type]
        events = _stream(client, world)
    assert [e["type"] for e in events] == ["final"] and events[0]["result"]["kind"] == "reply"


def test_a_missing_key_is_a_final_unavailable_with_the_authored_line(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    events = _stream(client, world)
    result = events[0]["result"]
    assert result["reason"] == "no_key" and result["fallback"]["text"]


def test_a_model_that_is_not_anthropic_is_never_called_and_reads_as_no_key(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "llm_model_strong", "mystery/model")
    events = _stream(client, world)
    assert [e["type"] for e in events] == ["final"]
    assert events[0]["result"]["reason"] == "no_key"


def test_a_stream_failure_ends_with_an_unavailable_final_and_the_authored_line(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service_chat, "_chat_stream", Wire([], error=True))
    events = _stream(client, world)
    result = events[-1]["result"]
    assert result["reason"] == "provider_error" and result["fallback"]["offers"]


def test_a_guardian_cannot_use_the_stream(client: TestClient, world: World) -> None:
    response = client.post(
        "/explain/chat/stream",
        json={"prompt": "hi", "history": []},
        headers=auth_header(world.parent_token),
    )
    assert response.status_code == 403


def test_the_streamed_route_withholds_the_answer_like_the_plain_one(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sid = _session_on_item(client, world, db)
    monkeypatch.setattr(service_chat, "_chat_stream", Wire(["Nice. ", "It is 12. "]))
    monkeypatch.setattr(service_chat, "_chat_complete", lambda *a: "Undo the +5 first.")
    events = _stream(client, world, session_id=sid)
    shown = "".join(e["text"] for e in events if e["type"] == "delta")
    assert "12" not in shown
    assert events[-1]["result"]["text"] == "Undo the +5 first."


def test_another_sessions_id_is_a_404_on_the_stream_too(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_model(monkeypatch)
    response = client.post(
        "/explain/chat/stream",
        json={"prompt": "hi", "history": [], "session_id": str(uuid.uuid4())},
        headers=auth_header(world.student_token),
    )
    assert response.status_code == 404
