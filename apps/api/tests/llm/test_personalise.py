"""G4 step 4: the gateway wired into a session. The policy stays pure; personalising happens
once, after the policy decides, and the result is stored on the action."""

from __future__ import annotations

import random
import uuid
from collections.abc import Generator
from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import (
    ItemRow,
    LlmCallRow,
    MasteryRow,
    OverlayRow,
    ReviewCardRow,
    SkillRow,
    StudentRow,
)
from app.llm.gateway import Gateway
from app.llm.personalise import personalise_action, set_gateway
from app.llm.provider import FakeProvider
from app.orchestrator.types import Action
from tests.conftest import World, auth_header
from tests.orchestrator.conftest import catalog_item, make_session

AUTHORED_HINT = "Undo the operation."
GOOD = "Think about which step undoes the adding."


def _gateway(*replies: str | Exception) -> tuple[Gateway, FakeProvider]:
    provider = FakeProvider(list(replies))
    gateway = Gateway(
        provider, sample_rate=1.0, rng=random.Random(1), models={"fast": "f", "strong": "s"}
    )
    return gateway, provider


@pytest.fixture(autouse=True)
def _reset() -> Generator[None, None, None]:
    keep = settings.llm_api_key
    settings.llm_api_key = "test-key"
    yield
    settings.llm_api_key = keep
    set_gateway(None)


def _state(*, ai: bool = True, session_type: str = "practice"):
    item = replace(
        catalog_item(answer="6"),
        hints=((1, AUTHORED_HINT), (2, "Do the opposite to the number."), (3, "x = 6")),
        solution_steps=("x = 6",),
        authored_explanation="Take 4 off both sides to keep the balance.",
    )
    state = make_session(item, session_type=session_type, introduced={"MATH.S1"})
    state.has_ai_processing = ai
    state.current_item_id = item.id
    return state, item


def _hint(level: int = 1, **extras: Any) -> Action:
    return Action(
        type="hint", item_id="ITEM.A", hint_level=level, text=AUTHORED_HINT, extras=extras
    )


def _item_row(db: Session, item_id: str) -> None:
    db.add(
        ItemRow(
            id=item_id,
            skill_ids=["MATH.S1"],
            primary_skill="MATH.S1",
            difficulty=0.3,
            type="expression",
            pool="practice",
            role="procedure",
            stem={"en": "Solve for x: x + 4 = 10"},
            verify=None,
            options=[],
            answer={"sympy": "6", "accept": ["6"]},
            solution_steps=[{"en": "x = 6"}],
            hints=[],
            prediction_prompt={"en": ""},
            misconception_rules=[],
            status="draft",
        )
    )
    db.commit()


def _call(db: Session, state, action: Action, **kw: Any) -> Action:
    return personalise_action(db, state, action, grade=9, language="en", session_id=None, **kw)


def test_a_level_1_hint_is_rephrased_logged_and_marked_as_llm(db: Session) -> None:
    state, item = _state()
    _item_row(db, item.id)
    gateway, provider = _gateway(GOOD)
    set_gateway(gateway)
    action = _call(db, state, _hint(1, kind="ladder"))
    assert action.text == GOOD and action.source == "llm" and action.llm_called
    assert "Undo the operation." in provider.calls[0].system  # the authored source is in the prompt
    assert "Never state or reveal this answer: 6" in provider.calls[0].system
    db.commit()
    row = db.scalars(select(LlmCallRow)).one()
    assert row.purpose == "personalise_hint" and row.outcome == "llm" and row.sampled


def test_a_reply_that_leaks_the_answer_is_replaced_by_the_authored_hint(db: Session) -> None:
    state, item = _state()
    _item_row(db, item.id)
    gateway, provider = _gateway("The answer is 6.", "So x is six.")
    set_gateway(gateway)
    action = _call(db, state, _hint(1))
    assert action.text == AUTHORED_HINT and action.source == "authored"
    assert len(provider.calls) == 2
    db.commit()
    assert db.scalars(select(LlmCallRow)).one().outcome == "fallback"


@pytest.mark.parametrize(
    "action",
    [
        _hint(3),  # level 3 is the authored reveal
        _hint(1, kind="restate"),  # authored restatement
        _hint(1, kind="step"),  # authored step hint
        Action(type="show_item", item_id="ITEM.A", text="Solve x + 4 = 10"),
    ],
)
def test_only_plain_ladder_hints_at_levels_1_and_2_are_personalised(
    db: Session, action: Action
) -> None:
    state, item = _state()
    _item_row(db, item.id)
    gateway, provider = _gateway(GOOD)
    set_gateway(gateway)
    before = action.text
    out = _call(db, state, action)
    assert provider.calls == [] and out.text == before and out.source == "authored"


