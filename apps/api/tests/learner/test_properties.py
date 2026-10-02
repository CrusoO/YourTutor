from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from app.learner.bkt import BktParams, posterior
from app.learner.mastery_service import apply_event, recompute_from_log
from app.learner.scheduler_fsrs import FixedClock
from app.learner.types import LearnerEvent, LearnerState

PARAMS = BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)
SKILLS = {"s1": PARAMS}
CLOCK = FixedClock(datetime(2026, 10, 2, 12, 0, tzinfo=UTC))


def test_p_known_stays_in_unit_interval() -> None:
    p = 0.2
    for correct in (True, False, True, True, False, True, True, True, False):
        p = posterior(p, correct=correct, params=PARAMS)
        assert 0.0 <= p <= 1.0


def test_correct_answer_never_lowers_p_known() -> None:
    for start in (0.01, 0.2, 0.4, 0.6, 0.8, 0.95, 0.99):
        nxt = posterior(start, correct=True, params=PARAMS)
        assert nxt >= start - 1e-12


def test_recompute_equals_incremental() -> None:
    events = [
        LearnerEvent("i1", "s1", "answer", correct=False, session_id="a"),
        LearnerEvent("i1", "s1", "request_hint", session_id="a"),
        LearnerEvent("i1", "s1", "answer", correct=True, session_id="a"),
        LearnerEvent("i2", "s1", "answer", correct=True, session_id="a"),
        LearnerEvent("", "s1", "session_end", session_id="a", pool="practice"),
    ]
    full = recompute_from_log(events, SKILLS, clock=CLOCK)
    incremental = LearnerState()
    memory: dict = {
        "bkt_done": set(),
        "hinted": set(),
        "first_wrong": set(),
        "session_unhinted": defaultdict(lambda: defaultdict(lambda: [0, 0])),
        "warmup_skills": set(),
    }
    for event in events:
        apply_event(incremental, event, SKILLS, clock=CLOCK, memory=memory)
    assert incremental.snapshot() == full.snapshot()


def test_recompute_is_idempotent() -> None:
    events = [
        LearnerEvent("i1", "s1", "answer", correct=True, session_id="a"),
        LearnerEvent("i2", "s1", "answer", correct=False, session_id="a"),
    ]
    a = recompute_from_log(events, SKILLS, clock=CLOCK)
    b = recompute_from_log(events, SKILLS, clock=CLOCK)
    assert a.snapshot() == b.snapshot()
