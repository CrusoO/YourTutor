"""G2a stretch slot: after level 4 an apply item, after level 5 a transfer item, in a later session.

Spaced like reviews (one day after the level was reached), at most two per session, once per
skill per session, only in practice sessions, and never a content-gap error when no item exists.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from app.learner.ladder import SkillLadder
from app.learner.types import LearnerState, Mastery
from app.orchestrator.policy import policy
from app.orchestrator.types import CatalogItem, Event
from tests.orchestrator.conftest import NOW, catalog_item, make_learner, make_session

PAST = (NOW - timedelta(hours=1)).isoformat()
FUTURE = (NOW + timedelta(hours=1)).isoformat()


def _item(item_id: str, skill: str, role: str, answer: str = "5") -> CatalogItem:
    return replace(catalog_item(item_id, skill=skill, answer=answer), role=role)


def _learner(levels: dict[str, tuple[int, dict[str, str]]]) -> LearnerState:
    learner = make_learner()
    for skill, (level, flags) in levels.items():
        learner.mastery[skill] = Mastery(skill_id=skill, p_known=0.96 if level >= 4 else 0.2)
        learner.ladders[skill] = SkillLadder(
            skill_id=skill, achieved=list(range(1, level + 1)), flags=dict(flags)
        )
    return learner


def _catalog() -> tuple[CatalogItem, ...]:
    items = []
    for n, skill in enumerate(("S1", "S2", "S3", "S4"), start=1):
        items.append(_item(f"P{n}", skill, "procedure"))
        items.append(_item(f"A{n}", skill, "apply"))
        items.append(_item(f"T{n}", skill, "transfer"))
    return tuple(items)


def _session(overlay=("S1", "S2", "S3", "S4"), catalog=None):
    return make_session(*(catalog or _catalog()), overlay=overlay, introduced=set(overlay))


def test_a_due_apply_stretch_comes_before_the_next_new_skill() -> None:
    learner = _learner({"S1": (4, {"stretch_after_4": PAST}), "S2": (0, {})})
    session = _session(("S1", "S2"))
    action = policy(learner, session, None)
    assert action.type == "show_item" and action.skill_id == "S1"
    assert action.item_id == "A1"
    assert session.stretch_served == 1


def test_a_stretch_that_is_not_due_yet_waits() -> None:
    learner = _learner({"S1": (4, {"stretch_after_4": FUTURE}), "S2": (0, {})})
    action = policy(learner, _session(("S1", "S2")), None)
    assert action.skill_id == "S2"


def test_a_level_4_skill_without_a_schedule_is_not_a_stretch() -> None:
    learner = _learner({"S1": (4, {}), "S2": (0, {})})
    action = policy(learner, _session(("S1", "S2")), None)
    assert action.skill_id == "S2"


def test_level_5_gets_a_transfer_item() -> None:
    learner = _learner({"S1": (5, {"stretch_after_5": PAST}), "S2": (0, {})})
    session = _session(("S1", "S2"))
    action = policy(learner, session, None)
    assert action.skill_id == "S1" and action.item_id == "T1"


def test_levels_6_and_7_are_never_stretched() -> None:
    learner = _learner(
        {"S1": (6, {"stretch_after_5": PAST}), "S2": (7, {"stretch_after_5": PAST}), "S3": (0, {})}
    )
    action = policy(learner, _session(("S1", "S2", "S3")), None)
    assert action.skill_id == "S3"


def test_at_most_two_stretch_items_in_a_session() -> None:
    flags = {"stretch_after_4": PAST}
    learner = _learner({"S1": (4, flags), "S2": (4, flags), "S3": (4, flags), "S4": (0, {})})
    session = _session()
    served = []
    action = policy(learner, session, None)
    for _ in range(3):
        served.append(action.item_id)
        action = policy(
            learner,
            session,
            Event(type="answer", response=("5"), item_id=action.item_id, latency_ms=9000),
        )
        while action.type in {"explain_back_prompt"}:
            action = policy(learner, session, Event(type="continue"))
    stretch = [i for i in served if i and i.startswith("A")]
    assert len(stretch) == 2 and session.stretch_served == 2
    assert served[2] == "P4" or not str(served[2]).startswith("A")


def test_a_skill_is_stretched_once_per_session_even_if_the_answer_was_wrong() -> None:
    learner = _learner({"S1": (4, {"stretch_after_4": PAST}), "S2": (0, {})})
    session = _session(("S1", "S2"))
    action = policy(learner, session, None)
    assert action.item_id == "A1"
    action = policy(
        learner, session, Event(type="answer", response="99", item_id="A1", latency_ms=9000)
    )
    for _ in range(4):  # run the help ladder out and move on
        if action.type == "hint":
            action = policy(
                learner, session, Event(type="answer", response="99", item_id="A1", latency_ms=9000)
            )
    assert session.stretch_skills == {"S1"}
    assert session.stretch_served == 1


def test_no_item_for_the_role_means_no_stretch_and_no_content_gap() -> None:
    catalog = tuple(i for i in _catalog() if not (i.skill_ids[0] == "S1" and i.role == "apply"))
    learner = _learner({"S1": (4, {"stretch_after_4": PAST}), "S2": (0, {})})
    session = _session(("S1", "S2"), catalog)
    action = policy(learner, session, None)
    assert action.type == "show_item" and action.skill_id == "S2"
    assert session.content_gaps == []


def test_stretch_only_happens_in_practice_sessions() -> None:
    learner = _learner({"S1": (4, {"stretch_after_4": PAST})})
    session = make_session(*_catalog(), overlay=("S1",), session_type="diagnostic")
    action = policy(learner, session, None)
    assert session.stretch_served == 0
    assert action.type != "show_item" or not (action.item_id or "").startswith("A")


def test_stretch_comes_after_the_warm_up() -> None:
    from tests.orchestrator.conftest import due_card

    learner = _learner({"S1": (4, {"stretch_after_4": PAST}), "S2": (4, {})})
    learner.cards["S2"] = due_card("S2")
    session = _session(("S1", "S2", "S3"))
    first = policy(learner, session, None)
    assert first.type == "warmup_item" and first.skill_id == "S2"