@pytest.mark.parametrize(
    ("ai", "key", "session_type"),
    [(False, "k", "practice"), (True, "", "practice"), (True, "k", "diagnostic")],
)
def test_no_call_without_consent_key_or_in_assessment(
    db: Session, ai: bool, key: str, session_type: str
) -> None:
    settings.llm_api_key = key
    state, item = _state(ai=ai, session_type=session_type)
    _item_row(db, item.id)
    gateway, provider = _gateway(GOOD)
    set_gateway(gateway)
    out = _call(db, state, _hint(1))
    assert provider.calls == [] and out.text == AUTHORED_HINT and not out.llm_called
    db.commit()
    assert db.scalars(select(LlmCallRow)).all() == []  # skipped calls are not logged


def test_explain_back_is_graded_formatively_and_the_students_words_are_not_logged(
    db: Session,
) -> None:
    state, item = _state()
    _item_row(db, item.id)
    gateway, provider = _gateway("GRADE: good\nYou named the step that undoes the adding.")
    set_gateway(gateway)
    result = Action(
        type="explain_back_result",
        item_id=item.id,
        text="Take 4 off both sides to keep the balance.",
        grade=None,
        store_text=True,
    )
    out = _call(db, state, result, student_text="I took the four off both sides to balance it")
    assert out.grade == "good" and (out.text or "").startswith("You named the step")
    assert "I took the four off both sides" in provider.calls[0].user  # sent as data
    db.commit()
    row = db.scalars(select(LlmCallRow)).one()
    assert row.purpose == "grade_explain_back"
    assert "four off both sides" not in " ".join(str(v) for v in vars(row).values())


def test_explain_back_falls_back_to_the_authored_explanation_with_no_grade(db: Session) -> None:
    state, item = _state()
    _item_row(db, item.id)
    gateway, _ = _gateway("no grade line", "still none")
    set_gateway(gateway)
    result = Action(
        type="explain_back_result", item_id=item.id, text="Model explanation.", grade=None
    )
    out = _call(db, state, result, student_text="because")
    assert out.grade is None and out.text == "Model explanation."


def test_encouragement_is_rephrased_but_may_not_praise_the_person(db: Session) -> None:
    state, item = _state()
    _item_row(db, item.id)
    praise = {
        "trigger": "persisted_on_hard_item",
        "variant": "persisted_1",
        "text": "You kept going.",
    }
    action = Action(type="show_item", item_id=item.id, extras={"encouragement": praise})
    gateway, _ = _gateway("You tried again when it was hard. That takes effort.")
    set_gateway(gateway)
    out = _call(db, state, action)
    assert (
        out.extras["encouragement"]["text"]
        == "You tried again when it was hard. That takes effort."
    )
    bad_gateway, _ = _gateway("You are so smart.", "What a genius.")
    set_gateway(bad_gateway)
    again = _call(
        db, state, Action(type="show_item", item_id=item.id, extras={"encouragement": praise})
    )
    assert again.extras["encouragement"]["text"] == "You kept going."


# --- through the API: a real session ----------------------------------------------------------

PLAIN = "MATH.PLAIN.LLM"


def _seed(db: Session, world: World) -> None:
    settings.allow_draft_content = True
    db.add(
        SkillRow(
            id=PLAIN,
            title={"en": PLAIN},
            grade_band=[9],
            subject="math",
            prerequisites=[],
            related=[],
            misconceptions=[],
            bkt={"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
            status="approved",
        )
    )
    db.add(
        OverlayRow(
            id="OV.LLM",
            curriculum_id="bhutan",
            grade=9,
            chapter="linear_equations",
            skill_ids=[PLAIN],
            live=False,
        )
    )
    for n, (stem, ans) in enumerate([("x + 4 = 10", "6"), ("x - 3 = 5", "8"), ("2x = 14", "7")]):
        db.add(
            ItemRow(
                id=f"LLM.P{n}",
                skill_ids=[PLAIN],
                primary_skill=PLAIN,
                difficulty=0.25,
                type="expression",
                pool="practice",
                role="procedure",
                stem={"en": f"Solve for x: {stem}", "ne": None, "as": None},
                verify=None,
                options=[],
                answer={"sympy": ans, "accept": [ans, f"x={ans}"]},
                solution_steps=[{"en": f"x = {ans}"}],
                hints=[
                    {"level": 1, "en": "Undo the operation."},
                    {"level": 2, "en": "Do the opposite to the number."},
                    {"level": 3, "en": f"x = {ans}"},
                ],
                prediction_prompt={"en": "Is x small?"},
                misconception_rules=[],
                status="draft",
            )
        )
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    student.current_chapter_id = "OV.LLM"
    student.context_key = {**(student.context_key or {}), "chapter_id": "OV.LLM"}
    db.commit()


def _to_first_hint(client: TestClient, world: World) -> dict:
    headers = auth_header(world.student_token)
    started = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "practice"},
        headers=headers,
    )
    assert started.status_code == 200, started.text
    sid, action = started.json()["id"], started.json()["action"]

    def send(event_type: str, item_id: str | None = None, **payload: Any) -> dict:
        body: dict[str, Any] = {
            "client_event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "payload": payload,
        }
        if item_id:
            body["item_id"] = item_id
        response = client.post(f"/sessions/{sid}/events", json=body, headers=headers)
        assert response.status_code == 200, response.text
        return response.json()["action"]

    if action["type"] == "predict":
        action = send("predict_response", response="4")
    if action["type"] == "worked_example":
        action = send("continue")
    assert action["type"] == "show_item", action["type"]
    return send("answer", action["item_id"], response="99", latency_ms=9000)


