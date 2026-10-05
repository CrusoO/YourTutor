from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from app.learner.bkt import BktModel, BktParams
from app.learner.scheduler_fsrs import (
    Clock,
    SystemClock,
    rating_from_unhinted_rate,
    rating_from_warmup,
    review,
)
from app.learner.types import LearnerEvent, LearnerState, Mastery


class MasteryModel(Protocol):
    def update(self, p_known: float, *, correct: bool, params: BktParams) -> float: ...


def _mastery(state: LearnerState, skill_id: str, params: BktParams) -> Mastery:
    row = state.mastery.get(skill_id)
    if row is None:
        row = Mastery(skill_id=skill_id, p_known=params.p_init)
        state.mastery[skill_id] = row
    return row


def apply_events(
    events: list[LearnerEvent],
    params_by_skill: dict[str, BktParams],
    *,
    clock: Clock | None = None,
    model: MasteryModel | None = None,
) -> LearnerState:
    clock = clock or SystemClock()
    model = model or BktModel()
    state = LearnerState()
    _apply(state, events, params_by_skill, clock=clock, model=model)
    return state


def apply_event(
    state: LearnerState,
    event: LearnerEvent,
    params_by_skill: dict[str, BktParams],
    *,
    clock: Clock | None = None,
    model: MasteryModel | None = None,
    memory: dict | None = None,
) -> LearnerState:
    """Incremental update. `memory` holds per-item flags across calls."""
    clock = clock or SystemClock()
    model = model or BktModel()
    mem = (
        memory
        if memory is not None
        else {
            "bkt_done": set(),
            "hinted": set(),
            "first_wrong": set(),
            "session_unhinted": defaultdict(lambda: defaultdict(lambda: [0, 0])),
            "warmup_skills": set(),
        }
    )
    _apply_one(state, event, params_by_skill, clock, model, mem)
    return state


def recompute_from_log(
    events: list[LearnerEvent],
    params_by_skill: dict[str, BktParams],
    *,
    clock: Clock | None = None,
    model: MasteryModel | None = None,
) -> LearnerState:
    """Idempotent: the same log always yields the same state."""
    return apply_events(events, params_by_skill, clock=clock, model=model)


def _apply(
    state: LearnerState,
    events: list[LearnerEvent],
    params_by_skill: dict[str, BktParams],
    *,
    clock: Clock,
    model: MasteryModel,
) -> None:
    memory: dict = {
        "bkt_done": set(),
        "hinted": set(),
        "first_wrong": set(),
        "session_unhinted": defaultdict(lambda: defaultdict(lambda: [0, 0])),
        "warmup_skills": set(),
    }
    for event in events:
        _apply_one(state, event, params_by_skill, clock, model, memory)


def _apply_one(
    state: LearnerState,
    event: LearnerEvent,
    params_by_skill: dict[str, BktParams],
    clock: Clock,
    model: MasteryModel,
    memory: dict,
) -> None:
    if event.event_type == "explain_back" or event.pool == "checkpoint":
        return
    if event.event_type == "session_end":
        _session_end_fsrs(state, event.session_id, memory, clock)
        return
    params = params_by_skill[event.skill_id]
    mastery = _mastery(state, event.skill_id, params)
    bkt_done: set[str] = memory["bkt_done"]
    hinted: set[str] = memory["hinted"]
    first_wrong: set[str] = memory["first_wrong"]

    if event.event_type == "request_hint":
        hinted.add(event.item_id)
        if event.item_id not in bkt_done:
            mastery.p_known = model.update(mastery.p_known, correct=False, params=params)
            mastery.attempts += 1
            bkt_done.add(event.item_id)
        return

    if event.event_type != "answer":
        return

    first = event.item_id not in bkt_done
    was_hinted = event.item_id in hinted
    if first:
        mastery.p_known = model.update(mastery.p_known, correct=bool(event.correct), params=params)
        mastery.attempts += 1
        bkt_done.add(event.item_id)
        if event.correct and not was_hinted:
            mastery.unhinted_correct += 1
        if not event.correct:
            first_wrong.add(event.item_id)
    elif event.correct and (was_hinted or event.item_id in first_wrong):
        mastery.hinted_correct += 1

    warmup = event.is_warmup or event.pool == "warmup"
    if warmup:
        memory["warmup_skills"].add((event.session_id, event.skill_id))
        state.cards[event.skill_id] = review(
            state.cards.get(event.skill_id),
            skill_id=event.skill_id,
            rating=rating_from_warmup(
                correct=bool(event.correct),
                hinted=was_hinted,
                latency_ms=event.latency_ms,
            ),
            now=clock.now(),
        )
        return
    if event.pool == "practice" and first and not was_hinted:
        pair = memory["session_unhinted"][event.session_id][event.skill_id]
        pair[1] += 1
        if event.correct:
            pair[0] += 1


def _session_end_fsrs(state: LearnerState, session_id: str, memory: dict, clock: Clock) -> None:
    per_skill = memory["session_unhinted"].get(session_id, {})
    for skill_id, (correct, total) in per_skill.items():
        if (session_id, skill_id) in memory["warmup_skills"]:
            continue
        rate = (correct / total) if total else 0.0
        state.cards[skill_id] = review(
            state.cards.get(skill_id),
            skill_id=skill_id,
            rating=rating_from_unhinted_rate(rate),
            now=clock.now(),
        )
