"""G2b: R35 break_or_switch, R36 frustration, R37 challenge, R40 never end on a failure, praise."""

from __future__ import annotations

from dataclasses import replace

from app.content.validator import item_tier
from app.learner.ladder import SkillLadder
from app.learner.types import LearnerState, Mastery
from app.orchestrator.policy import policy
from app.orchestrator.types import Action, CatalogItem, Event, SessionState
from tests.orchestrator.conftest import catalog_item, make_learner, make_session

S1, S2 = "S1", "S2"


def _items(
    skill: str, tier_difficulty: dict[str, float], per_tier: int = 6, role="procedure", offset=0
):
    out = []
    for tier, difficulty in tier_difficulty.items():
        for n in range(offset, offset + per_tier):
            item_id = f"{skill}.{tier}.{n}"
            out.append(
                replace(
                    catalog_item(item_id, skill=skill, answer=str(30 + n), difficulty=difficulty),
                    role=role,
                    min_plausible_ms=3000,
                )
            )
    return out


TIERS = {"easy": 0.2, "medium": 0.6, "hard": 0.9}


def _catalog(skills=(S1,)) -> tuple[CatalogItem, ...]:
    items: list[CatalogItem] = []
    for skill in skills:
        items.extend(_items(skill, TIERS))
        items.extend(_items(skill, {"hard": 0.9}, per_tier=2, role="transfer", offset=20))
    return tuple(items)


def _learner(p_known: float = 0.5, skills=(S1,)) -> LearnerState:
    learner = make_learner()
    for skill in skills:
        learner.mastery[skill] = Mastery(skill_id=skill, p_known=p_known)
    return learner


def _session(skills=(S1,), **fields) -> SessionState:
    session = make_session(*_catalog(skills), overlay=skills, introduced=set(skills))
    for key, value in fields.items():
        setattr(session, key, value)
    return session


def _answer_of(item_id: str | None) -> str:
    return str(30 + int((item_id or "x.y.0").split(".")[2]))


def _right(learner, session, action: Action, latency: int = 9000) -> Action:
    return policy(
        learner,
        session,
        Event(
            type="answer",
            response=_answer_of(action.item_id),
            item_id=action.item_id,
            latency_ms=latency,
        ),
    )


def _wrong(learner, session, action: Action, latency: int = 9000) -> Action:
    return policy(
        learner,
        session,
        Event(type="answer", response="-1", item_id=action.item_id, latency_ms=latency),
    )


def _skip_explain(learner, session, action: Action) -> Action:
    while action.type in {"explain_back_prompt", "explain_back_result"}:
        action = policy(learner, session, Event(type="continue"))
    return action


def _reveal_item(learner, session, action: Action) -> Action:
    """Fail an item all the way to the reveal, then continue to the next item."""
    action = _wrong(learner, session, action)
    for _ in range(4):
        if action.type == "hint":
            action = _wrong(learner, session, action)
    assert action.type == "reveal_solution", action.type
    return policy(learner, session, Event(type="continue"))


def _tier(session: SessionState, action: Action) -> str:
    item = session.item(action.item_id)
    assert item is not None
    return item_tier(item.difficulty)


# ---- R35 break_or_switch ------------------------------------------------------------------


def _fast_answers(learner, session, action: Action, count: int, *, right: bool) -> Action:
    """Exactly `count` fast answers (300 ms), clicking through Continue-only screens between."""
    given = 0
    for _ in range(40):
        if given == count or action.type == "break_or_switch":
            break
        if action.type in {"show_item", "similar_item", "hint", "check_your_work"}:
            action = (_right if right else _wrong)(learner, session, action, latency=300)
            given += 1
        else:
            action = policy(learner, session, Event(type="continue"))
    return action


def test_three_fast_answers_in_a_row_offer_a_break_or_a_switch() -> None:
    for right in (True, False):
        learner, session = _learner(), _session()
        action = policy(learner, session, None)
        action = _fast_answers(learner, session, action, 2, right=right)
        assert action.type != "break_or_switch" and session.fast_streak == 2
        action = _fast_answers(learner, session, action, 1, right=right)
        assert action.type == "break_or_switch", right
        assert action.rule_id == "R35"
        assert action.extras["choices"] == ["break", "switch", "continue"]
        assert session.fast_streak == 0 and session.phase == "break_choice"


