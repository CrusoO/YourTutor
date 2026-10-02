from __future__ import annotations

from app.orchestrator.policy import policy
from app.orchestrator.types import Event
from tests.orchestrator.conftest import catalog_item, make_learner, make_session


def test_similar_item_falls_back_then_logs_content_gap() -> None:
    only = catalog_item("ITEM.ONLY", difficulty=0.2)
    other_skill = catalog_item("ITEM.OTHER", skill="MATH.S2", difficulty=0.2)
    session = make_session(
        only,
        other_skill,
        overlay=("MATH.S1", "MATH.S2"),
        introduced={"MATH.S1", "MATH.S2"},
    )
    learner = make_learner()
    start = policy(learner, session, None)
    assert start.item_id == "ITEM.ONLY"
    policy(learner, session, Event(type="request_hint"))
    policy(learner, session, Event(type="request_hint"))
    policy(learner, session, Event(type="show_solution"))
    follow = policy(learner, session, Event(type="continue"))
    assert session.content_gaps
    gap = session.content_gaps[0]
    assert gap["skill"] == "MATH.S1"
    assert gap["tier"] == "easy"
    assert "ITEM.ONLY" in gap["item_ids_seen"]
    assert "MATH.S1" in session.blocked_skills
    assert follow.item_id != "ITEM.ONLY" or follow.type == "end_session"
    if follow.type != "end_session":
        assert follow.skill_id == "MATH.S2"


def test_nearest_tier_used_when_same_tier_exhausted() -> None:
    easy = catalog_item("ITEM.E", difficulty=0.2)
    hard = catalog_item("ITEM.H", difficulty=0.9)
    session = make_session(easy, hard, introduced={"MATH.S1"})
    learner = make_learner()
    start = policy(learner, session, None)
    policy(learner, session, Event(type="request_hint"))
    policy(learner, session, Event(type="request_hint"))
    policy(learner, session, Event(type="show_solution"))
    similar = policy(learner, session, Event(type="continue"))
    assert similar.type == "similar_item"
    assert similar.item_id != start.item_id
    assert not session.content_gaps
