"""G1 step 8: other skills get one FSRS rating at session end (PLAN Decision: FSRS timing)."""

from __future__ import annotations

from datetime import timedelta

from app.orchestrator.policy import policy
from app.orchestrator.types import IDLE_END_MS, Event
from tests.orchestrator.conftest import NOW, catalog_item, due_card, make_learner, make_session

S1, S2 = "MATH.S1", "MATH.S2"


def _items(skill: str = S1, count: int = 4, prefix: str = "A"):
    return [catalog_item(f"{prefix}{n}", skill=skill, difficulty=0.3) for n in range(count)]


def _answer(learner, session, action, response="5"):
    return policy(learner, session, Event(type="answer", item_id=action.item_id, response=response))


def _end_by_idle(learner, session):
    return policy(learner, session, Event(type="idle_nudge", idle_ms=IDLE_END_MS))


def _practise(learner, session, *, correct_answers: int, wrong_answers: int = 0):
    action = policy(learner, session, None)
    if action.type == "predict":
        policy(learner, session, Event(type="predict_response", text="x"))
        action = policy(learner, session, Event(type="continue"))
    for _ in range(correct_answers):
        action = _answer(learner, session, action)
        if action.type == "explain_back_prompt":
            action = policy(learner, session, Event(type="continue"))
    for _ in range(wrong_answers):
        action = _answer(learner, session, action, response="0")
    return action


def test_session_end_rates_each_practised_skill_once() -> None:
    session = make_session(*_items(), introduced={S1})
    session.session_key = "session-1"
    learner = make_learner()
    _practise(learner, session, correct_answers=2)
    assert S1 not in learner.cards
    end = _end_by_idle(learner, session)
    assert end.type == "end_session"
    card = learner.cards[S1]
    assert card.due_at > NOW
    first_state = dict(card.fsrs_state)
    again = policy(learner, session, Event(type="idle_nudge", idle_ms=IDLE_END_MS))
    assert again.type == "end_session"
    assert learner.cards[S1].fsrs_state == first_state  # not rated twice


def test_unhinted_correct_rate_drives_the_rating() -> None:
    good_session = make_session(*_items(), introduced={S1})
    good_session.session_key = "good"
    good = make_learner()
    _practise(good, good_session, correct_answers=3)
    _end_by_idle(good, good_session)

    bad_session = make_session(*_items(prefix="B"), introduced={S1})
    bad_session.session_key = "bad"
    bad = make_learner()
    _practise(bad, bad_session, correct_answers=0, wrong_answers=1)
    _end_by_idle(bad, bad_session)

    assert good.cards[S1].due_at > bad.cards[S1].due_at
    assert bad.cards[S1].due_at <= NOW + timedelta(days=2)


def test_session_key_is_stable_across_policy_calls() -> None:
    """Counts must aggregate under one id even though each request rebuilds SessionState."""
    session = make_session(*_items(), introduced={S1})
    session.session_key = "stable"
    learner = make_learner()
    _practise(learner, session, correct_answers=2)
    assert set(session.bkt_memory["session_unhinted"]) == {"stable"}


def test_skill_reviewed_as_warmup_is_not_rated_again_at_session_end() -> None:
    session = make_session(*_items(), introduced={S1})
    session.session_key = "warm"
    learner = make_learner()
    learner.cards[S1] = due_card(S1, due=NOW - timedelta(days=1))
    action = policy(learner, session, None)
    assert action.type == "warmup_item"
    after_warmup = None
    action = _answer(learner, session, action)
    after_warmup = dict(learner.cards[S1].fsrs_state)
    for _ in range(2):
        if action.type == "explain_back_prompt":
            action = policy(learner, session, Event(type="continue"))
        if action.type == "show_item":
            action = _answer(learner, session, action)
    _end_by_idle(learner, session)
    assert learner.cards[S1].fsrs_state == after_warmup


def test_assessment_sessions_never_create_cards() -> None:
    for session_type in ("diagnostic", "checkpoint"):
        rows = [catalog_item(f"Q{n}", skill=S1) for n in range(3)]
        rows = [type(r)(**{**r.__dict__, "pool": session_type}) for r in rows]
        session = make_session(*rows, session_type=session_type, introduced={S1})
        learner = make_learner()
        action = policy(learner, session, None)
        for _ in range(3):
            if action.type != "show_item":
                break
            action = _answer(learner, session, action)
        _end_by_idle(learner, session)
        assert learner.cards == {}, session_type


def test_consent_revoked_end_creates_no_card() -> None:
    session = make_session(*_items(), introduced={S1})
    session.session_key = "revoked"
    learner = make_learner()
    _practise(learner, session, correct_answers=2)
    end = policy(learner, session, Event(type="consent_revoked"))
    assert end.type == "end_session" and end.ended_reason == "consent_revoked"
    assert learner.cards == {}
