from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pytest

from app.learner.bkt import BktParams
from app.learner.bktf import AttemptKind, BktFParams
from app.learner.bktf_shadow import compare, replay_shadow, shadow_params
from app.learner.bktf_sim import simulate_learner
from app.learner.types import LearnerEvent

LEGACY = BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)
SKILLS = {"s1": LEGACY}
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


def ev(item: str, event_type: str = "answer", **kwargs) -> LearnerEvent:
    base = {"item_id": item, "skill_id": "s1", "event_type": event_type, "session_id": "sess"}
    base.update(kwargs)
    return LearnerEvent(**base)  # type: ignore[arg-type]


def test_one_step_per_item_and_a_retry_adds_none() -> None:
    steps = replay_shadow(
        [ev("a", correct=False), ev("a", correct=True), ev("b", correct=True)], SKILLS
    )
    assert [s.item_id for s in steps] == ["a", "b"]
    assert steps[0].correct is False


def test_attempt_kinds_come_from_hints_and_speed() -> None:
    log = [
        ev("a", "request_hint"),
        ev("a", correct=True, latency_ms=9000),
        ev("b", correct=True, latency_ms=300),
        ev("c", correct=True, latency_ms=9000),
        ev("d", correct=True),
    ]
    kinds = [s.kind for s in replay_shadow(log, SKILLS)]
    assert kinds == [
        AttemptKind.HINTED,
        AttemptKind.RAPID_GUESS,
        AttemptKind.VALID,
        AttemptKind.VALID,
    ]


def test_a_fast_answer_after_a_hint_is_still_hinted() -> None:
    log = [ev("a", "request_hint"), ev("a", correct=True, latency_ms=100)]
    assert replay_shadow(log, SKILLS)[0].kind is AttemptKind.HINTED


def test_gap_comes_from_timestamps() -> None:
    log = [
        ev("a", correct=True, at=T0),
        ev("b", correct=True, at=T0 + timedelta(days=10)),
        ev("c", correct=True, at=T0 + timedelta(days=10, hours=12)),
    ]
    assert [round(s.gap_days, 3) for s in replay_shadow(log, SKILLS)] == [0.0, 10.0, 0.5]


def test_without_timestamps_there_is_no_forgetting_and_it_matches_the_live_model() -> None:
    log = [
        ev(i, correct=c)
        for i, c in zip("abcdef", (True, False, True, True, False, True), strict=True)
    ]
    for step in replay_shadow(log, SKILLS):
        assert step.gap_days == 0.0
        assert step.p_shadow == pytest.approx(step.p_live)
        assert step.predicted_shadow == pytest.approx(step.predicted_live)


def test_checkpoint_and_non_answer_events_make_no_steps() -> None:
    log = [
        ev("a", pool="checkpoint", correct=True),
        ev("a", "explain_back"),
        LearnerEvent(item_id="", skill_id="", event_type="session_end", session_id="sess"),
        ev("b", correct=True),
    ]
    assert [s.item_id for s in replay_shadow(log, SKILLS)] == ["b"]


def test_a_long_break_lowers_the_shadow_prediction_but_not_the_live_one() -> None:
    log = [ev(i, correct=True, at=T0) for i in "abcdef"] + [
        ev("z", correct=True, at=T0 + timedelta(days=90))
    ]
    last = replay_shadow(log, SKILLS)[-1]
    assert last.predicted_shadow < last.predicted_live


def test_replay_is_deterministic() -> None:
    log = [ev(i, correct=i != "c", at=T0 + timedelta(days=n)) for n, i in enumerate("abcde")]
    assert replay_shadow(log, SKILLS) == replay_shadow(log, SKILLS)


def test_custom_shadow_parameters_are_used() -> None:
    quick = {"s1": BktFParams(0.2, 0.15, 0.1, 0.2, tau_days=1.0)}
    log = [ev("a", correct=True, at=T0), ev("b", correct=True, at=T0 + timedelta(days=5))]
    default = replay_shadow(log, SKILLS)[1]
    fast = replay_shadow(log, SKILLS, quick)[1]
    assert fast.predicted_shadow < default.predicted_shadow


def test_shadow_params_copy_the_live_values() -> None:
    p = shadow_params(LEGACY, tau_days=7.0)
    assert (p.p_init, p.p_learn, p.p_slip, p.p_guess, p.tau_days) == (0.2, 0.15, 0.1, 0.2, 7.0)


def test_comparing_nothing_is_an_error() -> None:
    with pytest.raises(ValueError):
        compare([])


def test_shadow_beats_live_on_logs_from_learners_who_forget() -> None:
    """End to end: simulated learners -> event log -> replay -> comparison."""
    truth = BktFParams(0.25, 0.12, 0.08, 0.2, tau_days=4.0)
    rng = random.Random(11)
    steps = []
    for learner in range(300):
        gaps = [0.0] + [rng.choice([0.0, 0.5, 2.0, 7.0, 14.0]) for _ in range(11)]
        kinds = [AttemptKind.RAPID_GUESS if rng.random() < 0.1 else AttemptKind.VALID for _ in gaps]
        attempts = simulate_learner(truth, gaps, kinds, rng)
        now, log = T0, []
        for n, attempt in enumerate(attempts):
            now += timedelta(days=attempt.gap_days)
            fast = attempt.kind is AttemptKind.RAPID_GUESS
            log.append(
                ev(
                    f"l{learner}-i{n}",
                    correct=attempt.correct,
                    at=now,
                    latency_ms=300 if fast else 9000,
                )
            )
        legacy = {"s1": BktParams(0.25, 0.12, 0.08, 0.2)}
        shadow = {"s1": truth}
        steps += replay_shadow(log, legacy, shadow)
    result = compare(steps)
    assert result.attempts == 300 * 12
    assert result.shadow_is_better
    assert result.shadow_log_loss < result.live_log_loss - 0.01
