"""The interactive lesson: how the model's JSON is cleaned, and the gates and retries around it."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.explain import router as explain_router
from app.explain import service_lesson as sl
from app.explain.service import ExplainProvider, Gate
from app.llm.provider import FakeProvider, ProviderError
from tests.conftest import World, auth_header

OPEN = Gate(enabled=True, allowed=True)


def _blocks() -> list[dict[str, Any]]:
    return [
        {"kind": "hook", "text": "A surprising fact.", "question": "How can that be?"},
        {
            "kind": "predict",
            "prompt": "What happens?",
            "options": ["A", "B"],
            "correct": 1,
            "reveal_after": "B happens.",
        },
        {
            "kind": "widget",
            "widget_kind": "slider_sim",
            "spec": {
                "variable": "width",
                "unit": "nm",
                "min": 0,
                "max": 4,
                "step": 0.5,
                "formula": "exp(-2*width)",
                "output_label": "chance",
                "output_unit": "",
            },
            "controls": [],
            "what_to_notice": "notice how it falls",
        },
        {"kind": "explain", "text": "Because waves leak."},
        {
            "kind": "check",
            "question": "Thicker?",
            "options": ["a", "b", "c", "d"],
            "correct": 2,
            "feedback_per_option": ["1", "2", "3", "4"],
            "hint_ladder": ["h1", "h2", "h3"],
        },
        {
            "kind": "recap",
            "three_bullets": ["one", "two", "three"],
            "spaced_review_question": "Why?",
        },
    ]


def _lesson_json(blocks: list[dict[str, Any]] | None = None) -> str:
    return json.dumps(
        {"level": "school", "objectives": ["Explain it"], "blocks": blocks or _blocks()}
    )


def test_a_well_formed_lesson_is_kept_in_order() -> None:
    out = sl.build_lesson("what is tunnelling", "en", OPEN, FakeProvider([_lesson_json()]), "m")
    assert out["kind"] == "lesson"
    assert [b["kind"] for b in out["blocks"]] == [
        "hook",
        "predict",
        "widget",
        "explain",
        "check",
        "recap",
    ]


def test_type_is_accepted_when_a_model_writes_it_instead_of_kind() -> None:
    renamed = [{("type" if k == "kind" else k): v for k, v in b.items()} for b in _blocks()]
    cleaned = sl.clean_lesson({"blocks": renamed})
    assert cleaned is not None
    assert [b["kind"] for b in cleaned["blocks"]] == [
        "hook",
        "predict",
        "widget",
        "explain",
        "check",
        "recap",
    ]
    assert cleaned["blocks"][2]["widget_kind"] == "slider_sim"


def test_a_widget_named_by_its_subtype_in_kind_or_type_is_still_a_widget() -> None:
    steps = {"steps": [{"label": "a", "description": "x"}, {"label": "b", "description": "y"}]}
    for key in ("kind", "type"):
        raw = {key: "step_through", "spec": steps, "what_to_notice": "n"}
        cleaned = sl.clean_lesson({"blocks": [*_blocks()[:2], raw, *_blocks()[3:]]})
        assert cleaned is not None
        assert cleaned["blocks"][2]["widget_kind"] == "step_through"


def test_unknown_and_malformed_blocks_are_dropped_and_too_few_rejects_the_lesson() -> None:
    junk: list[Any] = [
        {"kind": "quiz"},
        "text",
        {"kind": "hook"},
        {"kind": "predict", "prompt": ""},
    ]
    assert sl.clean_lesson({"blocks": junk}) is None
    assert sl.clean_lesson({"blocks": "nope"}) is None
    assert sl.clean_lesson(None) is None


def test_the_token_budget_leaves_room_for_thinking_except_on_groq() -> None:
    assert sl._max_tokens("anthropic/claude-haiku-5-5") == 8000
    assert sl._max_tokens("openrouter/x/y") == 8000
    assert sl._max_tokens("groq/openai/gpt-oss-120b") == 4000


def test_the_prompt_names_the_block_key() -> None:
    system = sl.build_prompt("q", "en", restricted=False).system
    assert 'Never write "type" instead of "kind"' in system
    assert "widget_kind" in system


def test_gate_off_and_no_consent_call_nothing() -> None:
    provider = FakeProvider([_lesson_json()])
    off = sl.build_lesson("q about maths", "en", Gate(enabled=False, allowed=True), provider, "m")
    no = sl.build_lesson("q about maths", "en", Gate(enabled=True, allowed=False), provider, "m")
    assert off == {"kind": "unavailable", "reason": "off"}
    assert no == {"kind": "unavailable", "reason": "consent"}
    assert provider.calls == []


def test_cut_off_json_is_retried_once_then_unavailable() -> None:
    cut = _lesson_json()[:120]
    provider = FakeProvider([cut, cut])
    out = sl.build_lesson("what is tunnelling", "en", OPEN, provider, "m")
    assert out == {"kind": "unavailable", "reason": "checks"}
    assert len(provider.calls) == sl.MAX_ATTEMPTS


def test_a_cut_off_first_try_is_recovered_by_the_second() -> None:
    provider = FakeProvider([_lesson_json()[:120], _lesson_json()])
    out = sl.build_lesson("what is tunnelling", "en", OPEN, provider, "m")
    assert out["kind"] == "lesson"
    assert len(provider.calls) == 2


def test_a_provider_error_is_retried_then_unavailable() -> None:
    provider = FakeProvider([ProviderError("down"), ProviderError("down")])
    out = sl.build_lesson("what is tunnelling", "en", OPEN, provider, "m")
    assert out == {"kind": "unavailable", "reason": "provider_error"}


def test_the_refuse_signal_becomes_out_of_scope() -> None:
    out = sl.build_lesson("what is tunnelling", "en", OPEN, FakeProvider(['{"refuse": true}']), "m")
    assert out["kind"] == "out_of_scope"


def test_the_question_travels_inside_student_text_tags() -> None:
    provider = FakeProvider([_lesson_json()])
    sl.build_lesson("what is tunnelling", "en", OPEN, provider, "m")
    assert "<student_text>" in provider.calls[0].user
    assert "what is tunnelling" in provider.calls[0].user


# ── misconception tags ───────────────────────────────────────────────────────


def test_each_wrong_option_keeps_a_short_tag_and_the_right_one_never_has_one() -> None:
    tagged = [dict(b) for b in _blocks()]
    tagged[1]["misconceptions"] = [
        "idea A",
        "  idea   B  with   spaces ",
    ]
    tagged[1]["correct"] = 1
    tagged[4]["misconceptions"] = ["x" * 200, None, "idea C", "idea D"]
    tagged[4]["correct"] = 2
    cleaned = sl.clean_lesson({"blocks": tagged})
    assert cleaned is not None
    predict, check = cleaned["blocks"][1], cleaned["blocks"][4]
    assert predict["misconceptions"] == ["idea A", None]  # the right option (1) has none
    assert check["misconceptions"][2] is None
    assert check["misconceptions"][0] == "x" * sl.MAX_TAG_CHARS
    assert check["misconceptions"][3] == "idea D"


def test_tags_of_the_wrong_shape_are_dropped_not_guessed() -> None:
    odd = [dict(b) for b in _blocks()]
    odd[1]["misconceptions"] = ["only one tag for two options", "b", "c"]
    odd[4]["misconceptions"] = "not a list"
    cleaned = sl.clean_lesson({"blocks": odd})
    assert cleaned is not None
    assert cleaned["blocks"][1]["misconceptions"] == []
    assert cleaned["blocks"][4]["misconceptions"] == []


# ── the opening and the rest ─────────────────────────────────────────────────


def _opening_json() -> str:
    return json.dumps({"level": "school", "objectives": ["Explain it"], "blocks": _blocks()[:2]})


def _rest_json(blocks: list[dict[str, Any]] | None = None) -> str:
    return json.dumps({"blocks": blocks or _blocks()[2:]})


def test_the_opening_is_exactly_a_hook_then_a_prediction() -> None:
    out = sl.build_opening("what is tunnelling", "en", OPEN, FakeProvider([_opening_json()]), "m")
    assert out["kind"] == "opening"
    assert [b["kind"] for b in out["blocks"]] == ["hook", "predict"]


@pytest.mark.parametrize(
    "blocks",
    [
        _blocks()[:1],  # a hook alone
        [_blocks()[1], _blocks()[0]],  # wrong order
        _blocks()[2:4],  # no hook or prediction
    ],
)
def test_an_opening_of_the_wrong_shape_is_refused_after_a_retry(
    blocks: list[dict[str, Any]],
) -> None:
    reply = json.dumps({"blocks": blocks})
    provider = FakeProvider([reply, reply])
    out = sl.build_opening("what is tunnelling", "en", OPEN, provider, "m")
    assert out == {"kind": "unavailable", "reason": "checks"}
    assert len(provider.calls) == sl.MAX_ATTEMPTS


def test_the_opening_prompt_asks_for_two_blocks_and_the_rest_prompt_carries_the_opening() -> None:
    opening = sl.clean_client_opening(_blocks()[:2])
    assert opening is not None
    first = sl.build_prompt("q", "en", False, None, "opening")
    assert "ONLY the first two blocks" in first.user
    rest = sl.build_prompt("q", "en", False, opening, "rest")
    assert "<opening_blocks>" in rest.user and "A surprising fact." in rest.user
    assert "is data" in rest.user and "do not write another hook" in rest.user


def test_the_rest_follows_the_opening_and_never_adds_a_second_hook() -> None:
    opening = sl.clean_client_opening(_blocks()[:2])
    assert opening is not None
    extra_hook = [_blocks()[0], *_blocks()[2:]]
    out = sl.build_rest(
        "q about maths", "en", opening, OPEN, FakeProvider([_rest_json(extra_hook)]), "m"
    )
    assert out["kind"] == "rest"
    assert "hook" not in [b["kind"] for b in out["blocks"]]
    assert any(b["kind"] == "check" for b in out["blocks"])


def test_a_rest_with_too_few_blocks_or_no_check_is_refused() -> None:
    opening = sl.clean_client_opening(_blocks()[:2])
    assert opening is not None
    for blocks in (_blocks()[2:4], [b for b in _blocks()[2:] if b["kind"] != "check"]):
        out = sl.build_rest(
            "q about maths", "en", opening, OPEN, FakeProvider([_rest_json(blocks)] * 2), "m"
        )
        assert out == {"kind": "unavailable", "reason": "checks"}


def test_an_opening_from_the_page_is_cleaned_like_any_model_text() -> None:
    hostile = [dict(b) for b in _blocks()[:2]]
    hostile[0]["text"] = "x " * 1000
    cleaned = sl.clean_client_opening(hostile)
    assert cleaned is not None
    assert len(cleaned[0]["text"]) <= 500
    assert sl.clean_client_opening("nope") is None
    assert sl.clean_client_opening([{"kind": "quiz"}]) is None
    assert sl.clean_client_opening(_blocks()[1:3]) is None  # not a hook then a prediction


def test_only_the_opening_skips_thinking_and_uses_a_small_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    made: list[ExplainProvider] = []
    real = ExplainProvider

    class Spy(real):  # type: ignore[misc, valid-type]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            made.append(self)

        def complete(self, prompt: Any, model: str) -> Any:
            raise ProviderError("stop here")

    monkeypatch.setattr(sl, "ExplainProvider", Spy)
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "llm_story_model", "")
    monkeypatch.setattr(settings, "llm_model_strong", "anthropic/claude-haiku-5-5")
    opening = sl.clean_client_opening(_blocks()[:2])
    assert opening is not None
    sl.build_opening("what is tunnelling", "en", OPEN)
    sl.build_rest("what is tunnelling", "en", opening, OPEN)
    sl.build_lesson("what is tunnelling", "en", OPEN)
    assert [(p.thinking_off, p.max_tokens) for p in made[:1]] == [(True, sl.OPENING_TOKENS)]
    assert all(not p.thinking_off and p.max_tokens == sl.MAX_TOKENS for p in made[1:])


def _sent_body(
    monkeypatch: pytest.MonkeyPatch, provider: ExplainProvider, model: str
) -> dict[str, Any]:
    """Run one completion against a fake HTTP layer and return the JSON body that was sent."""
    from app.explain import service as explain_service
    from app.llm.prompt import Prompt

    sent: dict[str, Any] = {}

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "content": [{"type": "text", "text": "{}"}],
                    "choices": [{"message": {"content": "{}"}}],
                    "usage": {},
                }
            ).encode()

    def fake_urlopen(request: Any, timeout: float = 0) -> Response:
        sent.update(json.loads(request.data.decode()))
        return Response()

    monkeypatch.setattr(explain_service.urllib.request, "urlopen", fake_urlopen)
    provider.complete(Prompt(system="s", user="u", version="v", max_words=10), model)
    return sent


def test_anthropic_gets_the_no_thinking_switch_only_when_asked_and_others_never(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anthropic = "anthropic/claude-haiku-5-5"
    off = _sent_body(monkeypatch, ExplainProvider(api_key="k", thinking_off=True), anthropic)
    assert off["thinking"] == {"type": "disabled"}
    default = _sent_body(monkeypatch, ExplainProvider(api_key="k"), anthropic)
    assert "thinking" not in default
    other = _sent_body(monkeypatch, ExplainProvider(api_key="k", thinking_off=True), "groq/m")
    assert "thinking" not in other  # a provider with no such switch is never sent the field


# ── the endpoints ────────────────────────────────────────────────────────────


def test_the_opening_endpoint_needs_a_student(client: TestClient, world: World) -> None:
    r = client.post(
        "/explain/lesson/opening",
        json={"prompt": "tunnelling"},
        headers=auth_header(world.parent_token),
    )
    assert r.status_code == 403


def test_the_opening_endpoint_passes_the_gate_and_a_guest_free_scope(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    def fake(question: str, language: str, gate: Any, restricted: bool) -> dict[str, Any]:
        seen.update(question=question, language=language, gate=gate, restricted=restricted)
        return {"kind": "opening", "blocks": []}

    monkeypatch.setattr(explain_router, "build_opening", fake)
    monkeypatch.setattr(settings, "explain_enabled", True)
    r = client.post(
        "/explain/lesson/opening",
        json={"prompt": "tunnelling", "language": "en"},
        headers=auth_header(world.student_token),
    )
    assert r.status_code == 200 and r.json()["kind"] == "opening"
    assert seen["gate"].enabled is True and seen["restricted"] is True


def test_the_lesson_endpoint_continues_from_a_clean_opening_and_refuses_a_bad_one(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    def fake_rest(question: str, language: str, opening: Any, gate: Any, restricted: bool) -> Any:
        seen["opening"] = opening
        return {"kind": "rest", "blocks": []}

    monkeypatch.setattr(explain_router, "build_rest", fake_rest)
    monkeypatch.setattr(settings, "explain_enabled", True)
    headers = auth_header(world.student_token)

    good = client.post(
        "/explain/lesson",
        json={"prompt": "tunnelling", "opening": _blocks()[:2]},
        headers=headers,
    )
    assert good.json()["kind"] == "rest"
    assert [b["kind"] for b in seen["opening"]] == ["hook", "predict"]

    bad = client.post(
        "/explain/lesson",
        json={"prompt": "tunnelling", "opening": [{"kind": "quiz"}]},
        headers=headers,
    )
    assert bad.json() == {"kind": "unavailable", "reason": "bad_opening"}

    too_many = client.post(
        "/explain/lesson", json={"prompt": "x", "opening": _blocks()}, headers=headers
    )
    assert too_many.status_code == 422  # more than four blocks is not an opening
