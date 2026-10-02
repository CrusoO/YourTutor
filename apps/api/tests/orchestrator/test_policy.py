from __future__ import annotations

import inspect
from datetime import timedelta

from app.content.validator import item_tier
from app.orchestrator.policy import policy
from app.orchestrator.types import (
    HARD_ACTIVE_MS,
    IDLE_END_MS,
    LATENCY_CAP_MS,
    SOFT_ACTIVE_MS,
    Event,
    SessionState,
)
from app.verifier.check import leak_check
from tests.orchestrator.conftest import (
    NOW,
    catalog_item,
    due_card,
    make_learner,
    make_session,
)


def _start_practice(session: SessionState, learner=None):
    learner = learner or make_learner()
    action = policy(learner, session, None)
    if action.type == "predict":
        policy(learner, session, Event(type="predict_response", text="maybe 5"))
        action = policy(learner, session, Event(type="continue"))
    return learner, action


def test_policy_is_pure_and_has_required_signature() -> None:
    sig = inspect.signature(policy)
    assert list(sig.parameters) == ["learner", "session", "last_event"]
    assert policy.__module__ == "app.orchestrator.policy"
    source = inspect.getsource(policy)
    assert "open(" not in source
    assert "requests" not in source


def test_actions_carry_transition_metadata() -> None:
    session = make_session()
    learner = make_learner()
    first = policy(learner, session, None)
    assert first.state_before == "start"
    assert first.state_after == "predict"
    assert first.rule_id == "R01"


def test_events_include_predict_response_and_continue() -> None:
    session = make_session()
    learner = make_learner()
    first = policy(learner, session, None)
    assert first.type == "predict"
    mid = policy(learner, session, Event(type="predict_response", text="x is small"))
    assert mid.type == "worked_example"
    shown = policy(learner, session, Event(type="continue"))
    assert shown.type == "show_item"


def test_predict_and_worked_example_only_for_new_skill() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner = make_learner()
    action = policy(learner, session, None)
    assert action.type == "show_item"
    assert action.type != "predict"


def test_no_reveal_on_hint_1_or_2_and_leak_check() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, _ = _start_practice(session)
    h1 = policy(learner, session, Event(type="request_hint"))
    assert h1.type == "hint"
    assert h1.hint_level == 1
    assert h1.type != "reveal_solution"
    assert not leak_check(h1.text or "", "5", level=1)
    h2 = policy(learner, session, Event(type="request_hint"))
    assert h2.type == "hint"
    assert h2.hint_level == 2
    assert h2.type != "reveal_solution"
    assert not leak_check(h2.text or "", "5", level=2)
    assert leak_check("The answer is 5", "5", level=1)
    assert not leak_check("The answer is 5", "5", level=3)


def test_hint_3_never_returned_as_retry_hint() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, _ = _start_practice(session)
    policy(learner, session, Event(type="request_hint"))
    policy(learner, session, Event(type="request_hint"))
    third = policy(learner, session, Event(type="request_hint"))
    assert not (third.type == "hint" and third.hint_level == 3)


def test_reveal_after_wrong_following_hint2_starts_with_hint3() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, start = _start_practice(session)
    policy(learner, session, Event(type="request_hint"))
    policy(learner, session, Event(type="request_hint"))
    reveal = policy(learner, session, Event(type="answer", response="19", item_id=start.item_id))
    assert reveal.type == "reveal_solution"
    assert (reveal.text or "").startswith("Subtract 7")


def test_show_solution_after_two_hints_reveals() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, _ = _start_practice(session)
    policy(learner, session, Event(type="request_hint"))
    policy(learner, session, Event(type="request_hint"))
    reveal = policy(learner, session, Event(type="show_solution"))
    assert reveal.type == "reveal_solution"


def test_after_hint_retry_same_practice_item() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, start = _start_practice(session)
    hint = policy(learner, session, Event(type="request_hint"))
    assert hint.type == "hint"
    assert session.phase == "practice"
    assert session.current_item_id == start.item_id


def test_single_bkt_update_then_hinted_correct() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, start = _start_practice(session)
    policy(learner, session, Event(type="request_hint"))
    after_hint = learner.mastery["MATH.S1"].p_known
    policy(learner, session, Event(type="answer", response="5", item_id=start.item_id))
    row = learner.mastery["MATH.S1"]
    assert row.p_known == after_hint
    assert row.hinted_correct == 1
    assert row.unhinted_correct == 0