def test_a_slow_answer_resets_the_fast_streak() -> None:
    learner, session = _learner(), _session()
    action = policy(learner, session, None)
    for latency in (300, 300, 20_000, 300, 300):
        action = _skip_explain(learner, session, _right(learner, session, action, latency=latency))
        assert action.type != "break_or_switch"


def test_help_without_an_attempt_three_times_offers_a_break() -> None:
    learner, session = _learner(), _session()
    policy(learner, session, None)
    for _ in range(2):
        picker = policy(learner, session, Event(type="request_help"))
        assert picker.type == "ask_stuck_point"
        policy(learner, session, Event(type="stuck_choice", response="start"))
        policy(learner, session, Event(type="request_help"))
        revealed = policy(learner, session, Event(type="show_solution"))
        assert revealed.type == "reveal_solution"
        policy(learner, session, Event(type="continue"))
    third = policy(learner, session, Event(type="request_help"))
    assert third.type == "break_or_switch" and third.rule_id == "R35"


def test_choosing_a_break_ends_the_session_so_it_can_be_resumed() -> None:
    learner, session = _learner(), _session()
    action = policy(learner, session, None)
    for _ in range(3):
        action = _skip_explain(learner, session, _right(learner, session, action, latency=300))
        if action.type == "break_or_switch":
            break
    ended = policy(learner, session, Event(type="break_choice", response="break"))
    assert ended.type == "end_session" and ended.ended_reason == "break" and ended.resumable


def test_choosing_to_continue_returns_to_the_same_item() -> None:
    learner, session = _learner(), _session()
    action = policy(learner, session, None)
    for _ in range(3):
        action = _skip_explain(learner, session, _right(learner, session, action, latency=300))
        if action.type == "break_or_switch":
            break
    item_before = session.current_item_id
    back = policy(learner, session, Event(type="break_choice", response="continue"))
    assert back.type == "show_item" and back.item_id == item_before
    assert session.phase == "practice"


def test_choosing_switch_moves_to_a_different_skill_when_there_is_one() -> None:
    skills = (S1, S2)
    learner, session = _learner(skills=skills), _session(skills)
    action = policy(learner, session, None)
    first_skill = action.skill_id
    for _ in range(3):
        action = _skip_explain(learner, session, _right(learner, session, action, latency=300))
        if action.type == "break_or_switch":
            break
    switched = policy(learner, session, Event(type="break_choice", response="switch"))
    assert switched.type == "show_item" and switched.skill_id != first_skill


def test_a_break_choice_outside_the_offer_is_flagged() -> None:
    learner, session = _learner(), _session()
    policy(learner, session, None)
    action = policy(learner, session, Event(type="break_choice", response="break"))
    assert action.rejected and action.guardrail_flag == "not_in_break_choice"


# ---- R36 frustration ----------------------------------------------------------------------


def test_two_reveals_step_the_tier_down_for_the_next_two_items() -> None:
    learner, session = _learner(p_known=0.6), _session()
    action = policy(learner, session, None)
    assert _tier(session, action) == "medium"
    action = _reveal_item(learner, session, action)
    action = _reveal_item(learner, session, action)
    tiers = []
    for _ in range(3):
        tiers.append(_tier(session, action))
        action = _skip_explain(learner, session, _right(learner, session, action))
    assert tiers[:2] == ["easy", "easy"]
    assert tiers[2] != "easy"  # back to the tier the student's knowledge calls for


def test_only_the_first_easier_item_carries_a_short_acknowledgement() -> None:
    learner, session = _learner(p_known=0.6), _session()
    action = policy(learner, session, None)
    action = _reveal_item(learner, session, action)
    action = _reveal_item(learner, session, action)
    assert action.extras.get("support") == "step_down"
    action = _skip_explain(learner, session, _right(learner, session, action))
    assert action.extras.get("support") is None  # the second easier item has no extra message


