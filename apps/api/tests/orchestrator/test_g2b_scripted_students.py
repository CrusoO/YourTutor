"""G2b acceptance: scripted students (hypothesis) against the real policy.

Guesser -> break_or_switch; strong student -> challenge or a higher tier; prerequisite-gap student
-> a probe within 3 failures; wheel-spinning caught by item 10 for every simulated non-learner;
teacher alerts only with teacher_share; no session ends right after a failure within the caps.
"""

from __future__ import annotations

import random

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.content.validator import item_tier
from app.learner.ladder import SkillLadder
from app.learner.types import LearnerState, Mastery
from app.orchestrator.policy import policy
from app.orchestrator.types import Action, Event, SessionState
from tests.orchestrator.conftest import make_learner, make_session
from tests.orchestrator.test_probe_wheel import P, T
from tests.orchestrator.test_probe_wheel import _catalog as probe_catalog
from tests.orchestrator.test_probe_wheel import _learner as probe_learner
from tests.orchestrator.test_rules_r35_r40 import S1, _answer_of, _catalog

SETTINGS = settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
RANK = {"easy": 0, "medium": 1, "hard": 2}


def _learner(p_known: float) -> LearnerState:
    learner = make_learner()
    learner.mastery[S1] = Mastery(skill_id=S1, p_known=p_known)
    return learner


def _session(**fields) -> SessionState:
    session = make_session(*_catalog(), overlay=(S1,), introduced={S1})
    for key, value in fields.items():
        setattr(session, key, value)
    return session


def _answer(learner, session, action: Action, correct: bool, latency: int) -> Action:
    response = _answer_of(action.item_id) if correct else "-1"
    return policy(
        learner,
        session,
        Event(type="answer", response=response, item_id=action.item_id, latency_ms=latency),
    )


def _settle(learner, session, action: Action) -> Action:
    """Click through screens that only need Continue."""
    for _ in range(4):
        if action.type in {"explain_back_prompt", "explain_back_result", "reveal_solution"}:
            action = policy(learner, session, Event(type="continue"))
    return action


# ---- guesser ------------------------------------------------------------------------------


@SETTINGS
@given(
    latencies=st.lists(st.integers(50, 2500), min_size=3, max_size=8),
    rights=st.lists(st.booleans(), min_size=8, max_size=8),
)
def test_a_guesser_is_offered_a_break_or_switch_within_a_few_answers(latencies, rights) -> None:
    learner, session = _learner(0.3), _session()
    action = policy(learner, session, None)
    given = 0
    for _ in range(60):
        if action.type == "break_or_switch" or given == len(latencies):
            break
        if action.type in {"show_item", "similar_item", "hint", "check_your_work"}:
            action = _answer(learner, session, action, rights[given], latencies[given])
            given += 1
        else:
            action = _settle(learner, session, action)
    # three fast answers are enough, whatever the answers were
    assert action.type == "break_or_switch" or session.phase == "break_choice"


# ---- strong student -----------------------------------------------------------------------


@SETTINGS
@given(p_known=st.sampled_from([0.1, 0.5, 0.9]), latency=st.integers(4000, 20000))
def test_a_strong_student_meets_a_higher_tier_or_a_challenge(p_known, latency) -> None:
    learner, session = _learner(p_known), _session()
    action = policy(learner, session, None)
    first_rank = RANK[item_tier(session.item(action.item_id).difficulty)]  # type: ignore[union-attr]
    best = first_rank
    challenged = False
    for _ in range(10):
        if action.type in {"show_item", "similar_item"}:
            item = session.item(action.item_id)
            assert item is not None
            best = max(best, RANK[item_tier(item.difficulty)])
            challenged = challenged or bool(action.extras.get("challenge"))
            action = _answer(learner, session, action, True, latency)
        else:
            action = _settle(learner, session, action)
        if action.type == "end_session":
            break
    assert challenged or best > first_rank or first_rank == 2


# ---- prerequisite gap ---------------------------------------------------------------------


def _prereq_catalog():
    from dataclasses import replace

    return tuple(
        replace(i, misconception_rules=(("MC.PRE", ("-2",)),)) if i.id.startswith("S1.") else i
        for i in probe_catalog()
    )


@SETTINGS
@given(attempts=st.integers(1, 3))
def test_a_prerequisite_gap_student_is_probed_within_three_failures(attempts) -> None:
    from tests.orchestrator.test_probe_wheel import _session as probe_session

    learner, session = probe_learner(), probe_session(_prereq_catalog())
    action = policy(learner, session, None)
    failures = 0
    for _ in range(attempts):
        if action.type == "show_item" and action.extras.get("probe"):
            break
        failures += 1  # the student's wrong answers all look like a gap in the prerequisite
        action = policy(
            learner,
            session,
            Event(type="answer", response="-2", item_id=action.item_id, latency_ms=9000),
        )
    assert action.type == "show_item" and action.extras.get("probe") is True
    assert failures <= 3 and session.probe_for == T and session.probe_skill == P


