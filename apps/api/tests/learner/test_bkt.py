from __future__ import annotations

from app.learner.bkt import BktParams, posterior
from app.learner.mastery_service import recompute_from_log
from app.learner.types import LearnerEvent

PARAMS = BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)
SKILLS = {"s1": PARAMS}


def ev(**kwargs) -> LearnerEvent:
    base = {
        "item_id": "i1",
        "skill_id": "s1",
        "event_type": "answer",
        "pool": "practice",
        "session_id": "sess",
    }
    base.update(kwargs)
    return LearnerEvent(**base)  # type: ignore[arg-type]


def test_first_unhinted_correct_one_bkt() -> None:
    state = recompute_from_log([ev(correct=True)], SKILLS)
    row = state.mastery["s1"]
    assert row.p_known == posterior(0.2, correct=True, params=PARAMS)
    assert row.attempts == 1
    assert row.unhinted_correct == 1
    assert row.hinted_correct == 0


def test_first_wrong_then_hinted_correct() -> None:
    events = [
        ev(correct=False),
        ev(event_type="request_hint", correct=None),
        ev(correct=True),
    ]
    state = recompute_from_log(events, SKILLS)
    row = state.mastery["s1"]
    assert row.p_known == posterior(0.2, correct=False, params=PARAMS)
    assert row.attempts == 1
    assert row.unhinted_correct == 0
    assert row.hinted_correct == 1


def test_first_request_hint_then_correct() -> None:
    events = [
        ev(event_type="request_hint", correct=None),
        ev(correct=True),
    ]
    state = recompute_from_log(events, SKILLS)
    row = state.mastery["s1"]
    assert row.p_known == posterior(0.2, correct=False, params=PARAMS)
    assert row.attempts == 1
    assert row.unhinted_correct == 0
    assert row.hinted_correct == 1


def test_two_answers_never_two_bkt_updates() -> None:
    once = recompute_from_log([ev(correct=True)], SKILLS)
    twice = recompute_from_log([ev(correct=True), ev(correct=True)], SKILLS)
    assert twice.mastery["s1"].p_known == once.mastery["s1"].p_known
    assert twice.mastery["s1"].attempts == 1


def test_bkt_updates_primary_skill_only() -> None:
    skills = {"s1": PARAMS, "s2": PARAMS}
    state = recompute_from_log([ev(correct=True, skill_id="s1")], skills)
    assert "s1" in state.mastery
    assert "s2" not in state.mastery


def test_mastered_requires_p_known_and_three_unhinted() -> None:
    events = [ev(item_id=f"i{n}", correct=True) for n in range(3)]
    state = recompute_from_log(events, SKILLS)
    row = state.mastery["s1"]
    assert row.unhinted_correct == 3
    if row.p_known >= 0.95:
        assert row.mastered
    else:
        assert not row.mastered
    high = PARAMS
    # keep answering until mastered or cap
    n = 3
    while not state.mastery["s1"].mastered and n < 40:
        n += 1
        events.append(ev(item_id=f"i{n}", correct=True))
        state = recompute_from_log(events, {"s1": high})
    assert state.mastery["s1"].mastered
    assert state.mastery["s1"].p_known >= 0.95
    assert state.mastery["s1"].unhinted_correct >= 3
