"""G1: T by ladder level, role-aware selection, and ladder updates driven by policy()."""

from __future__ import annotations

from dataclasses import replace

from app.learner.ladder import SkillLadder
from app.learner.types import LearnerState, Mastery
from app.orchestrator.policy import policy
from app.orchestrator.types import CatalogItem, Event, SessionState
from tests.orchestrator.conftest import NOW, catalog_item, due_card, make_learner, make_session

S1, S2 = "MATH.S1", "MATH.S2"


def item(
    item_id: str,
    *,
    skill: str = S1,
    role: str = "procedure",
    structure: str = "",
    difficulty: float = 0.3,
) -> CatalogItem:
    return replace(
        catalog_item(item_id, skill=skill, difficulty=difficulty),
        role=role,
        structure=structure or f"struct-{item_id}",
    )


def ladder_at(*levels: int, skill: str = S1) -> SkillLadder:
    return SkillLadder(skill_id=skill, achieved=list(levels))


def learner_with(**ladders: SkillLadder) -> LearnerState:
    state = make_learner()
    for skill, row in ladders.items():
        state.ladders[skill] = row
    return state


def level4(skill: str = S1) -> SkillLadder:
    return ladder_at(3, 4, skill=skill)


def first_action(learner: LearnerState, session: SessionState):
    return policy(learner, session, None)


class Student:
    """Drives policy() like the player: always answers correctly unless told otherwise."""

    def __init__(self, learner: LearnerState, session: SessionState) -> None:
        self.learner = learner
        self.session = session
        self.count = 0
        self.served: list[CatalogItem] = []
        self.answer_ids: list[str] = []

    def _event(self, event_type: str, **kw) -> Event:
        self.count += 1
        return Event(type=event_type, event_id=f"ev{self.count}", **kw)

    def send(self, event_type: str, **kw):
        return policy(self.learner, self.session, self._event(event_type, **kw))

    def start(self):
        return policy(self.learner, self.session, None)

    def settle(self, action):
        """Skip predict / worked example / explain-back prompts until a question appears."""
        while action.type in {
            "predict",
            "worked_example",
            "explain_back_prompt",
            "explain_back_result",
        }:
            if action.type == "predict":
                action = self.send("predict_response", text="a guess")
            else:
                action = self.send("continue")
        return action

    def answer(self, action, *, correct: bool = True, hinted: bool = False):
        row = self.session.item(action.item_id)
        assert row is not None
        self.served.append(row)
        if hinted:
            self.send("request_hint", item_id=row.id)
        self.answer_ids.append(f"ev{self.count + 1}")
        return self.send("answer", item_id=row.id, response="5" if correct else "0", latency_ms=800)


def run_correct(student: Student, count: int):
    action = student.settle(student.start())
    for _ in range(count):
        assert action.type in {"show_item", "similar_item", "warmup_item"}, action.type
        action = student.settle(student.answer(action))
    return action


# --- T = first overlay skill with ladder level < 4 -------------------------------------


def test_t_skips_skills_at_level_4_even_when_p_known_is_low() -> None:
    session = make_session(item("A", skill=S1), item("B", skill=S2), overlay=(S1, S2))
    learner = make_learner(p_known={S1: 0.3})
    learner.ladders[S1] = level4()
    action = first_action(learner, session)
    assert action.type == "predict" and action.skill_id == S2


def test_high_p_known_alone_no_longer_skips_a_skill() -> None:
    session = make_session(item("A", skill=S1), item("B", skill=S2), overlay=(S1, S2))
    learner = LearnerState()
    learner.mastery[S1] = Mastery(skill_id=S1, p_known=0.99)  # no ladder evidence
    action = first_action(learner, session)
    assert action.skill_id == S1


def test_chapter_complete_when_every_skill_is_at_level_6() -> None:
    session = make_session(item("A"), introduced={S1})
    learner = learner_with(**{S1: ladder_at(3, 4, 5, 6)})
    action = first_action(learner, session)
    assert action.type == "end_session" and action.ended_reason == "chapter_complete"


# --- role-aware selection ---------------------------------------------------------------


def _extension_session() -> SessionState:
    return make_session(
        item("P1", role="procedure"),
        item("A1", role="apply"),
        item("T1", role="transfer"),
        introduced={S1},
    )


def test_selection_serves_apply_at_level_4() -> None:
    action = first_action(learner_with(**{S1: level4()}), _extension_session())
    assert action.type == "show_item" and action.item_id == "A1"


def test_selection_serves_transfer_at_level_5() -> None:
    action = first_action(learner_with(**{S1: ladder_at(3, 4, 5)}), _extension_session())
    assert action.type == "show_item" and action.item_id == "T1"


def test_missing_apply_item_logs_content_gap_and_ends_the_chapter() -> None:
    session = make_session(item("P1"), item("T1", role="transfer"), introduced={S1})
    action = first_action(learner_with(**{S1: level4()}), session)
    assert action.type == "end_session" and action.ended_reason == "chapter_complete"
    assert [(g["skill"], g["role"]) for g in session.content_gaps] == [(S1, "apply")]


def test_below_level_4_prefers_procedure_items() -> None:
    session = make_session(
        item("P1"), item("A1", role="apply"), item("T1", role="transfer"), introduced={S1}
    )
    learner = learner_with(**{S1: ladder_at(2)})
    assert first_action(learner, session).item_id == "P1"


