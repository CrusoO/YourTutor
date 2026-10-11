"""G4 step 3: the gateway gates, calls the provider, post-checks, regenerates once, and falls
back to the authored text. The call log holds no student text."""

from __future__ import annotations

import random
import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LlmCallRow
from app.llm.gateway import Gate, Gateway, record_call
from app.llm.prompt import PromptContext
from app.llm.provider import FakeProvider, ProviderError
from app.llm.purposes import Purpose
from app.registries.loaders import load_grade_bands

BAND = {b.id: b for b in load_grade_bands()}["lower_secondary"]
OPEN = Gate(session_type="practice", has_ai_processing=True, has_api_key=True)
AUTHORED = "Take 4 off both sides."


def _ctx(purpose: Purpose = Purpose.personalise_hint, **over: Any) -> PromptContext:
    fields = {
        Purpose.personalise_hint: {
            "item_stem": "Solve x + 4 = 10",
            "hint_level": "1",
            "authored_hint": AUTHORED,
        },
        Purpose.grade_explain_back: {
            "student_text": "I took 4 from both sides.",
            "rubric": "Mentions undoing + 4.",
        },
        Purpose.encourage: {"trigger": "persisted"},
    }[purpose]
    base: dict[str, Any] = dict(
        purpose=purpose,
        band=BAND,
        language="en",
        source="Take 4 off both sides to keep the balance.",
        forbidden_answer="6",
        fields=fields,
    )
    base.update(over)
    return PromptContext(**base)


def _gateway(provider: FakeProvider, rate: float = 1.0) -> Gateway:
    return Gateway(
        provider, sample_rate=rate, rng=random.Random(1), models={"fast": "f", "strong": "s"}
    )


GOOD = "Think about what undoes adding 4."


def test_a_good_reply_is_used_and_the_provider_is_called_once() -> None:
    provider = FakeProvider([GOOD])
    out = _gateway(provider).generate(_ctx(), fallback=AUTHORED, gate=OPEN)
    assert out.text == GOOD and out.source == "llm" and out.llm_called
    assert out.attempts == 1 and out.failure_codes == [] and out.outcome == "llm"
    assert len(provider.calls) == 1
    assert out.prompt_version == "personalise_hint/v1"


@pytest.mark.parametrize(
    ("gate", "reason"),
    [
        (Gate("diagnostic", True, True), "mode"),
        (Gate("checkpoint", True, True), "mode"),
        (Gate("practice", False, True), "consent"),
        (Gate("practice", True, False), "no_key"),
    ],
)
def test_no_call_without_the_right_mode_consent_and_key(gate: Gate, reason: str) -> None:
    provider = FakeProvider([GOOD])
    out = _gateway(provider).generate(_ctx(), fallback=AUTHORED, gate=gate)
    assert provider.calls == []
    assert out.text == AUTHORED and out.source == "authored" and not out.llm_called
    assert out.outcome == "skipped" and out.skip_reason == reason


def test_one_bad_reply_is_regenerated_once_with_a_short_reason_not_the_bad_text() -> None:
    provider = FakeProvider(["The answer is 6.", GOOD])
    out = _gateway(provider).generate(_ctx(), fallback=AUTHORED, gate=OPEN)
    assert out.text == GOOD and out.attempts == 2 and out.failure_codes == ["leak"]
    retry_user = provider.calls[1].user
    assert "broke a rule: leak" in retry_user and "The answer is 6." not in retry_user


def test_two_bad_replies_fall_back_to_the_authored_text() -> None:
    provider = FakeProvider(["The answer is 6.", "So x is 6."])
    out = _gateway(provider).generate(_ctx(), fallback=AUTHORED, gate=OPEN)
    assert len(provider.calls) == 2  # regenerate once, never more
    assert out.text == AUTHORED and out.source == "authored" and out.outcome == "fallback"
    assert out.failure_codes == ["leak", "leak"] and out.llm_called


def test_provider_errors_count_as_attempts_and_never_raise() -> None:
    provider = FakeProvider([ProviderError("timeout"), GOOD])
    out = _gateway(provider).generate(_ctx(), fallback=AUTHORED, gate=OPEN)
    assert out.text == GOOD and out.failure_codes == ["provider_error"]
    both = _gateway(FakeProvider([ProviderError("x"), ProviderError("y")])).generate(
        _ctx(), fallback=AUTHORED, gate=OPEN
    )
    assert both.text == AUTHORED and both.outcome == "fallback"


def test_explain_back_grades_through_the_gateway_and_falls_back_without_a_grade() -> None:
    ctx = _ctx(Purpose.grade_explain_back)
    ok = _gateway(FakeProvider(["GRADE: good\nYou undid the + 4 step by step."])).generate(
        ctx, fallback="Model: take 4 off both sides.", gate=OPEN
    )
    assert ok.grade == "good" and ok.text == "You undid the + 4 step by step."
    bad = _gateway(FakeProvider(["no grade line", "still none"])).generate(
        ctx, fallback="Model: take 4 off both sides.", gate=OPEN
    )
    assert bad.grade is None and bad.text == "Model: take 4 off both sides."


def test_models_follow_the_purpose() -> None:
    fast = FakeProvider([GOOD])
    _gateway(fast).generate(_ctx(), fallback=AUTHORED, gate=OPEN)
    assert fast.models == ["f"]
    strong = FakeProvider(["GRADE: good\nYou undid the + 4 step by step."])
    _gateway(strong).generate(_ctx(Purpose.grade_explain_back), fallback="m", gate=OPEN)
    assert strong.models == ["s"]


def test_sampling_follows_the_rate() -> None:
    assert (
        _gateway(FakeProvider([GOOD]), rate=1.0)
        .generate(_ctx(), fallback=AUTHORED, gate=OPEN)
        .sampled
    )
    assert (
        not _gateway(FakeProvider([GOOD]), rate=0.0)
        .generate(_ctx(), fallback=AUTHORED, gate=OPEN)
        .sampled
    )


def test_skipped_calls_are_never_sampled() -> None:
    gate = Gate("diagnostic", True, True)
    assert (
        not _gateway(FakeProvider([]), rate=1.0)
        .generate(_ctx(), fallback=AUTHORED, gate=gate)
        .sampled
    )


def test_the_call_log_has_no_student_text_and_keeps_the_reply_only_when_sampled(
    db: Session,
) -> None:
    ctx = _ctx(Purpose.grade_explain_back)
    reply = "GRADE: good\nYou undid the + 4 step by step."
    sampled = _gateway(FakeProvider([reply]), rate=1.0).generate(ctx, fallback="m", gate=OPEN)
    unsampled = _gateway(FakeProvider([reply]), rate=0.0).generate(ctx, fallback="m", gate=OPEN)
    session_id = uuid.uuid4()
    record_call(db, sampled, ctx, session_id=None)
    record_call(db, unsampled, ctx, session_id=None)
    db.commit()
    rows = db.scalars(select(LlmCallRow).order_by(LlmCallRow.sampled.desc())).all()
    assert [r.sampled for r in rows] == [True, False]
    assert rows[0].output_text == "You undid the + 4 step by step."
    assert rows[1].output_text is None
    assert all(r.purpose == "grade_explain_back" and r.band_id == BAND.id for r in rows)
    assert all(r.prompt_version == "grade_explain_back/v1" and r.attempts == 1 for r in rows)
    dumped = " ".join(str(v) for r in rows for v in vars(r).values())
    assert "I took 4 from both sides" not in dumped  # the student's own words are never logged
    assert session_id  # (unused session ids are fine: the column is optional)