def test_first_answer_updates_bkt_once() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, start = _start_practice(session)
    policy(learner, session, Event(type="answer", response="5", item_id=start.item_id))
    row = learner.mastery["MATH.S1"]
    assert row.attempts == 1
    assert row.unhinted_correct == 1


def test_explain_back_once_after_unhinted_correct() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, start = _start_practice(session)
    action = policy(learner, session, Event(type="answer", response="5", item_id=start.item_id))
    assert action.type == "explain_back_prompt"
    skipped = policy(learner, session, Event(type="continue"))
    assert skipped.type != "explain_back_prompt"


def test_explain_back_without_ai_stores_text_no_grade() -> None:
    session = make_session(introduced={"MATH.S1"})
    session.has_ai_processing = False
    session.has_api_key = False
    learner, start = _start_practice(session)
    policy(learner, session, Event(type="answer", response="5", item_id=start.item_id))
    p_before = learner.mastery["MATH.S1"].p_known
    result = policy(learner, session, Event(type="explain_back", text="I subtracted."))
    assert result.grade is None
    assert result.store_text is True
    assert result.llm_called is False
    assert session.stored_explain_text == "I subtracted."
    assert "Subtract" in (result.text or "")
    assert learner.mastery["MATH.S1"].p_known == p_before


def test_warmup_skipped_when_no_due_cards() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner = make_learner()
    action = policy(learner, session, None)
    assert action.type != "warmup_item"


def test_warmup_at_most_three_when_due() -> None:
    items = tuple(catalog_item(f"ITEM.W{i}", difficulty=0.3) for i in range(4))
    session = make_session(*items, introduced={"MATH.S1"})
    learner = make_learner()
    learner.cards["MATH.S1"] = due_card("MATH.S1")
    first = policy(learner, session, None)
    assert first.type == "warmup_item"
    count = 1
    while session.warmup_left > 0:
        policy(
            learner,
            session,
            Event(type="answer", response="5", item_id=session.current_item_id),
        )
        count += 1
        if count > 5:
            break
    assert count <= 4


def test_prerequisite_below_0_6_before_target() -> None:
    intro = catalog_item("ITEM.INTRO", skill="MATH.INTRO", difficulty=0.2)
    target = catalog_item("ITEM.T", skill="MATH.T", difficulty=0.2)
    session = make_session(
        intro,
        target,
        overlay=("MATH.T",),
        prereqs={"MATH.T": ("MATH.INTRO",)},
        introduced={"MATH.T", "MATH.INTRO"},
    )
    session.bkt_params["MATH.INTRO"] = session.bkt_params["MATH.T"]
    learner = make_learner(p_known={"MATH.T": 0.3, "MATH.INTRO": 0.5})
    action = policy(learner, session, None)
    assert action.skill_id == "MATH.INTRO"


def test_item_tiers_and_least_recently_shown() -> None:
    older = catalog_item("ITEM.OLD", difficulty=0.2, last_shown_at=NOW - timedelta(days=3))
    newer = catalog_item("ITEM.NEW", difficulty=0.25, last_shown_at=NOW - timedelta(days=1))
    session = make_session(newer, older, introduced={"MATH.S1"})
    learner = make_learner(p_known={"MATH.S1": 0.2})
    action = policy(learner, session, None)
    assert action.item_id == "ITEM.OLD"
    hard = catalog_item("ITEM.HARD", difficulty=0.9)
    medium = catalog_item("ITEM.MED", difficulty=0.5)
    easy = catalog_item("ITEM.EASY", difficulty=0.2)
    session_h = make_session(hard, medium, easy, introduced={"MATH.S1"})
    learner_h = make_learner(p_known={"MATH.S1": 0.9})
    picked = policy(learner_h, session_h, None)
    assert picked.item_id == "ITEM.HARD"
    assert item_tier(0.2) == "easy"
    assert item_tier(0.5) == "medium"
    assert item_tier(0.9) == "hard"


def test_active_ms_caps_idle_and_resume() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, start = _start_practice(session)
    policy(
        learner,
        session,
        Event(type="answer", response="5", item_id=start.item_id, latency_ms=10_000),
    )
    assert session.active_ms == 10_000
    session.active_ms = 0
    policy(learner, session, Event(type="idle_nudge", latency_ms=700_000))
    assert session.active_ms == LATENCY_CAP_MS
    session.last_active_at = NOW - timedelta(milliseconds=IDLE_END_MS)
    ended = policy(learner, session, Event(type="answer", response="1"))
    assert ended.type == "end_session"
    assert ended.ended_reason == "idle"
    assert ended.resumable is True
    session.last_action = start
    resumed = policy(learner, session, Event(type="resume"))
    assert resumed.item_id == start.item_id


