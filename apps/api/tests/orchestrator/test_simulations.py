from __future__ import annotations

import random

from hypothesis import given, settings
from hypothesis import strategies as st

from app.learner.types import LearnerState
from app.orchestrator.policy import policy
from app.orchestrator.replay import verify_replay
from app.orchestrator.types import SOFT_ITEM_CAP, Event
from tests.orchestrator.catalog import seed_catalog, seed_session

PERSONAS = (
    "perfect",
    "always_wrong",
    "random",
    "hint_spam",
    "idle",
    "show_solution_spam",
)


def _correct(session) -> str:
    item = session.item()
    return item.answer_sympy if item else "0"


def _event(persona: str, action, session, rng: random.Random, step: int) -> Event:
    latency = 90_000
    if persona == "idle" and step >= 1:
        return Event(type="idle_nudge", idle_ms=10 * 60 * 1000, latency_ms=latency)
    if action.type == "predict":
        return Event(type="predict_response", text="guess", latency_ms=latency)
    if action.type in {"worked_example", "reveal_solution", "explain_back_prompt", "similar_item"}:
        if action.type == "similar_item":
            return Event(type="answer", response=_next_answer(persona, session, rng), latency_ms=latency)
        return Event(type="continue", latency_ms=latency)
    if persona == "hint_spam":
        return Event(type="request_hint", latency_ms=latency)
    if persona == "show_solution_spam":
        return Event(type="show_solution", latency_ms=latency)
    if action.type in {"show_item", "hint", "feedback", "nudge", "warmup_item", "content_gap"}:
        return Event(
            type="answer",
            response=_next_answer(persona, session, rng),
            item_id=session.current_item_id,
            latency_ms=latency,
        )
    return Event(type="continue", latency_ms=latency)


def _next_answer(persona: str, session, rng: random.Random) -> str:
    if persona == "perfect":
        return _correct(session)
    if persona == "always_wrong":
        return "999"
    if persona == "random":
        return rng.choice(["999", _correct(session), "0", "-1"])
    return "999"


@given(st.sampled_from(PERSONAS), st.integers(min_value=0, max_value=10_000))
@settings(max_examples=12, deadline=None)
def test_scripted_students_on_seed(persona: str, seed: int) -> None:
    catalog = seed_catalog()
    session = seed_session(catalog)
    learner = LearnerState()
    rng = random.Random(seed)
    start_learner = LearnerState()
    start_session = seed_session(catalog)
    events: list[Event] = []
    actions = [policy(learner, session, None)]
    steps = 0
    while actions[-1].type != "end_session" and steps < 80:
        event = _event(persona, actions[-1], session, rng, steps)
        events.append(event)
        actions.append(policy(learner, session, event))
        steps += 1
    assert actions[-1].type == "end_session"
    assert session.items_completed <= SOFT_ITEM_CAP or session.active_ms > 0
    practice_ids = {item.id for item in catalog if item.pool == "practice"}
    for action in actions:
        if action.type in {"show_item", "similar_item", "hint"} and action.item_id:
            item = session.item(action.item_id) or next(
                (row for row in catalog if row.id == action.item_id), None
            )
            if item and session.session_type == "practice":
                assert item.pool != "checkpoint"
                assert item.id in practice_ids or item.pool == "practice"
    reveals_ok = True
    hint2_attempt = False
    shown2 = False
    for event, action in zip(events, actions[1:], strict=False):
        if action.type == "hint" and action.hint_level == 2:
            shown2 = True
        if shown2 and event.type == "answer":
            hint2_attempt = True
        if action.type == "reveal_solution" and not (shown2 and (hint2_attempt or event.type == "show_solution")):
            if event.type == "show_solution" and shown2:
                continue
            if event.type == "answer" and shown2:
                continue
            reveals_ok = action.rejected or shown2
    assert reveals_ok
    memory = session.bkt_memory["bkt_done"]
    assert len(memory) == len(set(memory))
    assert verify_replay(start_learner, start_session, events, actions)
    for gap in session.content_gaps:
        assert "skill" in gap and "tier" in gap and "item_ids_seen" in gap