def test_missing_procedure_falls_back_to_any_role_and_logs_a_gap() -> None:
    session = make_session(item("A1", role="apply"), introduced={S1})
    action = first_action(learner_with(**{S1: ladder_at(2)}), session)
    assert action.type == "show_item" and action.item_id == "A1"
    assert [(g["skill"], g["role"]) for g in session.content_gaps] == [(S1, "procedure")]


def _mix_session(shown: int) -> SessionState:
    rows = [item(f"F{n}", difficulty=0.9) for n in range(4)]
    rows += [
        item("P1"),
        item("P2"),
        item("R1", role="recall"),
        item("X1", role="explain"),
    ]
    session = make_session(*rows, introduced={S1})
    session.shown_item_ids = [f"F{n}" for n in range(shown)]
    return session


def test_recall_and_explain_items_are_mixed_in_until_level_2() -> None:
    roles = []
    for shown in range(4):
        action = first_action(make_learner(), _mix_session(shown))
        roles.append(next(r.role for r in _mix_session(0).catalog if r.id == action.item_id))
    assert roles == ["procedure", "recall", "procedure", "explain"]


def test_no_mixing_once_level_2_is_reached() -> None:
    for shown in range(4):
        learner = learner_with(**{S1: ladder_at(2)})
        action = first_action(learner, _mix_session(shown))
        row = next(r for r in _mix_session(0).catalog if r.id == action.item_id)
        assert row.role == "procedure", shown


def test_warmup_uses_the_role_for_the_skills_level() -> None:
    session = make_session(
        item("P1"), item("A1", role="apply"), item("T1", role="transfer"), introduced={S1}
    )
    learner = learner_with(**{S1: level4()})
    learner.cards[S1] = due_card(S1, due=NOW)
    action = first_action(learner, session)
    assert action.type == "warmup_item" and action.item_id == "A1"


# --- ladder updates through policy -----------------------------------------------------


def _three_structures() -> list[CatalogItem]:
    return [
        item("P1", structure="s-a"),
        item("P2", structure="s-b"),
        item("P3", structure="s-c"),
        item("P4", structure="s-d"),
    ]


def test_three_unhinted_correct_answers_over_two_structures_reach_level_4() -> None:
    session = make_session(*_three_structures(), introduced={S1})
    student = Student(make_learner(), session)
    run_correct(student, 3)
    ladder = student.learner.ladders[S1]
    assert ladder.level == 4
    assert ladder.evidence[4] == student.answer_ids[:3]


def test_one_structure_never_reaches_level_4() -> None:
    items = [item(f"P{n}", structure="same") for n in range(1, 6)]
    session = make_session(*items, introduced={S1})
    student = Student(make_learner(), session)
    run_correct(student, 5)
    assert student.learner.ladders[S1].level == 3


def test_hinted_correct_answers_never_reach_level_4() -> None:
    session = make_session(*_three_structures(), introduced={S1})
    student = Student(make_learner(), session)
    action = student.settle(student.start())
    for _ in range(3):
        action = student.settle(student.answer(action, hinted=True))
    assert student.learner.ladders[S1].level <= 3


def test_explain_back_never_changes_the_ladder() -> None:
    session = make_session(*_three_structures(), introduced={S1})
    student = Student(make_learner(), session)
    action = student.start()
    action = student.answer(student.settle(action))
    assert action.type == "explain_back_prompt"
    before = student.learner.ladders[S1].to_json()
    student.send("explain_back", text="because we do the same to both sides")
    assert student.learner.ladders[S1].to_json() == before


def test_diagnostic_and_checkpoint_answers_never_create_ladders() -> None:
    for pool, session_type in (("diagnostic", "diagnostic"), ("checkpoint", "checkpoint")):
        rows = [replace(catalog_item(f"{pool}{n}"), pool=pool, role="explain") for n in range(3)]
        session = make_session(*rows, session_type=session_type, introduced={S1})
        learner = make_learner()
        action = policy(learner, session, None)
        for _ in range(3):
            if action.type != "show_item":
                break
            action = policy(
                learner, session, Event(type="answer", item_id=action.item_id, response="5")
            )
        assert learner.ladders == {}, session_type


def test_lesson_flow_then_correct_first_item_reaches_level_1() -> None:
    session = make_session(item("P1", role="recall"), item("P2"), overlay=(S1,))
    learner = make_learner()
    action = policy(learner, session, None)
    assert action.type == "predict"
    action = policy(learner, session, Event(type="predict_response", text="smaller", event_id="p"))
    assert action.type == "worked_example"
    action = policy(learner, session, Event(type="continue", event_id="c"))
    assert action.type == "show_item"
    answer = policy(
        learner,
        session,
        Event(type="answer", item_id=action.item_id, response="5", event_id="a1"),
    )
    assert answer.type in {"explain_back_prompt", "show_item"}
    assert 1 in learner.ladders[S1].achieved


def test_events_without_ids_get_unique_generated_ids() -> None:
    session = make_session(*_three_structures(), introduced={S1})
    learner = make_learner()
    action = policy(learner, session, None)
    for _ in range(2):
        action = policy(
            learner, session, Event(type="answer", item_id=action.item_id, response="5")
        )
        if action.type == "explain_back_prompt":
            action = policy(learner, session, Event(type="continue"))
    ids = [event_id for ids in learner.ladders[S1].evidence.values() for event_id in ids]
    assert ids and len(set(ids)) == len(set(ids))
    assert all(isinstance(event_id, str) and event_id for event_id in ids)
