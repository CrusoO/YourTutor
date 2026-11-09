"""C2: the follow-up chat uses the learner's register and never ends on a bare error."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.conversation.voice import register_for_grade
from app.explain import router as explain_router
from app.explain import service_chat
from app.explain.service import Gate
from app.llm.provider import ProviderError
from tests.conftest import World, auth_header

OPEN = Gate(enabled=True, allowed=True)
LONG = (
    "You have the direction right and that matters here. The speed doubles, so the distance "
    "in the same time doubles as well. Think about what that does to the units. "
    "What happens to the time if the distance stays the same?"
)


@pytest.fixture(autouse=True)
def _keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("groq_api_key", "gemini_api_key", "openrouter_api_key", "anthropic_api_key"):
        monkeypatch.setattr(settings, name, "")  # a developer's own .env must not change a test
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model_strong", "groq/test-model")
    monkeypatch.setattr(settings, "explain_enabled", True)


def _fake(reply: str, seen: dict[str, Any]):
    def complete(
        system: str, history: list[dict[str, Any]], user: str, model: str, key: str
    ) -> str:
        seen.update(system=system, history=history, user=user)
        return reply

    return complete


# -- the prompt and the length -----------------------------------------------------------------


def test_the_prompt_carries_the_learners_tone_and_word_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr(service_chat, "_chat_complete", _fake(LONG, seen))
    reg = register_for_grade(3)
    service_chat.build_chat("why?", "en", [], OPEN, register=reg)
    assert reg.style in seen["system"] and "25 words or fewer" in seen["system"]
    assert "{register_rule}" not in seen["system"] and "{scope_rule}" not in seen["system"]


def test_the_prompt_follows_the_constitution(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr(service_chat, "_chat_complete", _fake(LONG, seen))
    service_chat.build_chat("why?", "en", [], OPEN, register=register_for_grade(10))
    system = seen["system"].lower()
    for rule in (
        "you are an ai",
        "acknowledging",
        "one idea",
        "at most one question",
        "never ability",
        "<student_text>",
        "never invent facts",
    ):
        assert rule in system, rule


def test_a_young_learners_reply_is_cut_to_the_primary_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service_chat, "_chat_complete", _fake(LONG, {}))
    out = service_chat.build_chat("why?", "en", [], OPEN, register=register_for_grade(3))
    assert out["kind"] == "reply" and len(out["text"].split()) <= 25
    assert out["text"].endswith((".", "?", "!"))  # cut at a sentence, never mid-sentence


def test_an_older_learner_keeps_more(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service_chat, "_chat_complete", _fake(LONG, {}))
    out = service_chat.build_chat("why?", "en", [], OPEN, register=register_for_grade(12))
    assert out["text"] == LONG  # 80 words allowed


def test_without_a_register_the_old_behaviour_holds(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr(service_chat, "_chat_complete", _fake(LONG, seen))
    out = service_chat.build_chat("why?", "en", [], OPEN)
    assert out["text"] == LONG and "short" in seen["system"]


# -- the endpoint never ends on a bare error --------------------------------------------------


def _ask(
    client: TestClient, world: World, history: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    r = client.post(
        "/explain/chat",
        json={"prompt": "why does it double", "history": history or []},
        headers=auth_header(world.student_token),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_a_provider_failure_gets_an_honest_line_and_choices(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_a: Any, **_k: Any) -> str:
        raise ProviderError("down")

    monkeypatch.setattr(service_chat, "_chat_complete", boom)
    body = _ask(client, world)
    assert body["kind"] == "unavailable" and body["reason"] == "provider_error"  # unchanged
    fb = body["fallback"]
    assert fb["reason"] == "unavailable" and fb["text"]
    assert [o["id"] for o in fb["offers"]] == ["ask_again", "practice"]


def test_switched_off_says_so_and_offers_practice_only(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "explain_enabled", False)
    body = _ask(client, world)
    assert body["reason"] == "off" and body["fallback"]["reason"] == "ai_off"
    assert [o["id"] for o in body["fallback"]["offers"]] == ["practice"]


def test_no_key_is_treated_like_any_other_unavailable(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "llm_api_key", "")
    body = _ask(client, world)
    assert body["reason"] == "no_key" and body["fallback"]["reason"] == "unavailable"


def test_the_fallback_line_changes_as_the_conversation_goes_on(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "llm_api_key", "")
    first = _ask(client, world)["fallback"]["text"]
    later = _ask(
        client, world, [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
    )["fallback"]["text"]
    assert first != later


def test_a_good_reply_has_no_fallback_and_is_trimmed(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service_chat, "_chat_complete", _fake(LONG, {}))
    body = _ask(client, world)
    assert body["kind"] == "reply" and "fallback" not in body
    assert len(body["text"].split()) <= 60  # this learner's grade is in the 60-word band


def test_safety_replies_are_untouched(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service_chat, "_chat_complete", _fake(LONG, {}))
    r = client.post(
        "/explain/chat",
        json={"prompt": "I want to hurt myself"},
        headers=auth_header(world.student_token),
    )
    body = r.json()
    assert body["kind"] == "distress" and "fallback" not in body


def test_the_router_names_the_students_grade_band(monkeypatch: pytest.MonkeyPatch) -> None:
    assert explain_router.register_for_grade(9).band_id == "lower_secondary"
