"""G2b: R33 prerequisite probe and R34 wheel-spinning stop (with teacher alerts)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.learner.ladder import SkillLadder
from app.learner.types import LearnerState, Mastery
from app.orchestrator.policy import policy
from app.orchestrator.types import Action, CatalogItem, Event, SessionState
from tests.orchestrator.conftest import catalog_item, make_learner, make_session

T = "S1"
P = "P1"
ANSWERS = {f"S1.{n}": str(10 + n) for n in range(1, 13)}


def _catalog(extra_rules: tuple[Any, ...] = ()) -> tuple[CatalogItem, ...]:
    items = []
    for n in range(1, 13):
        item = catalog_item(f"S1.{n}", skill=T, answer=str(10 + n), difficulty=0.3)
        if n == 1 and extra_rules:
            item = replace(item, misconception_rules=extra_rules)
        items.append(item)
    for n in range(1, 5):
        items.append(catalog_item(f"P1.{n}", skill=P, answer=str(20 + n), difficulty=0.2))
    return tuple(items)


def _learner(p_known: float = 0.7) -> LearnerState:
    learner = make_learner()
    learner.mastery[P] = Mastery(skill_id=P, p_known=p_known)
    learner.ladders[P] = SkillLadder(skill_id=P, achieved=[1, 2, 3])
    return learner


def _session(
    catalog=None, *, teacher_share: bool = False, with_prereq: bool = True
) -> SessionState:
    session = make_session(
        *(catalog or _catalog()),
        overlay=(T,),  # the prerequisite belongs to an earlier chapter
        prereqs={T: (P,)} if with_prereq else {},
        introduced={P, T},
    )
    session.teacher_share = teacher_share
    session.misconception_remedial = {"MC.PRE": P}
    return session


def _answer(learner, session, action: Action, response: str, latency: int = 9000) -> Action:
    return policy(
        learner,
        session,
        Event(type="answer", response=response, item_id=action.item_id, latency_ms=latency),
    )


def _right(item_id: str | None) -> str:
    if item_id and item_id.startswith("S1."):
        return ANSWERS[item_id]
    return str(20 + int((item_id or "P1.1").split(".")[1]))


def _fail_first_attempt(learner, session, action: Action) -> Action:
    """A wrong first attempt, then wrong until the item is over (reveal); returns the next."""
    action = _answer(learner, session, action, "999")
    for _ in range(6):
        if action.type == "hint":
            action = _answer(learner, session, action, "999")
        elif action.type == "reveal_solution":
            action = policy(learner, session, Event(type="continue"))
        else:
            break
    return action


# ---- R33: probe on a prerequisite gap -----------------------------------------------------


def test_a_prerequisite_gap_answer_probes_the_prerequisite() -> None:
    catalog = _catalog((("MC.PRE", ("-2",)),))
    learner, session = _learner(), _session(catalog)
    first = policy(learner, session, None)
    assert first.item_id == "S1.1"
    probe = _answer(learner, session, first, "-2")
    assert probe.type == "show_item" and probe.skill_id == P
    assert probe.extras["probe"] is True and probe.extras["for_skill"] == T
    assert probe.rule_id == "R33"
    assert session.last_diagnosis == {"class": "prerequisite_gap", "detail": P}


def test_the_probe_is_a_practice_item_on_the_prerequisite_and_counts_once_for_bkt() -> None:
    catalog = _catalog((("MC.PRE", ("-2",)),))
    learner, session = _learner(), _session(catalog)
    first = policy(learner, session, None)
    probe = _answer(learner, session, first, "-2")
    before = learner.mastery[P].attempts
    _answer(learner, session, probe, _right(probe.item_id))
    assert learner.mastery[P].attempts == before + 1


def test_a_right_probe_changes_the_representation_for_the_target_skill() -> None:
    catalog = _catalog((("MC.PRE", ("-2",)),))
    learner, session = _learner(), _session(catalog)
    first = policy(learner, session, None)
    probe = _answer(learner, session, first, "-2")
    shown = _answer(learner, session, probe, _right(probe.item_id))
    assert shown.type == "worked_example" and shown.skill_id == T
    assert shown.extras["representation_change"] is True
    back = policy(learner, session, Event(type="continue"))
    assert back.type == "show_item" and back.skill_id == T
    assert session.probe_for is None


def test_a_wrong_probe_schedules_the_prerequisite_and_returns_to_the_target_later() -> None:
    catalog = _catalog((("MC.PRE", ("-2",)),))
    learner, session = _learner(), _session(catalog)
    first = policy(learner, session, None)
    probe = _answer(learner, session, first, "-2")
    nxt = _answer(learner, session, probe, "999")
    # the prerequisite comes next, for two practice items, then the target skill again
    seen = []
    action = nxt
    for _ in range(5):
        seen.append(action.skill_id)
        if action.type == "reveal_solution":
            action = policy(learner, session, Event(type="continue"))
            continue
        action = _answer(learner, session, action, _right(action.item_id))
        while action.type in {"explain_back_prompt"}:
            action = policy(learner, session, Event(type="continue"))
    assert seen[0] == P and seen[1] == P
    assert T in seen[2:]


def test_no_probe_when_the_prerequisite_has_no_items() -> None:
    catalog = tuple(i for i in _catalog((("MC.PRE", ("-2",)),)) if i.skill_ids[0] != P)
    learner, session = _learner(), _session(catalog)
    first = policy(learner, session, None)
    action = _answer(learner, session, first, "-2")
    assert action.type == "worked_example" and action.extras["representation_change"] is True


def test_the_probe_is_offered_once_per_prerequisite_per_session() -> None:
    catalog = _catalog((("MC.PRE", ("-2",)),))
    catalog = tuple(
        replace(i, misconception_rules=(("MC.PRE", ("-2",)),)) if i.id.startswith("S1.") else i
        for i in catalog
    )
    learner, session = _learner(), _session(catalog)
    first = policy(learner, session, None)
    probe = _answer(learner, session, first, "-2")
    shown = _answer(learner, session, probe, _right(probe.item_id))
    assert shown.type == "worked_example"
    nxt = policy(learner, session, Event(type="continue"))
    again = _answer(learner, session, nxt, "-2")
    assert not again.extras.get("probe")


# ---- R34: wheel spinning --------------------------------------------------------------------


def test_three_wrong_first_attempts_in_a_row_flag_the_skill_and_probe() -> None:
    learner, session = _learner(), _session()
    action = policy(learner, session, None)
    action = _fail_first_attempt(learner, session, action)
    action = _fail_first_attempt(learner, session, action)
    assert T not in session.wheel_skills
    third = _answer(learner, session, action, "999")
    assert T in session.wheel_skills
    assert third.type == "show_item" and third.extras["probe"] is True and third.skill_id == P


def test_a_right_first_attempt_resets_the_streak() -> None:
    learner, session = _learner(), _session()
    action = policy(learner, session, None)
    action = _fail_first_attempt(learner, session, action)
    action = _fail_first_attempt(learner, session, action)
    action = _answer(learner, session, action, _right(action.item_id))  # right first attempt
    while action.type == "explain_back_prompt":
        action = policy(learner, session, Event(type="continue"))
    assert session.wrong_first_streak.get(T, 0) == 0
    action = _fail_first_attempt(learner, session, action)
    assert T not in session.wheel_skills


def test_ten_items_without_level_4_flag_the_skill() -> None:
    learner, session = _learner(), _session()
    action = policy(learner, session, None)
    items = 0
    for _ in range(80):
        if T in session.wheel_skills:
            break
        if action.type in {"show_item", "similar_item"} and action.skill_id == T:
            items += 1  # alternate right and wrong first attempts so the streak never reaches 3
            if items % 2:
                action = _answer(learner, session, action, _right(action.item_id))
            else:
                action = _fail_first_attempt(learner, session, action)
        elif action.type in {"explain_back_prompt", "worked_example", "reveal_solution"}:
            action = policy(learner, session, Event(type="continue"))
        elif action.type == "show_item" and action.extras.get("probe"):
            action = _answer(learner, session, action, _right(action.item_id))
        else:
            break
    assert T in session.wheel_skills
    assert max(session.wrong_first_streak.values(), default=0) < 3
    assert session.skill_items[T] == 10 and items <= 10


def test_a_teacher_alert_is_queued_only_with_teacher_share() -> None:
    for share in (False, True):
        learner, session = _learner(), _session(teacher_share=share)
        action = policy(learner, session, None)
        for _ in range(3):
            action = _fail_first_attempt(learner, session, action)
        assert T in session.wheel_skills
        want = [{"skill_id": T, "type": "wheel_spinning"}] if share else []
        assert session.alerts == want, share


def test_the_alert_is_queued_once_per_skill_per_session() -> None:
    learner, session = _learner(), _session(teacher_share=True)
    action = policy(learner, session, None)
    for _ in range(6):
        action = _fail_first_attempt(learner, session, action)
    assert session.alerts.count({"skill_id": T, "type": "wheel_spinning"}) == 1


def test_a_skill_that_reached_level_4_is_not_wheel_spinning() -> None:
    learner, session = _learner(), _session()
    action = policy(learner, session, None)
    action = _fail_first_attempt(learner, session, action)
    action = _fail_first_attempt(learner, session, action)
    learner.ladders[T] = SkillLadder(skill_id=T, achieved=[1, 2, 3, 4])
    _answer(learner, session, action, "999")
    assert T not in session.wheel_skills


def test_without_prerequisites_the_wheel_stop_changes_the_representation() -> None:
    learner, session = _learner(), _session(with_prereq=False)
    action = policy(learner, session, None)
    action = _fail_first_attempt(learner, session, action)
    action = _fail_first_attempt(learner, session, action)
    third = _answer(learner, session, action, "999")
    assert T in session.wheel_skills
    assert third.type == "worked_example" and third.extras["representation_change"] is True