@SETTINGS
@given(wrong=st.sampled_from(["-1", "999", "0", "17"]))
def test_a_student_who_misses_three_items_in_a_row_is_probed_without_any_signature(wrong) -> None:
    from tests.orchestrator.test_probe_wheel import _session as probe_session

    learner, session = probe_learner(), probe_session(probe_catalog())
    action = policy(learner, session, None)
    missed_items: set[str] = set()
    for _ in range(40):
        if action.type == "show_item" and action.extras.get("probe"):
            break
        if action.type in {"show_item", "similar_item", "hint", "check_your_work"}:
            missed_items.add(str(action.item_id))
            action = policy(
                learner,
                session,
                Event(type="answer", response=wrong, item_id=action.item_id, latency_ms=9000),
            )
        else:
            action = _settle(learner, session, action)
    assert action.extras.get("probe") is True
    assert len(missed_items) <= 3  # three missed first attempts, then the probe


# ---- wheel spinning -----------------------------------------------------------------------


@SETTINGS
@given(seed=st.integers(0, 10_000), p_correct=st.floats(0.0, 0.25))
def test_wheel_spinning_is_caught_by_item_ten_for_every_non_learner(seed, p_correct) -> None:
    rng = random.Random(seed)
    learner, session = _learner(0.2), _session()
    action = policy(learner, session, None)
    for _ in range(300):
        if action.type == "end_session":
            break
        if S1 in session.wheel_skills:
            break
        # the invariant: ten items without level 4 always means the skill is flagged
        assert not (session.skill_items.get(S1, 0) >= 10 and S1 not in session.wheel_skills)
        if action.type in {"show_item", "similar_item", "hint", "check_your_work"}:
            action = _answer(learner, session, action, rng.random() < p_correct, 9000)
        else:
            action = _settle(learner, session, action)
            if action.type in {"worked_example", "break_or_switch"}:
                action = policy(
                    learner,
                    session,
                    Event(type="break_choice", response="continue")
                    if action.type == "break_or_switch"
                    else Event(type="continue"),
                )
    assert S1 in session.wheel_skills or session.skill_items.get(S1, 0) < 10
    if session.skill_items.get(S1, 0) >= 10:
        assert S1 in session.wheel_skills


@SETTINGS
@given(share=st.booleans(), seed=st.integers(0, 1000))
def test_alerts_exist_only_with_teacher_share(share, seed) -> None:
    rng = random.Random(seed)
    learner, session = _learner(0.2), _session(teacher_share=share)
    action = policy(learner, session, None)
    for _ in range(120):
        if action.type == "end_session" or session.wheel_skills:
            break
        if action.type in {"show_item", "similar_item", "hint", "check_your_work"}:
            action = _answer(learner, session, action, rng.random() < 0.1, 9000)
        else:
            action = _settle(learner, session, action)
            if action.type == "break_or_switch":
                action = policy(learner, session, Event(type="break_choice", response="continue"))
    assert bool(session.alerts) == (share and bool(session.wheel_skills))


# ---- never end right after a failure ------------------------------------------------------


@SETTINGS
@given(
    soft=st.integers(2, 6),
    pattern=st.lists(st.booleans(), min_size=4, max_size=30),
    latency=st.integers(4000, 15000),
)
def test_no_cap_ends_a_session_straight_after_a_failure(soft, pattern, latency) -> None:
    learner, session = _learner(0.3), _session(soft_item_cap=soft)
    action = policy(learner, session, None)
    index = 0
    for _ in range(80):
        if action.type == "end_session":
            break
        if action.type in {"show_item", "similar_item", "hint", "check_your_work"}:
            correct = pattern[index % len(pattern)]
            index += 1
            action = _answer(learner, session, action, correct, latency)
        elif action.type == "break_or_switch":
            action = policy(learner, session, Event(type="break_choice", response="continue"))
        else:
            action = _settle(learner, session, action)
            if action.type == "worked_example":
                action = policy(learner, session, Event(type="continue"))
    if action.type == "end_session" and action.ended_reason in {"soft_cap", "hard_cap"}:
        assert not session.last_failure or session.win_served, (
            session.last_failure,
            session.win_served,
        )


def _unused(_: SkillLadder) -> None:
    return None
