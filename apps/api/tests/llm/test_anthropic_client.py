"""The Claude SDK wrapper: text blocks only, refusals, errors without detail, no sampling params."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from app.llm import anthropic_client
from app.llm.provider import ProviderError

TURNS = [{"role": "user", "content": "why?"}]


def _message(stop: str = "end_turn", *blocks: Any) -> Any:
    content = blocks or (SimpleNamespace(type="text", text="Hello."),)
    return SimpleNamespace(
        stop_reason=stop,
        content=list(content),
        usage=SimpleNamespace(input_tokens=5, output_tokens=7),
    )


def _install(monkeypatch: pytest.MonkeyPatch, messages: Any) -> None:
    monkeypatch.setattr(anthropic_client, "_client", lambda *_a: SimpleNamespace(messages=messages))


class _Create:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _complete(**extra: Any) -> anthropic_client.Reply:
    return anthropic_client.complete(
        "SYS", TURNS, "claude-haiku-5-5", "key", max_tokens=100, timeout_s=5.0, **extra
    )


def test_the_reply_joins_text_blocks_skips_the_rest_and_counts_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blocks = (
        SimpleNamespace(type="thinking", thinking="hmm"),
        SimpleNamespace(type="text", text="Try "),
        SimpleNamespace(type="text", text="this."),
    )
    _install(monkeypatch, _Create(_message("end_turn", *blocks)))
    assert _complete() == anthropic_client.Reply("Try this.", 5, 7)


def test_a_refusal_is_an_empty_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _Create(_message("refusal")))
    assert _complete().text == ""


def test_the_request_has_no_sampling_params_and_thinking_only_when_turned_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = _Create(_message())
    _install(monkeypatch, create)
    _complete()
    _complete(thinking_off=True)
    plain, off = create.calls
    assert plain["model"] == "claude-haiku-5-5" and plain["system"] == "SYS"
    assert plain["max_tokens"] == 100 and plain["messages"] == TURNS
    assert "thinking" not in plain and off["thinking"] == {"type": "disabled"}
    for call in create.calls:
        assert not {"temperature", "top_p", "top_k"} & call.keys()
        assert call["messages"][-1]["role"] == "user"  # never an assistant prefill


def test_a_failure_carries_only_the_class_name(monkeypatch: pytest.MonkeyPatch) -> None:
    class RateLimitError(Exception):
        pass

    _install(monkeypatch, _Create(RateLimitError("secret detail with the key sk-ant-123")))
    with pytest.raises(ProviderError) as caught:
        _complete()
    assert str(caught.value) == "RateLimitError" and "sk-ant" not in repr(caught.value)


class _Stream:
    def __init__(self, pieces: list[str], stop: str = "end_turn", fail: bool = False) -> None:
        self.text_stream = self._iterate(pieces, fail)
        self.stop = stop
        self.closed = False

    @staticmethod
    def _iterate(pieces: list[str], fail: bool) -> Any:
        yield from pieces
        if fail:
            raise ConnectionError("dropped")

    def __enter__(self) -> _Stream:
        return self

    def __exit__(self, *_a: Any) -> None:
        self.closed = True

    def get_final_message(self) -> Any:
        return SimpleNamespace(stop_reason=self.stop)


def _streaming(stream: _Stream) -> Any:
    return SimpleNamespace(stream=lambda **_k: stream)


def _run() -> Any:
    return anthropic_client.stream_text(
        "SYS", TURNS, "claude-haiku-5-5", "key", max_tokens=100, timeout_s=5.0
    )


def test_the_stream_yields_text_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _Stream(["Think ", "first."])
    _install(monkeypatch, _streaming(stream))
    assert list(_run()) == ["Think ", "first."] and stream.closed


def test_a_streamed_refusal_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _Stream(["x"], stop="refusal")
    _install(monkeypatch, _streaming(stream))
    with pytest.raises(ProviderError, match="refusal"):
        list(_run())


def test_a_dropped_stream_is_a_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _Stream(["a"], fail=True)
    _install(monkeypatch, _streaming(stream))
    seen: list[str] = []
    with pytest.raises(ProviderError, match="ConnectionError"):
        for piece in _run():
            seen.append(piece)
    assert seen == ["a"]


def test_closing_the_stream_early_closes_the_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _Stream(["one ", "two ", "three"])
    _install(monkeypatch, _streaming(stream))
    reader = _run()
    assert next(reader) == "one "
    reader.close()
    assert stream.closed


def test_a_missing_sdk_is_a_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    anthropic_client._client.cache_clear()
    monkeypatch.setitem(sys.modules, "anthropic", None)  # makes `import anthropic` fail
    with pytest.raises(ProviderError, match="sdk_missing"):
        anthropic_client._client("key", 5.0)
    anthropic_client._client.cache_clear()