def test_three_wrong_first_attempts_in_a_row_across_skills_also_step_down() -> None:
    learner, session = _learner(p_known=0.6), _session()
    action = policy(learner, session, None)
    session.wrong_run = 2  # two misses on other skills just before this one
    session.wrong_first_streak = {"OTHER": 2}
    _wrong(learner, session, action)
    assert session.tier_down_items == 2 and session.wrong_run == 0


def _reveal_rest(learner, session, action: Action) -> Action:
    for _ in range(4):
        if action.type == "hint":
            action = _wrong(learner, session, action)
    if action.type == "reveal_solution":
        action = policy(learner, session, Event(type="continue"))
    return action


def test_the_step_down_ends_after_two_items() -> None:
    learner, session = _learner(p_known=0.6), _session()
    action = policy(learner, session, None)
    action = _reveal_item(learner, session, action)
    action = _reveal_item(learner, session, action)
    assert session.tier_down_items == 1  # the first of the two easier items is already on screen
    action = _skip_explain(learner, session, _right(learner, session, action))
    assert session.tier_down_items == 0
    assert _tier(session, action) != "easy" or session.tier_down_items == 0


# ---- R37 challenge ------------------------------------------------------------------------


def test_three_unhinted_correct_first_attempts_step_the_tier_up() -> None:
    learner, session = _learner(p_known=0.3), _session()
    action = policy(learner, session, None)
    assert _tier(session, action) == "easy"
    for _ in range(3):
        action = _skip_explain(learner, session, _right(learner, session, action))
    ranks = {"easy": 0, "medium": 1, "hard": 2}
    from_knowledge = item_tier(learner.mastery[S1].p_known)
    assert session.unhinted_run == 0
    assert ranks[_tier(session, action)] == min(2, ranks[from_knowledge] + 1)


def test_at_the_hard_tier_three_correct_in_a_row_serve_a_transfer_challenge() -> None:
    learner, session = _learner(p_known=0.9), _session()
    action = policy(learner, session, None)
    assert _tier(session, action) == "hard"
    for _ in range(3):
        action = _skip_explain(learner, session, _right(learner, session, action))
    assert action.type == "show_item" and action.extras.get("challenge") is True
    item = session.item(action.item_id)
    assert item is not None and item.role == "transfer"


def test_a_hinted_correct_answer_breaks_the_run() -> None:
    learner, session = _learner(p_known=0.9), _session()
    action = policy(learner, session, None)
    action = _skip_explain(learner, session, _right(learner, session, action))
    policy(learner, session, Event(type="request_help"))
    policy(learner, session, Event(type="stuck_choice", response="start"))
    action = _skip_explain(learner, session, _right(learner, session, action))
    assert session.unhinted_run == 0


# ---- R40 never end on a failure ----------------------------------------------------------


def test_a_cap_after_a_wrong_answer_serves_one_likely_success_item_first() -> None:
    learner, session = _learner(p_known=0.6), _session()
    action = policy(learner, session, None)
    session.items_completed = session.soft_item_cap  # the cap is reached ...
    action = _reveal_item(learner, session, action)  # ... right after a failure
    assert action.type != "end_session"
    assert action.extras.get("win") is True
    assert _tier(session, action) == "easy"
    done = _right(learner, session, action)
    done = _skip_explain(learner, session, done)
    assert done.type == "end_session"


def test_the_win_item_is_served_once_even_if_it_is_also_failed() -> None:
    learner, session = _learner(p_known=0.6), _session()
    action = policy(learner, session, None)
    session.items_completed = session.soft_item_cap
    action = _reveal_item(learner, session, action)
    assert action.extras.get("win") is True
    ended = _wrong(learner, session, action)
    for _ in range(4):
        if ended.type in {"hint", "reveal_solution"}:
            ended = (
                policy(learner, session, Event(type="continue"))
                if ended.type == "reveal_solution"
                else _wrong(learner, session, ended)
            )
    assert ended.type == "end_session"