def test_a_wrong_answer_in_a_real_session_gets_a_personalised_hint_and_no_mastery_change(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world)
    gateway, provider = _gateway(GOOD)
    set_gateway(gateway)
    action = _to_first_hint(client, world)
    assert action["type"] == "hint" and action["hint_level"] == 1
    assert action["text"] == GOOD and action["source"] == "llm" and action["llm_called"]
    assert len(provider.calls) == 1
    db.expire_all()
    assert db.scalars(select(LlmCallRow)).one().session_id is not None
    # the LLM never touched mastery or review cards: only the answered item's own update exists
    assert len(db.scalars(select(ReviewCardRow)).all()) == 0
    assert all(m.skill_id == PLAIN for m in db.scalars(select(MasteryRow)).all())


def test_the_same_session_without_a_key_serves_the_authored_hint(
    client: TestClient, world: World, db: Session
) -> None:
    settings.llm_api_key = ""
    _seed(db, world)
    gateway, provider = _gateway(GOOD)
    set_gateway(gateway)
    action = _to_first_hint(client, world)
    assert action["type"] == "hint" and action["text"] == "Undo the operation."
    assert provider.calls == [] and not action["llm_called"]


def _play(client: TestClient, world: World, *, max_events: int = 40) -> list[dict]:
    """Play a plain session to its end, answering every item correctly."""
    headers = auth_header(world.student_token)
    started = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "practice"},
        headers=headers,
    )
    assert started.status_code == 200, started.text
    sid, action = started.json()["id"], started.json()["action"]
    seen = [action]
    answers = {"LLM.P0": "6", "LLM.P1": "8", "LLM.P2": "7"}
    for _ in range(max_events):
        if action.get("ended_reason") or action["type"] in {"end_session", "done"}:
            break
        kind, item_id = "continue", None
        payload: dict[str, Any] = {}
        if action["type"] == "predict":
            kind, payload = "predict_response", {"response": "4"}
        elif action["type"] in {"show_item", "similar_item", "warmup_item"}:
            item_id = action["item_id"]
            kind, payload = "answer", {"response": answers[item_id], "latency_ms": 9000}
        elif action["type"] == "explain_back_prompt":
            kind, payload = "explain_back", {"text": "I undid the step on both sides."}
        body: dict[str, Any] = {
            "client_event_id": str(uuid.uuid4()),
            "event_type": kind,
            "payload": payload,
        }
        if item_id:
            body["item_id"] = item_id
        response = client.post(f"/sessions/{sid}/events", json=body, headers=headers)
        assert response.status_code == 200, response.text
        action = response.json()["action"]
        seen.append(action)
    return seen


@pytest.mark.parametrize("key", ["", "test-key"])
def test_sessions_complete_end_to_end_without_a_key_and_the_model_is_never_needed(
    client: TestClient, world: World, db: Session, key: str
) -> None:
    settings.llm_api_key = key
    _seed(db, world)
    gateway, provider = _gateway()  # no scripted replies: any model call would fail and fall back
    set_gateway(gateway)
    seen = _play(client, world)
    assert seen[-1].get("ended_reason") or seen[-1]["type"] in {"end_session", "done"}
    texts = [a.get("text") or "" for a in seen]
    assert all("llm" != a.get("source") for a in seen)  # every reply is authored
    assert all("Think about" not in t for t in texts)
    if not key:
        assert provider.calls == []


def test_explain_back_grading_never_changes_mastery_ladder_or_review_cards(
    db: Session, world: World
) -> None:
    from datetime import UTC, datetime

    student = uuid.UUID(world.student_share_id)
    db.add(
        MasteryRow(
            student_id=student,
            skill_id="MATH.S1",
            p_known=0.6,
            attempts=4,
            unhinted_correct=2,
            hinted_correct=1,
            last_updated=datetime.now(UTC),
            ladder_level=3,
            ladder_evidence={"3": ["e1"]},
            flags={"k": 1},
            ladder_memory={"streak": 2},
        )
    )
    state, item = _state()
    _item_row(db, item.id)
    db.commit()

    def snapshot() -> tuple[Any, ...]:
        db.expire_all()
        row = db.get(MasteryRow, (student, "MATH.S1"))
        assert row is not None
        return (
            row.p_known, row.attempts, row.unhinted_correct, row.hinted_correct, row.ladder_level,
            row.ladder_evidence, row.flags, row.ladder_memory,
            len(db.scalars(select(ReviewCardRow)).all()),
        )  # fmt: skip

    before = snapshot()
    gateway, _ = _gateway("GRADE: good\nYou undid the step on both sides.")
    set_gateway(gateway)
    result = Action(type="explain_back_result", item_id=item.id, text="Model.", store_text=True)
    out = _call(db, state, result, student_text="I undid the step on both sides.")
    db.commit()
    assert out.grade == "good"
    assert snapshot() == before
