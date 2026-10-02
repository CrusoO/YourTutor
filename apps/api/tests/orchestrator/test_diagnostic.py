from __future__ import annotations

from app.orchestrator.diagnostic import LOW_PRIOR, is_dont_know
from app.orchestrator.policy import policy
from app.orchestrator.types import Event
from tests.orchestrator.conftest import catalog_item, make_learner, make_session


def _diag(item_id: str, skill: str, answer: str = "5") -> object:
    return catalog_item(item_id, skill=skill, pool="diagnostic", answer=answer)


def test_one_item_per_skill_then_complete() -> None:
    s1 = _diag("D1", "MATH.S1")
    s2 = _diag("D2", "MATH.S2", "4")
    session = make_session(
        s1,
        s2,
        session_type="diagnostic",
        overlay=("MATH.S1", "MATH.S2"),
        prereqs={"MATH.S2": ("MATH.S1",)},
    )
    learner = make_learner()
    first = policy(learner, session, None)
    assert first.item_id == "D1"
    second = policy(learner, session, Event(type="answer", response="5", item_id="D1"))
    assert second.item_id == "D2"
    done = policy(learner, session, Event(type="answer", response="4", item_id="D2"))
    assert done.type == "end_session"
    assert set(learner.mastery) == {"MATH.S1", "MATH.S2"}


def test_second_item_only_when_wrong_and_prereq_correct() -> None:
    s1 = _diag("D1", "MATH.S1")
    s2a = _diag("D2A", "MATH.S2", "4")
    s2b = _diag("D2B", "MATH.S2", "6")
    session = make_session(
        s1,
        s2a,
        s2b,
        session_type="diagnostic",
        overlay=("MATH.S1", "MATH.S2"),
        prereqs={"MATH.S2": ("MATH.S1",)},
    )
    learner = make_learner()
    policy(learner, session, None)
    policy(learner, session, Event(type="answer", response="5", item_id="D1"))
    shown = policy(learner, session, Event(type="answer", response="99", item_id="D2A"))
    assert shown.item_id == "D2B"
    done = policy(learner, session, Event(type="answer", response="6", item_id="D2B"))
    assert done.type == "end_session"
    assert learner.mastery["MATH.S2"].attempts == 1


def test_no_second_item_when_prereq_wrong() -> None:
    s1 = _diag("D1", "MATH.S1")
    s2a = _diag("D2A", "MATH.S2", "4")
    s2b = _diag("D2B", "MATH.S2", "6")
    session = make_session(
        s1,
        s2a,
        s2b,
        session_type="diagnostic",
        overlay=("MATH.S1", "MATH.S2"),
        prereqs={"MATH.S2": ("MATH.S1",)},
    )
    learner = make_learner()
    policy(learner, session, None)
    shown = policy(learner, session, Event(type="answer", response="99", item_id="D1"))
    assert shown.item_id == "D2A"
    done = policy(learner, session, Event(type="answer", response="99", item_id="D2A"))
    assert done.type == "end_session"
    assert done.item_id != "D2B"


def test_failed_twice_skips_dependents_low_prior() -> None:
    s1a = _diag("D1A", "MATH.S1")
    s1b = _diag("D1B", "MATH.S1", "3")
    s2 = _diag("D2", "MATH.S2", "4")
    s3 = _diag("D3", "MATH.S3", "7")
    session = make_session(
        s1a,
        s1b,
        s2,
        s3,
        session_type="diagnostic",
        overlay=("MATH.S1", "MATH.S2", "MATH.S3"),
        prereqs={"MATH.S2": ("MATH.S1",), "MATH.S3": ("MATH.S2",)},
    )
    learner = make_learner()
    policy(learner, session, None)
    policy(learner, session, Event(type="answer", response="99", item_id="D1A"))
    done = policy(learner, session, Event(type="answer", response="99", item_id="D1B"))
    assert done.type == "end_session"
    assert "MATH.S2" in session.skipped_skills
    assert "MATH.S3" in session.skipped_skills
    assert "MATH.S2" in session.skills_not_tested
    assert learner.mastery["MATH.S2"].p_known == LOW_PRIOR
    assert learner.mastery["MATH.S3"].p_known == LOW_PRIOR
    assert all(row["skill_id"] != "MATH.S2" for row in session.diagnostic_results)


def test_root_skill_gets_second_item_when_first_wrong() -> None:
    first = _diag("D1A", "MATH.S1")
    second = _diag("D1B", "MATH.S1", "3")
    session = make_session(
        first,
        second,
        session_type="diagnostic",
        overlay=("MATH.S1",),
        prereqs={},
    )
    learner = make_learner()
    policy(learner, session, None)
    shown = policy(learner, session, Event(type="answer", response="99", item_id="D1A"))
    assert shown.item_id == "D1B"
    done = policy(learner, session, Event(type="answer", response="3", item_id="D1B"))
    assert done.type == "end_session"
    assert learner.mastery["MATH.S1"].attempts == 1


def test_dont_know_is_incorrect_and_seeds_bkt() -> None:
    assert is_dont_know("I don't know")
    item = _diag("D1", "MATH.S1")
    session = make_session(item, session_type="diagnostic")
    learner = make_learner()
    policy(learner, session, None)
    done = policy(learner, session, Event(type="answer", response="I don't know", item_id="D1"))
    assert done.type == "end_session"
    assert session.diagnostic_results[0]["correct"] is False
    assert session.diagnostic_results[0]["dont_know"] is True
    assert learner.mastery["MATH.S1"].attempts == 1
    assert learner.mastery["MATH.S1"].p_known < 0.2


def test_diagnostic_caps_at_sixteen_items() -> None:
    items = [_diag(f"D{i}", "MATH.S1", "5") for i in range(20)]
    session = make_session(*items, session_type="diagnostic", overlay=("MATH.S1",))
    learner = make_learner()
    policy(learner, session, None)
    steps = 0
    while session.phase != "ended" and steps < 30:
        policy(learner, session, Event(type="answer", response="99", item_id=session.current_item_id))
        steps += 1
    assert session.items_completed <= 16
    assert session.ended_reason == "diagnostic_complete"
