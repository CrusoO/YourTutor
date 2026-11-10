"""The learner's own "I don't know" in practice (FIX-PLAN B1-5): honest data, no BKT update,
the next hint at once, never the answer early, and no endless loop. Pure policy: no database."""

from __future__ import annotations

from dataclasses import replace

from app.learner.types import LearnerState
from app.orchestrator.policy import policy
from app.orchestrator.types import Event, SessionState
from app.verifier.check import leak_check
from tests.orchestrator.conftest import ask_hint, catalog_item, make_learner, make_session


def _start(**fields):  # type: ignore[no-untyped-def]
    item = replace(catalog_item(), **fields) if fields else catalog_item()
    session = make_session(item)
    learner = make_learner()
    action = policy(learner, session, None)
    if action.type == "predict":
        policy(learner, session, Event(type="predict_response", text="maybe 5"))
        policy(learner, session, Event(type="continue"))
    return learner, session


def _dk(learner: LearnerState, session: SessionState, **extra):  # type: ignore[no-untyped-def]
    return policy(learner, session, Event(type="dont_know", **extra))


def _snapshot(learner: LearnerState) -> object:
    return learner.snapshot()


def test_dont_know_gives_hint_one_without_the_stuck_picker() -> None:
    learner, session = _start()
    action = _dk(learner, session)
    assert action.type == "hint" and action.hint_level == 1
    assert action.text == "What undoes the operation?"


def test_dont_know_does_not_touch_mastery() -> None:
    learner, session = _start()
    before = _snapshot(learner)
    _dk(learner, session)
    _dk(learner, session)
    assert _snapshot(learner) == before  # not a miss, not evidence
    assert learner.mastery == {} or all(m.attempts == 0 for m in learner.mastery.values())


def test_a_help_request_still_counts_as_before() -> None:
    learner, session = _start()
    before = _snapshot(learner)
    action = ask_hint(learner, session)
    assert action.type == "hint"
    assert _snapshot(learner) != before  # existing behaviour is unchanged


def test_a_wrong_answer_still_counts_as_before() -> None:
    learner, session = _start()
    before = _snapshot(learner)
    policy(learner, session, Event(type="answer", response="9"))
    assert _snapshot(learner) != before


def test_dont_know_walks_the_ladder_then_reveals_then_stops() -> None:
    learner, session = _start()
    first = _dk(learner, session)
    second = _dk(learner, session)
    third = _dk(learner, session)
    assert (first.type, first.hint_level) == ("hint", 1)
    assert (second.type, second.hint_level) == ("hint", 2)
    assert third.type == "reveal_solution"
    assert session.hint_level_shown == 2
    # the item is finished: a further "I don't know" cannot loop on the reveal
    again = _dk(learner, session)
    assert again.rejected and again.guardrail_flag == "illegal_dont_know"
    assert session.reveals == 1
    assert learner.ladders["MATH.S1"].hinted == ["ITEM.A"]  # helped, never credited


def test_dont_know_never_shows_the_answer_before_the_reveal() -> None:
    leaking = "So x is 5."
    learner, session = _start(hints=((1, leaking), (2, "Do the same to both sides."), (3, "x = 5")))
    first = _dk(learner, session)
    assert first.type == "hint"
    assert not leak_check(first.text or "", "5", level=1)
    second = _dk(learner, session)
    assert not leak_check(second.text or "", "5", level=2)


def test_dont_know_after_a_wrong_answer_continues_the_ladder() -> None:
    learner, session = _start()
    wrong = policy(learner, session, Event(type="answer", response="9"))
    assert wrong.hint_level == 1
    after = _dk(learner, session)
    assert after.type == "hint" and after.hint_level == 2


def test_dont_know_is_not_a_wrong_answer_for_the_run_counters() -> None:
    learner, session = _start()
    _dk(learner, session)
    assert session.last_wrong_item_id is None
    assert session.last_correct is None


def test_dont_know_is_refused_in_assessments() -> None:
    for kind in ("diagnostic", "checkpoint"):
        session = make_session(session_type=kind)
        action = _dk(make_learner(), session)
        assert action.type != "hint"
        assert session.hint_level_shown == 0


def test_confidence_never_makes_dont_know_a_fragile_correct() -> None:
    """With CONFIDENCE_RULES on, "unsure" on a right answer is fragile. A don't-know is no answer,
    so it is never counted as one, even when a confidence tap rides along."""
    learner, session = _start()
    _dk(learner, session, confidence="unsure")
    ladder = learner.ladders.get("MATH.S1")
    assert ladder is None or ("ITEM.A" in ladder.hinted and not ladder.flags.get("fragile"))
    assert _snapshot(learner)["mastery"] == {} or all(  # type: ignore[index]
        m["attempts"] == 0
        for m in _snapshot(learner)["mastery"].values()  # type: ignore[index]
    )
    # the right answer after it is a hinted one, never an unhinted or fragile credit
    policy(learner, session, Event(type="answer", response="5", confidence="unsure"))
    row = learner.mastery.get("MATH.S1")
    assert row is None or row.unhinted_correct == 0


def test_replaying_the_log_matches_the_live_state() -> None:
    """A logged dont_know replays as "helped, no BKT update", like the live policy did."""
    from app.learner.mastery_service import apply_events
    from app.learner.types import LearnerEvent
    from app.orchestrator.types import default_params

    def ev(kind: str, correct: bool | None = None) -> LearnerEvent:
        return LearnerEvent(
            item_id="ITEM.A", skill_id="MATH.S1", event_type=kind, correct=correct, pool="practice"
        )

    params = {"MATH.S1": default_params()}
    only_dk = apply_events([ev("dont_know")], params)
    assert only_dk.mastery.get("MATH.S1") is None or only_dk.mastery["MATH.S1"].attempts == 0
    then_right = apply_events([ev("dont_know"), ev("answer", True)], params)
    assert then_right.mastery["MATH.S1"].unhinted_correct == 0
    assert then_right.mastery["MATH.S1"].attempts == 1
