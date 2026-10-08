"""G2a policy: R30 diagnose before hint, R31 slip path, R32 stuck-point picker, help alias."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.learner.ladder import SkillLadder
from app.orchestrator.policy import policy
from app.orchestrator.types import Action, CatalogItem, Event, SessionState
from app.verifier.check import leak_check
from tests.orchestrator.conftest import catalog_item, make_learner, make_session

SKILL = "MATH.S1"
STEP_HINTS = (
    "First step: undo the plus.",
    "Second step: now undo the times.",
    "Last step: check it in the question.",
)


def _item(**fields: Any) -> CatalogItem:
    base: dict[str, Any] = {
        "slip_patterns": ({"kind": "sign_flip"}, {"kind": "off_by", "max_distance": 1}),
        "step_hints": STEP_HINTS,
        "hint_restate": "Let's read it again: what number makes x + 7 = 12 true?",
        "min_plausible_ms": 3000,
        "solution_steps": ("Subtract 7.", "x = 12 - 7", "x = 5"),
    }
    if "rules" in fields:
        fields["misconception_rules"] = fields.pop("rules")
    base.update(fields)
    return replace(catalog_item(), **base)


def _practice(item: CatalogItem | None = None, *, level: int = 0):
    item = item or _item()
    session = make_session(item, introduced={SKILL})
    learner = make_learner()
    first = policy(learner, session, None)
    assert first.type == "show_item"
    if level:  # the skill reaches this level while the item is on screen
        learner.ladders[SKILL] = SkillLadder(skill_id=SKILL, achieved=list(range(1, level + 1)))
    return learner, session, first


def _answer(learner, session, response: str, item_id: str, latency_ms: int | None = 9000) -> Action:
    return policy(
        learner,
        session,
        Event(type="answer", response=response, item_id=item_id, latency_ms=latency_ms),
    )


def _bkt_attempts(learner) -> int:
    return learner.mastery[SKILL].attempts if SKILL in learner.mastery else 0


# ---- R30 / R31 ----------------------------------------------------------------------------


def test_every_answer_is_diagnosed_and_the_result_is_kept_for_the_event() -> None:
    learner, session, first = _practice()
    _answer(learner, session, "99", first.item_id)
    assert session.last_diagnosis == {"class": "generic", "detail": None}
    learner, session, first = _practice()
    _answer(learner, session, "5", first.item_id)
    assert session.last_diagnosis == {"class": "none", "detail": None}


def test_a_slip_gets_check_your_work_and_uses_no_hint_level() -> None:
    learner, session, first = _practice(level=4)
    action = _answer(learner, session, "-5", first.item_id)
    assert action.type == "check_your_work"
    assert action.rule_id == "R31"
    assert action.extras["check_kind"] == "sign_flip"
    assert session.hint_level_shown == 0
    assert session.last_diagnosis == {"class": "slip", "detail": "sign_flip"}


def test_a_slip_still_counts_as_the_items_one_bkt_update() -> None:
    learner, session, first = _practice(level=4)
    _answer(learner, session, "-5", first.item_id)
    assert _bkt_attempts(learner) == 1
    _answer(learner, session, "-5", first.item_id)
    assert _bkt_attempts(learner) == 1


def test_a_second_wrong_answer_goes_to_the_normal_hint_ladder() -> None:
    learner, session, first = _practice(level=4)
    assert _answer(learner, session, "-5", first.item_id).type == "check_your_work"
    action = _answer(learner, session, "-5", first.item_id)
    assert action.type == "hint" and action.hint_level == 1


def test_no_slip_path_below_level_4() -> None:
    learner, session, first = _practice(level=3)
    action = _answer(learner, session, "-5", first.item_id)
    assert action.type == "hint" and action.hint_level == 1


def test_a_slip_then_the_right_answer_moves_on() -> None:
    learner, session, first = _practice(level=4)
    _answer(learner, session, "-5", first.item_id)
    action = _answer(learner, session, "5", first.item_id)
    assert action.type in {"explain_back_prompt", "show_item", "predict", "end_session"}
    assert session.items_completed == 1


def test_a_misconception_gets_a_targeted_hint() -> None:
    item = _item(rules=(("MC.FORGET", ("19",)),))
    learner, session, first = _practice(item)
    session.misconception_text = {"MC.FORGET": "It looks like only one side changed."}
    action = _answer(learner, session, "19", first.item_id)
    assert action.type == "hint" and action.hint_level == 1
    assert action.misconception_id == "MC.FORGET"
    assert action.text == "It looks like only one side changed."
    assert session.last_diagnosis == {"class": "misconception", "detail": "MC.FORGET"}


def test_a_targeted_hint_that_would_leak_falls_back_to_the_authored_hint() -> None:
    item = _item(rules=(("MC.FORGET", ("19",)),))
    learner, session, first = _practice(item)
    session.misconception_text = {"MC.FORGET": "The answer is 5."}
    action = _answer(learner, session, "19", first.item_id)
    assert action.text == "What undoes the operation?"
    assert not leak_check(action.text or "", "5", level=1)


def test_fast_answers_build_a_streak_and_a_slow_one_resets_it() -> None:
    learner, session, first = _practice()
    _answer(learner, session, "99", first.item_id, latency_ms=300)
    _answer(learner, session, "98", first.item_id, latency_ms=300)
    assert session.fast_streak == 2
    _answer(learner, session, "97", first.item_id, latency_ms=20_000)
    assert session.fast_streak == 0


def test_a_missing_latency_never_counts_as_fast() -> None:
    learner, session, first = _practice()
    _answer(learner, session, "99", first.item_id, latency_ms=None)
    assert session.fast_streak == 0


# ---- R32 ----------------------------------------------------------------------------------


def _ask(learner, session, event_type: str = "request_help") -> Action:
    return policy(learner, session, Event(type=event_type, item_id=session.current_item_id))


def _choose(learner, session, choice: str) -> Action:
    return policy(
        learner,
        session,
        Event(type="stuck_choice", response=choice, item_id=session.current_item_id),
    )


def test_help_before_an_answer_asks_where_the_student_is_stuck() -> None:
    learner, session, _ = _practice()
    action = _ask(learner, session)
    assert action.type == "ask_stuck_point"
    assert action.rule_id == "R32"
    assert action.extras["choices"] == ["start", "step", "restate", "might_be_right"]
    assert session.hint_level_shown == 0
    assert session.phase == "stuck"


def test_the_picker_counts_as_the_items_one_bkt_update_and_later_events_do_not_add() -> None:
    learner, session, first = _practice()
    _ask(learner, session)
    assert _bkt_attempts(learner) == 1
    _choose(learner, session, "start")
    _answer(learner, session, "99", first.item_id)
    _answer(learner, session, "5", first.item_id)
    assert _bkt_attempts(learner) == 1


def test_request_hint_is_an_alias_for_request_help() -> None:
    learner, session, _ = _practice()
    action = _ask(learner, session, "request_hint")
    assert action.type == "ask_stuck_point" and action.rule_id == "R32"


def test_i_dont_know_how_to_start_gives_hint_one() -> None:
    learner, session, _ = _practice()
    _ask(learner, session)
    action = _choose(learner, session, "start")
    assert action.type == "hint" and action.hint_level == 1
    assert action.text == "What undoes the operation?"
    assert session.hint_level_shown == 1 and session.phase == "practice"


def test_stuck_at_a_step_shows_the_step_count_then_that_steps_hint() -> None:
    learner, session, _ = _practice()
    _ask(learner, session)
    picked = _choose(learner, session, "step")
    assert picked.type == "ask_stuck_step"
    assert picked.extras["step_count"] == len(STEP_HINTS)
    assert session.phase == "stuck_step"
    hint = policy(
        learner, session, Event(type="stuck_step", response="1", item_id=session.current_item_id)
    )
    assert hint.type == "hint" and hint.text == STEP_HINTS[1]
    assert hint.extras["kind"] == "step" and hint.extras["step"] == 1
    assert session.hint_level_shown == 0  # a step hint is not a ladder level
    assert session.phase == "practice"


def test_a_step_that_does_not_exist_is_refused() -> None:
    learner, session, _ = _practice()
    _ask(learner, session)
    _choose(learner, session, "step")
    action = policy(
        learner, session, Event(type="stuck_step", response="7", item_id=session.current_item_id)
    )
    assert action.rejected and action.guardrail_flag == "bad_step"


def test_a_step_hint_that_would_leak_falls_back_to_hint_one() -> None:
    item = _item(step_hints=("The answer is 5.", "b", "c"))
    learner, session, _ = _practice(item)
    _ask(learner, session)
    _choose(learner, session, "step")
    action = policy(
        learner, session, Event(type="stuck_step", response="0", item_id=session.current_item_id)
    )
    assert action.text == "What undoes the operation?"


def test_i_dont_understand_the_question_restates_it_without_using_a_level() -> None:
    learner, session, _ = _practice()
    _ask(learner, session)
    action = _choose(learner, session, "restate")
    assert action.type == "hint" and action.extras["kind"] == "restate"
    assert action.text == "Let's read it again: what number makes x + 7 = 12 true?"
    assert session.hint_level_shown == 0


def test_my_answer_might_be_right_before_answering_asks_to_submit() -> None:
    learner, session, _ = _practice()
    _ask(learner, session)
    action = _choose(learner, session, "might_be_right")
    assert action.type == "show_item" and action.extras["prompt_submit"] is True
    assert session.phase == "practice"


def test_my_answer_might_be_right_after_a_wrong_answer_rechecks() -> None:
    learner, session, first = _practice()
    _answer(learner, session, "99", first.item_id)  # wrong, hint 1 shown
    session.phase = "stuck"  # the picker was opened from the hint screen
    action = _choose(learner, session, "might_be_right")
    assert action.type == "check_your_work"


def test_help_after_a_wrong_answer_goes_straight_to_the_ladder() -> None:
    learner, session, first = _practice()
    _answer(learner, session, "99", first.item_id)
    action = _ask(learner, session)
    assert action.type == "hint" and action.hint_level == 2


def test_an_item_shown_again_after_it_was_answered_gets_a_fresh_picker() -> None:
    learner, session, first = _practice()
    _ask(learner, session)
    _choose(learner, session, "start")
    _answer(learner, session, "5", first.item_id)  # finished
    assert session.stuck_item_id is None and session.last_wrong_item_id is None
    session.current_item_id = first.item_id  # the same item comes round again
    session.phase = "practice"
    session.hint_level_shown = 0
    assert _ask(learner, session).type == "ask_stuck_point"


def test_the_picker_is_offered_once_per_item() -> None:
    learner, session, _ = _practice()
    _ask(learner, session)
    _choose(learner, session, "restate")
    action = _ask(learner, session)
    assert action.type == "hint" and action.hint_level == 1


def test_help_without_an_attempt_is_counted_and_an_answer_resets_it() -> None:
    learner, session, first = _practice()
    _ask(learner, session)
    assert session.help_without_attempt == 1
    _choose(learner, session, "start")
    _answer(learner, session, "99", first.item_id)
    assert session.help_without_attempt == 0


def test_a_picker_choice_outside_the_picker_is_flagged() -> None:
    learner, session, _ = _practice()
    action = _choose(learner, session, "start")
    assert action.rejected and action.guardrail_flag == "not_in_stuck_picker"


def test_an_unknown_choice_is_flagged_and_keeps_the_picker_open() -> None:
    learner, session, _ = _practice()
    _ask(learner, session)
    action = _choose(learner, session, "tell_me_the_answer")
    assert action.rejected and action.guardrail_flag == "bad_choice"
    assert session.phase == "stuck"


def test_assessments_have_no_picker() -> None:
    session = make_session(catalog_item(pool="diagnostic"), session_type="diagnostic")
    learner = make_learner()
    policy(learner, session, None)
    action = policy(learner, session, Event(type="request_help"))
    assert action.rejected and action.guardrail_flag == "no_hint_in_assessment"


def test_the_reveal_rules_are_unchanged_by_the_picker() -> None:
    learner, session, first = _practice()
    _ask(learner, session)
    _choose(learner, session, "start")  # hint 1
    early = policy(learner, session, Event(type="show_solution"))
    assert early.rejected and early.guardrail_flag == "illegal_reveal"
    _ask(learner, session)  # hint 2 through the ladder
    assert session.hint_level_shown == 2
    reveal = policy(learner, session, Event(type="show_solution"))
    assert reveal.type == "reveal_solution"


def _unused(_: SessionState) -> None:  # keeps the import used for type readers
    return None
