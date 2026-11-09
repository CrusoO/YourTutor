"""The tutor chat speaks both OpenAI-style providers and Anthropic's Messages API."""

from __future__ import annotations

import io
import json
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
from app.llm.provider import ProviderError

HISTORY = [{"role": "user", "content": "slope"}, {"role": "assistant", "content": "A ratio."}]
OPEN = Gate(enabled=True, allowed=True)


def _body(request: Any) -> dict[str, Any]:
    return json.loads(request.data.decode("utf-8"))


def test_an_anthropic_request_uses_the_messages_api() -> None:
    req = _chat_request("SYS", HISTORY, "why?", "anthropic/claude-haiku-5-5", "k", stream=True)
    body = _body(req)
    assert req.full_url == "https://api.anthropic.com/v1/messages"
    assert req.get_header("X-api-key") == "k" and req.get_header("Anthropic-version")
    assert req.get_header("Authorization") is None
    assert body["system"] == "SYS" and body["model"] == "claude-haiku-5-5"
    assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user"]
    assert body["stream"] is True and "temperature" not in body


def test_an_openai_style_request_is_unchanged() -> None:
    req = _chat_request("SYS", HISTORY, "why?", "groq/m", "k")
    body = _body(req)
    assert req.get_header("Authorization") == "Bearer k"
    assert body["messages"][0] == {"role": "system", "content": "SYS"}
    assert "stream" not in body


def test_an_unknown_provider_is_a_provider_error() -> None:
    with pytest.raises(ProviderError):
        _chat_request("s", [], "q", "mystery/x", "k")


def test_the_anthropic_reply_joins_text_blocks_and_skips_the_rest() -> None:
    data = {
        "content": [
            {"type": "thinking", "thinking": "hmm"},
            {"type": "text", "text": "Try "},
            {"type": "text", "text": "this."},
        ],
        "stop_reason": "end_turn",
    }
    assert _reply_text("anthropic", data) == "Try this."


def test_an_anthropic_refusal_is_no_reply() -> None:
    assert (
        _reply_text(
            "anthropic", {"content": [{"type": "text", "text": "x"}], "stop_reason": "refusal"}
        )
        == ""
    )


def test_the_openai_reply_is_read_as_before() -> None:
    assert _reply_text("groq", {"choices": [{"message": {"content": "hi"}}]}) == "hi"


def test_anthropic_stream_events_give_text_and_a_refusal_raises() -> None:
    delta = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hi"}}
    assert _stream_piece("anthropic", delta) == "Hi"
    assert _stream_piece("anthropic", {"type": "message_start"}) == ""
    thinking = {"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "x"}}
    assert _stream_piece("anthropic", thinking) == ""
    with pytest.raises(ProviderError):
        _stream_piece("anthropic", {"type": "message_delta", "delta": {"stop_reason": "refusal"}})


class _Wire(io.BytesIO):
    def __enter__(self) -> _Wire:
        return self

    def __exit__(self, *_a: Any) -> None:
        return None


def test_the_anthropic_stream_is_read_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = [
        "event: message_start",
        'data: {"type":"message_start"}',
        "",
        'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Think "}}',
        "",
        'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"first."}}',
        'data: {"type":"message_stop"}',
    ]
    payload = ("\n".join(lines) + "\n").encode()
    monkeypatch.setattr(service_chat.urllib.request, "urlopen", lambda *a, **k: _Wire(payload))
    out = list(service_chat._chat_stream("s", [], "q", "anthropic/claude-haiku-5-5", "k"))
    assert out == ["Think ", "first."]


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