def test_a_cap_after_a_success_ends_without_an_extra_item() -> None:
    learner, session = _learner(p_known=0.6), _session()
    action = policy(learner, session, None)
    session.items_completed = session.soft_item_cap - 1
    done = _skip_explain(learner, session, _right(learner, session, action))
    assert done.type == "end_session" and done.ended_reason == "soft_cap"


def test_the_hard_cap_adds_at_most_one_item_after_a_failure() -> None:
    learner, session = _learner(p_known=0.6), _session()
    action = policy(learner, session, None)
    session.active_ms = session.hard_active_ms
    action = _wrong(learner, session, action)
    served = 0
    for _ in range(8):
        if action.type == "end_session":
            break
        if action.extras.get("win"):
            served += 1
            action = _right(learner, session, action)
        elif action.type == "hint":
            action = _wrong(learner, session, action)
        elif action.type == "reveal_solution":
            action = policy(learner, session, Event(type="continue"))
        else:
            action = _skip_explain(learner, session, action)
    assert action.type == "end_session" and served <= 1


def test_consent_revoked_still_ends_immediately_after_a_failure() -> None:
    learner, session = _learner(), _session()
    action = policy(learner, session, None)
    _wrong(learner, session, action)
    ended = policy(learner, session, Event(type="consent_revoked"))
    assert ended.type == "end_session" and ended.ended_reason == "consent_revoked"


# ---- praise triggers ---------------------------------------------------------------------


def _praise(action: Action) -> dict | None:
    return action.extras.get("encouragement")


def test_a_hard_tier_success_earns_strategy_encouragement() -> None:
    learner, session = _learner(p_known=0.9), _session()
    action = policy(learner, session, None)
    done = _right(learner, session, action)
    praise = _praise(done)
    assert praise is not None and praise["trigger"] == "hard_success"


def test_no_encouragement_after_easy_or_medium_items() -> None:
    for p_known in (0.2, 0.6):
        learner, session = _learner(p_known=p_known), _session()
        action = policy(learner, session, None)
        assert _praise(_right(learner, session, action)) is None


def test_a_hinted_hard_success_is_not_praised() -> None:
    learner, session = _learner(p_known=0.9), _session()
    action = policy(learner, session, None)
    policy(learner, session, Event(type="request_help"))
    policy(learner, session, Event(type="stuck_choice", response="start"))
    assert _praise(_right(learner, session, action)) is None


def test_recovery_after_a_failure_on_the_same_skill_is_praised_on_a_non_easy_item() -> None:
    learner, session = _learner(p_known=0.6), _session()
    action = policy(learner, session, None)
    assert _tier(session, action) == "medium"
    session.skill_failed = {S1}  # an earlier miss on this skill
    praise = _praise(_right(learner, session, action))
    assert praise is not None and praise["trigger"] == "recovery"
    assert S1 not in session.skill_failed


def test_recovery_on_an_easy_item_is_not_praised() -> None:
    learner, session = _learner(p_known=0.2), _session()
    action = policy(learner, session, None)
    assert _tier(session, action) == "easy"
    session.skill_failed = {S1}
    assert _praise(_right(learner, session, action)) is None
    assert S1 not in session.skill_failed  # recovered, quietly


def test_encouragement_is_not_repeated_on_consecutive_items() -> None:
    learner, session = _learner(p_known=0.9), _session()
    action = policy(learner, session, None)
    first = _right(learner, session, action)
    assert _praise(first) is not None
    second = _right(learner, session, _skip_explain(learner, session, first))
    assert _praise(second) is None


def test_the_session_end_gets_encouragement_when_it_does_not_follow_a_failure() -> None:
    learner, session = _learner(p_known=0.6), _session()
    action = policy(learner, session, None)
    session.items_completed = session.soft_item_cap - 1
    done = _skip_explain(learner, session, _right(learner, session, action))
    assert done.type == "end_session"
    praise = _praise(done)
    assert praise is not None and praise["trigger"] == "session_end"


def _unused(_: Mastery | SkillLadder) -> None:
    return None
