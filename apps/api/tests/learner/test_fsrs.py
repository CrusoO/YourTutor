from __future__ import annotations

from datetime import UTC, datetime

from app.learner.bkt import BktParams
from app.learner.mastery_service import recompute_from_log
from app.learner.scheduler_fsrs import FixedClock
from app.learner.types import LearnerEvent

PARAMS = BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)
SKILLS = {"s1": PARAMS, "s2": PARAMS}
T0 = datetime(2026, 10, 2, 8, 0, tzinfo=UTC)
CLOCK = FixedClock(T0)


def test_fsrs_due_dates_deterministic() -> None:
    events = [
        LearnerEvent("w1", "s1", "answer", correct=True, is_warmup=True, session_id="a"),
    ]
    a = recompute_from_log(events, SKILLS, clock=CLOCK)
    b = recompute_from_log(events, SKILLS, clock=CLOCK)
    assert a.cards["s1"].due_at == b.cards["s1"].due_at == a.cards["s1"].due_at
    assert a.cards["s1"].due_at == T0 or a.cards["s1"].due_at >= T0


def test_checkpoint_and_explain_back_do_not_move_due() -> None:
    warmup = [
        LearnerEvent("w1", "s1", "answer", correct=True, is_warmup=True, session_id="a"),
    ]
    baseline = recompute_from_log(warmup, SKILLS, clock=CLOCK)
    extra = warmup + [
        LearnerEvent("c1", "s1", "answer", correct=True, pool="checkpoint", session_id="a"),
        LearnerEvent("c1", "s1", "explain_back", pool="practice", session_id="a"),
    ]
    after = recompute_from_log(extra, SKILLS, clock=CLOCK)
    assert after.cards["s1"].due_at == baseline.cards["s1"].due_at
    assert after.mastery["s1"].attempts == baseline.mastery["s1"].attempts
    assert after.mastery["s1"].p_known == baseline.mastery["s1"].p_known


def test_warmup_updates_immediately_other_skills_at_session_end() -> None:
    before_end = [
        LearnerEvent("w1", "s1", "answer", correct=True, is_warmup=True, session_id="a"),
        LearnerEvent("p1", "s2", "answer", correct=True, pool="practice", session_id="a"),
    ]
    mid = recompute_from_log(before_end, SKILLS, clock=CLOCK)
    assert "s1" in mid.cards
    assert "s2" not in mid.cards
    due_s1 = mid.cards["s1"].due_at
    ended = recompute_from_log(
        before_end + [LearnerEvent("", "s2", "session_end", session_id="a")],
        SKILLS,
        clock=CLOCK,
    )
    assert ended.cards["s1"].due_at == due_s1
    assert "s2" in ended.cards
    assert ended.cards["s2"].due_at >= T0
