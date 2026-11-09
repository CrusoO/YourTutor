"""Layer 2: the classifier protocol, its fallbacks and the request shape. No model is called."""

from __future__ import annotations

import logging
import threading
from types import SimpleNamespace
from typing import Any

import pytest

from app.safety_classifier import (
    AnthropicSafetyClient,
    Classification,
    ClassifierError,
    as_detection,
    classifier_enabled,
    classify_safely,
    collect_text,
    get_classifier,
    is_moderation,
    parse_classification,
    run_beside,
    use_classifier,
)


class FakeClassifier:
    def __init__(self, answers: dict[str, Classification] | Exception | None = None) -> None:
        self.answers = answers
        self.seen: list[tuple[str, str]] = []

    def classify(self, text: str, source: str) -> Classification:
        self.seen.append((source, text))
        if isinstance(self.answers, Exception):
            raise self.answers
        return (self.answers or {}).get(text, Classification("none", "none"))


def test_it_is_off_unless_the_env_switch_is_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SAFETY_CLASSIFIER_ENABLED", raising=False)
    assert classifier_enabled() is False and get_classifier() is None
    monkeypatch.setenv("SAFETY_CLASSIFIER_ENABLED", "false")
    assert classifier_enabled() is False
    monkeypatch.setenv("SAFETY_CLASSIFIER_ENABLED", "true")
    assert classifier_enabled() is True


def test_parse_accepts_only_allowed_values() -> None:
    assert parse_classification('{"risk":"urgent","category":"suicide"}') == Classification(
        "urgent", "suicide"
    )
    for bad in ("not json", '{"risk":"high","category":"suicide"}', '{"risk":"none"}', "[]"):
        with pytest.raises(ClassifierError):
            parse_classification(bad)


def test_categories_map_to_distress_or_moderation() -> None:
    assert as_detection(Classification("urgent", "abuse")).risk == "urgent"
    assert as_detection(Classification("concern", "exam_stress")).risk == "concern"
    assert as_detection(Classification("concern", "violence")).risk == "none"
    assert as_detection(None).risk == "none"
    assert is_moderation(Classification("concern", "sexual_content"))
    assert not is_moderation(Classification("none", "none"))
    assert not is_moderation(Classification("urgent", "suicide"))


def test_a_failing_classifier_falls_back_and_logs_no_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "my secret sentence about my teacher"
    with caplog.at_level(logging.WARNING, logger="app.safety"):
        assert classify_safely(secret, "input", FakeClassifier(TimeoutError("x"))) is None
    assert "TimeoutError" in caplog.text and secret not in caplog.text
    assert classify_safely(secret, "input", None) is None
    assert classify_safely("   ", "input", FakeClassifier()) is None


def test_it_runs_beside_the_main_call_not_before_it() -> None:
    started = threading.Event()

    class Slow(FakeClassifier):
        def classify(self, text: str, source: str) -> Classification:
            started.set()
            return Classification("urgent", "suicide")

    def main() -> str:
        assert started.wait(2), "the classifier must start while the main call runs"
        return "answer"

    found, result = run_beside("text", main, Slow())
    assert result == "answer" and found == Classification("urgent", "suicide")
    assert run_beside("text", lambda: 1, None) == (None, 1)


def test_use_classifier_overrides_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SAFETY_CLASSIFIER_ENABLED", raising=False)
    fake = FakeClassifier()
    with use_classifier(fake):
        assert get_classifier() is fake
    assert get_classifier() is None


def test_collect_text_skips_codes_and_caps_length() -> None:
    reply = {
        "kind": "explanation",
        "proof": "sig",
        "sections": [{"heading": "H", "body": "B" * 9000}],
    }
    text = collect_text(reply)
    assert text.startswith("H B") and "sig" not in text and len(text) <= 4000


class _Messages:
    def __init__(self, stop_reason: str = "end_turn", text: str | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.stop_reason = stop_reason
        self.text = text if text is not None else '{"risk":"none","category":"none"}'

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=self.text)]
        )


def _client(messages: _Messages) -> AnthropicSafetyClient:
    client = AnthropicSafetyClient.__new__(AnthropicSafetyClient)  # skip the SDK import
    client._client = SimpleNamespace(messages=messages)  # type: ignore[attr-defined,assignment]
    client._model = "claude-haiku-5-5"
    return client


def test_the_request_has_no_sampling_params_no_prefill_and_uses_structured_output() -> None:
    messages = _Messages()
    result = _client(messages).classify("hello", "input")
    assert result == Classification("none", "none")
    call = messages.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    for forbidden in ("temperature", "top_p", "top_k"):
        assert forbidden not in call
    assert [m["role"] for m in call["messages"]] == ["user"]  # no assistant prefill
    assert call["output_config"]["effort"] == "low"
    assert call["output_config"]["format"]["type"] == "json_schema"
    schema = call["output_config"]["format"]["schema"]
    assert schema["properties"]["risk"]["enum"] == ["none", "concern", "urgent"]
    assert "hello" in call["messages"][0]["content"]


@pytest.mark.parametrize("stop", ["refusal", "max_tokens", "pause_turn"])
def test_a_stop_reason_other_than_end_turn_is_an_error(stop: str) -> None:
    with pytest.raises(ClassifierError):
        _client(_Messages(stop_reason=stop)).classify("x", "input")


def test_an_unparseable_model_reply_is_an_error() -> None:
    with pytest.raises(ClassifierError):
        _client(_Messages(text="sure!")).classify("x", "input")
