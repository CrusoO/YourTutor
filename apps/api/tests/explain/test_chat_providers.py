"""The tutor chat speaks OpenAI-style providers over HTTP and Claude through the Anthropic SDK."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.config import settings
from app.explain import service_chat
from app.explain.service import Gate
from app.explain.service_chat import (
    ChatCall,
    _chat_request,
    _reply_text,
    _stream_piece,
    prepare_chat,
)
from app.llm import anthropic_client
from app.llm.provider import ProviderError

HISTORY = [{"role": "user", "content": "slope"}, {"role": "assistant", "content": "A ratio."}]
OPEN = Gate(enabled=True, allowed=True)


def _body(request: Any) -> dict[str, Any]:
    return json.loads(request.data.decode("utf-8"))


def test_an_openai_style_request_is_unchanged() -> None:
    req = _chat_request("SYS", HISTORY, "why?", "groq/m", "k")
    body = _body(req)
    assert req.get_header("Authorization") == "Bearer k"
    assert body["messages"][0] == {"role": "system", "content": "SYS"}
    assert "stream" not in body


def test_an_unknown_provider_is_a_provider_error() -> None:
    with pytest.raises(ProviderError):
        _chat_request("s", [], "q", "mystery/x", "k")


def test_claude_never_goes_through_the_hand_built_http_request() -> None:
    with pytest.raises(ProviderError):
        _chat_request("s", [], "q", "anthropic/claude-haiku-5-5", "k")


def test_the_openai_reply_is_read_as_before() -> None:
    assert _reply_text({"choices": [{"message": {"content": "hi"}}]}) == "hi"
    assert _stream_piece({"choices": [{"delta": {"content": "yo"}}]}) == "yo"


class _FakeStream:
    def __init__(self, pieces: list[str]) -> None:
        self.text_stream = iter(pieces)

    def __enter__(self) -> _FakeStream:
        return self

    def __exit__(self, *_a: Any) -> None:
        return None

    def get_final_message(self) -> Any:
        return SimpleNamespace(stop_reason="end_turn")


class _FakeMessages:
    def __init__(self, calls: list[dict[str, Any]]) -> None:
        self.calls = calls

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text="Try it.")],
            usage=SimpleNamespace(input_tokens=3, output_tokens=2),
        )

    def stream(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return _FakeStream(["Think ", "first."])


def _fake_sdk(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    client = SimpleNamespace(messages=_FakeMessages(calls))
    monkeypatch.setattr(anthropic_client, "_client", lambda *_a: client)
    return calls


def test_a_claude_chat_goes_through_the_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _fake_sdk(monkeypatch)
    text = service_chat._chat_complete("SYS", HISTORY, "why?", "anthropic/claude-haiku-5-5", "k")
    assert text == "Try it."
    sent = calls[0]
    assert sent["model"] == "claude-haiku-5-5" and sent["system"] == "SYS"
    assert [m["role"] for m in sent["messages"]] == ["user", "assistant", "user"]
    assert not {"temperature", "top_p", "top_k"} & sent.keys()


def test_a_claude_chat_stream_goes_through_the_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _fake_sdk(monkeypatch)
    out = list(service_chat._chat_stream("s", [], "q", "anthropic/claude-haiku-5-5", "k"))
    assert out == ["Think ", "first."]
    assert calls[0]["model"] == "claude-haiku-5-5"


def test_a_claude_model_with_no_name_is_unknown() -> None:
    with pytest.raises(ProviderError):
        service_chat._chat_complete("s", [], "q", "anthropic/", "k")


@pytest.fixture
def _clean_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("groq_api_key", "gemini_api_key", "openrouter_api_key", "anthropic_api_key"):
        monkeypatch.setattr(settings, name, "")
    monkeypatch.setattr(settings, "llm_api_key", "")


@pytest.mark.usefixtures("_clean_keys")
def test_a_claude_model_uses_the_anthropic_key_not_llm_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "claude-key")
    prepared = prepare_chat("why?", "en", [], OPEN, model="anthropic/claude-haiku-5-5")
    assert isinstance(prepared, ChatCall) and prepared.api_key == "claude-key"


@pytest.mark.usefixtures("_clean_keys")
def test_without_the_models_own_key_the_chat_says_no_key() -> None:
    prepared = prepare_chat("why?", "en", [], OPEN, model="anthropic/claude-haiku-5-5")
    assert prepared == {"kind": "unavailable", "reason": "no_key"}