def test_soft_and_hard_caps() -> None:
    session = make_session(introduced={"MATH.S1"})
    session.active_ms = HARD_ACTIVE_MS
    learner = make_learner()
    action = policy(learner, session, None)
    assert action.ended_reason == "hard_cap"
    session2 = make_session(introduced={"MATH.S1"})
    session2.active_ms = SOFT_ACTIVE_MS
    action2 = policy(make_learner(), session2, None)
    assert action2.ended_reason == "soft_cap"


def test_diagnostic_no_hints_no_reveal_seeds_mastery() -> None:
    d1 = catalog_item("ITEM.D1", pool="diagnostic")
    session = make_session(d1, session_type="diagnostic")
    learner = make_learner()
    first = policy(learner, session, None)
    assert first.type == "show_item"
    blocked = policy(learner, session, Event(type="request_hint"))
    assert blocked.rejected is True
    done = policy(learner, session, Event(type="answer", response="5", item_id="ITEM.D1"))
    assert done.type == "end_session"
    assert "MATH.S1" in learner.mastery
    assert learner.mastery["MATH.S1"].attempts >= 1


def test_checkpoint_score_does_not_update_mastery_or_fsrs() -> None:
    c1 = catalog_item("ITEM.C1", pool="checkpoint")
    session = make_session(c1, session_type="checkpoint")
    learner = make_learner(p_known={"MATH.S1": 0.4})
    learner.cards.clear()
    policy(learner, session, None)
    policy(learner, session, Event(type="answer", response="5", item_id="ITEM.C1"))
    assert learner.mastery["MATH.S1"].p_known == 0.4
    assert learner.cards == {}


def test_unmatched_wrong_uses_generic_hint() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, start = _start_practice(session)
    hint = policy(learner, session, Event(type="answer", response="99", item_id=start.item_id))
    assert hint.type == "hint"
    assert hint.hint_level == 1
    assert hint.misconception_id is None


def test_matched_misconception_on_hint() -> None:
    item = catalog_item(rules=(("MC.WRONG", ("19",)),))
    session = make_session(item, introduced={"MATH.S1"})
    learner, start = _start_practice(session)
    hint = policy(learner, session, Event(type="answer", response="19", item_id=start.item_id))
    assert hint.misconception_id == "MC.WRONG"


def test_idle_nudge_does_not_change_pedagogy() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, start = _start_practice(session)
    phase = session.phase
    item = session.current_item_id
    nudge = policy(learner, session, Event(type="idle_nudge"))
    assert nudge.type == "nudge"
    assert session.phase == phase
    assert session.current_item_id == item
    assert start.item_id == item


def test_checkpoint_items_never_in_practice_selection() -> None:
    practice = catalog_item("ITEM.P")
    checkpoint = catalog_item("ITEM.C", pool="checkpoint", difficulty=0.1)
    session = make_session(checkpoint, practice, introduced={"MATH.S1"})
    learner = make_learner(p_known={"MATH.S1": 0.2})
    action = policy(learner, session, None)
    assert action.item_id == "ITEM.P"
    assert action.item_id != "ITEM.C"


def test_similar_item_different_approved_same_skill_and_tier() -> None:
    a = catalog_item("ITEM.A", difficulty=0.25)
    b = catalog_item("ITEM.B", difficulty=0.28, answer="4")
    session = make_session(a, b, introduced={"MATH.S1"})
    learner, start = _start_practice(session)
    policy(learner, session, Event(type="request_hint"))
    policy(learner, session, Event(type="request_hint"))
    policy(learner, session, Event(type="show_solution"))
    similar = policy(learner, session, Event(type="continue"))
    assert similar.type == "similar_item"
    assert similar.item_id != start.item_id
    assert similar.skill_id == "MATH.S1"
    picked = session.item(similar.item_id)
    shown = session.item(start.item_id)
    assert picked is not None and shown is not None
    assert item_tier(picked.difficulty) == item_tier(shown.difficulty)


def test_consent_revoked_ends_and_no_llm() -> None:
    session = make_session(introduced={"MATH.S1"})
    learner, _ = _start_practice(session)
    action = policy(learner, session, Event(type="consent_revoked"))
    assert action.type == "end_session"
    assert action.ended_reason == "consent_revoked"
    assert action.llm_called is False
    assert session.llm_called is False
