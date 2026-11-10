"""The tutor chat speaks to Claude through the Anthropic SDK, and to nothing else."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.config import settings
from app.explain import service_chat
from app.explain.service import Gate
from app.explain.service_chat import ChatCall, prepare_chat
from app.llm import anthropic_client
from app.llm.provider import ProviderError

HISTORY = [{"role": "user", "content": "slope"}, {"role": "assistant", "content": "A ratio."}]
OPEN = Gate(enabled=True, allowed=True)


def test_a_model_name_without_the_anthropic_prefix_is_a_provider_error() -> None:
    for name in ("groq/m", "mystery/x", "claude-haiku-5-5", "anthropic/"):
        with pytest.raises(ProviderError):
            service_chat._chat_complete("s", [], "q", name, "k")
        with pytest.raises(ProviderError):
            list(service_chat._chat_stream("s", [], "q", name, "k"))


def test_only_anthropic_models_can_stream() -> None:
    assert service_chat.can_stream("anthropic/claude-haiku-5-5")
    assert not service_chat.can_stream("groq/m")
    assert not service_chat.can_stream("anthropic/")


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


@pytest.fixture
def _clean_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "")


@pytest.mark.usefixtures("_clean_keys")
def test_a_claude_model_uses_the_anthropic_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "claude-key")
    prepared = prepare_chat("why?", "en", [], OPEN, model="anthropic/claude-haiku-5-5")
    assert isinstance(prepared, ChatCall) and prepared.api_key == "claude-key"


@pytest.mark.usefixtures("_clean_keys")
def test_without_the_models_own_key_the_chat_says_no_key() -> None:
    prepared = prepare_chat("why?", "en", [], OPEN, model="anthropic/claude-haiku-5-5")
    assert prepared == {"kind": "unavailable", "reason": "no_key"}


@pytest.mark.usefixtures("_clean_keys")
def test_a_non_anthropic_model_has_no_key_even_when_a_key_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "claude-key")
    prepared = prepare_chat("why?", "en", [], OPEN, model="groq/some-model")
    assert prepared == {"kind": "unavailable", "reason": "no_key"}
