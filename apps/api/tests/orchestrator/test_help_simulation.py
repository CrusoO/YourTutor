"""G2a hypothesis simulations: help escalation is monotonic and the v1 reveal rules hold.

Random event sequences (valid and nonsense) drive the real policy. After every step:
  * hint levels on one item never go down
  * no reveal before hint level 2 has been shown
  * no hint text shown before the reveal contains the answer
  * the stuck-point picker is offered at most once per item
  * BKT never updates more than once per item
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.learner.ladder import SkillLadder
from app.orchestrator.policy import policy
from app.orchestrator.types import Event
from app.verifier.check import leak_check
from tests.orchestrator.conftest import catalog_item, make_learner, make_session

SKILL = "MATH.S1"
ANSWERS = {"ITEM.H1": "5", "ITEM.H2": "8", "ITEM.H3": "3"}

EVENTS = st.sampled_from(
    [
        "request_help",
        "request_hint",
        "stuck_start",
        "stuck_step",
        "stuck_restate",
        "stuck_might",
        "stuck_nonsense",
        "step_0",
        "step_2",
        "step_9",
        "right",
        "wrong",
        "slip",
        "fast_wrong",
        "show_solution",
        "continue",
        "predict",
        "explain",
        "nudge",
    ]
)


def _catalog():
    items = []
    for item_id, answer in ANSWERS.items():
        base = catalog_item(item_id, answer=answer)
        items.append(
            replace(
                base,
                slip_patterns=({"kind": "sign_flip"}, {"kind": "off_by", "max_distance": 1}),
                step_hints=("First, undo the plus.", "Then undo the times.", "Check it."),
                hint_restate="Read the question again: what makes the sentence true?",
                min_plausible_ms=3000,
                solution_steps=("Subtract.", "Divide.", f"x = {answer}"),
            )
        )
    return tuple(items)


def _event(name: str, action_item: str | None, session) -> Event:
    item_id = action_item or session.current_item_id
    answer = ANSWERS.get(item_id or "", "5")
    table: dict[str, tuple[str, str | None, int | None]] = {
        "request_help": ("request_help", None, None),
        "request_hint": ("request_hint", None, None),
        "stuck_start": ("stuck_choice", "start", None),
        "stuck_step": ("stuck_choice", "step", None),
        "stuck_restate": ("stuck_choice", "restate", None),
        "stuck_might": ("stuck_choice", "might_be_right", None),
        "stuck_nonsense": ("stuck_choice", "reveal_it", None),
        "step_0": ("stuck_step", "0", None),
        "step_2": ("stuck_step", "2", None),
        "step_9": ("stuck_step", "9", None),
        "right": ("answer", answer, 9000),
        "wrong": ("answer", "999", 9000),
        "slip": ("answer", f"-{answer}", 9000),
        "fast_wrong": ("answer", "998", 100),
        "show_solution": ("show_solution", None, None),
        "continue": ("continue", None, None),
        "predict": ("predict_response", "yes", None),
        "explain": ("explain_back", "because", None),
        "nudge": ("idle_nudge", None, None),
    }
    kind, response, latency = table[name]
    return Event(type=kind, response=response, item_id=item_id, latency_ms=latency, text=response)


# Flow-control events are only ever sent by the client on the screen they belong to; every help,
# answer and reveal event stays random so illegal help sequences are still exercised.
_FLOW_ACTIONS = {
    "predict": {"predict"},
    "explain": {"explain_back_prompt"},
    "continue": {
        "worked_example",
        "reveal_solution",
        "explain_back_prompt",
        "explain_back_result",
        "feedback",
        "nudge",
        "content_gap",
    },
}


def _legal(name: str, action_type: str) -> bool:
    allowed = _FLOW_ACTIONS.get(name)
    return allowed is None or action_type in allowed


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(names=st.lists(EVENTS, min_size=1, max_size=45), level=st.sampled_from([0, 4]))
def test_help_is_monotonic_and_the_reveal_rules_hold(names: list[str], level: int) -> None:
    session = make_session(*_catalog(), introduced={SKILL})
    learner = make_learner()
    action = policy(learner, session, None)
    if level:
        learner.ladders[SKILL] = SkillLadder(skill_id=SKILL, achieved=[1, 2, 3, 4])
    levels_seen: dict[str, int] = {}
    pickers: dict[str, int] = {}
    shown_items: set[str] = set()
    for name in names:
        if action.type == "end_session":
            break
        if not _legal(name, action.type):
            continue
        item_id = action.item_id or session.current_item_id
        if item_id:
            shown_items.add(item_id)
        event = _event(name, item_id, session)
        phase_before = session.phase
        answered_item = item_id
        action = policy(learner, session, event)
        if session.last_correct and answered_item:
            levels_seen.pop(answered_item, None)  # finished: a repeat is a new presentation
            pickers.pop(answered_item, None)
        item_id = action.item_id or session.current_item_id
        if item_id:
            shown_items.add(item_id)
            previous = levels_seen.get(item_id, 0)
            assert session.hint_level_shown >= previous or session.current_item_id != item_id, (
                name,
                previous,
                session.hint_level_shown,
            )
            if session.current_item_id == item_id:
                levels_seen[item_id] = max(previous, session.hint_level_shown)
        if action.type == "reveal_solution":
            assert session.hint_level_shown >= 2
        if action.type == "hint":
            assert action.hint_level != 3
            answer = ANSWERS.get(action.item_id or "", "5")
            assert not leak_check(action.text or "", answer, level=1), action.text
        if action.type == "ask_stuck_point" and phase_before not in {"stuck", "stuck_step"}:
            key = action.item_id or ""  # entering the picker; re-showing it is not a new offer
            pickers[key] = pickers.get(key, 0) + 1
            assert pickers[key] == 1, key
    attempts = learner.mastery[SKILL].attempts if SKILL in learner.mastery else 0
    assert attempts <= max(1, len(shown_items))


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(names=st.lists(EVENTS, min_size=1, max_size=40))
def test_bkt_updates_once_per_item_whatever_the_help_path(names: list[str]) -> None:
    session = make_session(*_catalog(), introduced={SKILL})
    learner = make_learner()
    action = policy(learner, session, None)
    per_item_updates: dict[str, int] = {}
    last_attempts = 0
    for name in names:
        if action.type == "end_session":
            break
        if not _legal(name, action.type):
            continue
        item_id = action.item_id or session.current_item_id
        event = _event(name, item_id, session)
        action = policy(learner, session, event)
        attempts = learner.mastery[SKILL].attempts if SKILL in learner.mastery else 0
        if attempts > last_attempts:
            assert attempts == last_attempts + 1
            key = item_id or ""
            per_item_updates[key] = per_item_updates.get(key, 0) + 1
            assert per_item_updates[key] == 1, (key, name)
        last_attempts = attempts


def test_the_picker_never_appears_after_a_wrong_answer_on_the_same_item() -> None:
    session = make_session(*_catalog(), introduced={SKILL})
    learner = make_learner()
    first = policy(learner, session, None)
    policy(learner, session, _event("wrong", first.item_id, session))
    action = policy(learner, session, _event("request_help", first.item_id, session))
    assert action.type != "ask_stuck_point"


def _unused(_: Any) -> None:
    return None
