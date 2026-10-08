"""G2a through the API: stuck-point picker, help alias, diagnosis on events, one BKT update."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EventRow, ItemRow, MasteryRow, MisconceptionRow, StudentRow
from tests.conftest import World, auth_header
from tests.learner.test_chapters import chapters_world  # noqa: F401  (fixture)
from tests.player.test_skip_ahead_api import _item

STEP_HINTS = ["First step: undo the plus.", "Second step: now undo the times.", "Check it."]
RESTATE = "Let's read it again: what number makes the sentence true?"


def _full_item(item_id: str, answer: str, **extra: Any) -> ItemRow:
    row = _item(item_id, answer, role=extra.pop("role", "procedure"), difficulty=0.25)
    row.step_hints = [{"en": text, "ne": None, "as": None} for text in STEP_HINTS]
    row.hint_restate = {"en": RESTATE, "ne": None, "as": None}
    row.slip_patterns = [{"kind": "sign_flip"}, {"kind": "off_by", "max_distance": 1}]
    row.min_plausible_ms = 3000
    row.solution_steps = [{"en": "Subtract 7."}, {"en": "x = 12 - 7"}, {"en": f"x = {answer}"}]
    for key, value in extra.items():
        setattr(row, key, value)
    return row


@pytest.fixture
def picker_world(db: Session, chapters_world: World) -> World:  # noqa: F811
    for item_id, answer in (("PK.1", "6"), ("PK.2", "8"), ("PK.3", "7")):
        db.add(_full_item(item_id, answer))
    db.commit()
    return chapters_world


class Play:
    def __init__(self, client: TestClient, world: World) -> None:
        self.client = client
        self.world = world
        self.headers = auth_header(world.student_token)
        started = client.post(
            "/sessions",
            json={"student_id": world.student_share_id, "type": "practice", "chapter_id": "CH.ONE"},
            headers=self.headers,
        )
        assert started.status_code == 200, started.text
        self.session_id = started.json()["id"]
        self.action = started.json()["action"]
        self.advance_to_item()

    def send(self, event_type: str, **payload: Any) -> dict[str, Any]:
        body = {
            "client_event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "item_id": self.action.get("item_id"),
            "payload": payload,
        }
        response = self.client.post(
            f"/sessions/{self.session_id}/events", json=body, headers=self.headers
        )
        assert response.status_code == 200, response.text
        self.action = response.json()["action"]
        return self.action

    def advance_to_item(self) -> None:
        if self.action["type"] == "predict":
            self.send("predict_response", response="yes")
        if self.action["type"] == "worked_example":
            self.send("continue")
        assert self.action["type"] == "show_item", self.action["type"]


def _events(db: Session, session_id: str) -> list[EventRow]:
    db.expire_all()
    return list(
        db.scalars(
            select(EventRow)
            .where(EventRow.session_id == uuid.UUID(session_id))
            .order_by(EventRow.created_at, EventRow.id)
        )
    )


def _mastery(db: Session, world: World) -> MasteryRow | None:
    db.expire_all()
    return db.get(MasteryRow, (uuid.UUID(world.student_share_id), "SK.A"))


def test_help_before_an_answer_opens_the_picker_with_localised_choices(
    client: TestClient, picker_world: World
) -> None:
    play = Play(client, picker_world)
    action = play.send("request_help")
    assert action["type"] == "ask_stuck_point"
    assert action["extras"]["choices"] == ["start", "step", "restate", "might_be_right"]
    assert action["extras"]["step_count"] == 3
    assert action["can_request_help"] is False and action["can_request_hint"] is False
    assert action["rule_id"] == "R32"


def test_the_picker_state_survives_between_requests(
    client: TestClient, picker_world: World
) -> None:
    play = Play(client, picker_world)
    play.send("request_help")
    hint = play.send("stuck_choice", choice="start")
    assert hint["type"] == "hint" and hint["hint_level"] == 1
    again = play.send("request_help")  # no second picker for the same item
    assert again["type"] == "hint" and again["hint_level"] == 2


def test_request_hint_is_stored_and_treated_as_request_help(
    client: TestClient, db: Session, picker_world: World
) -> None:
    play = Play(client, picker_world)
    assert play.send("request_hint")["type"] == "ask_stuck_point"
    stored = [e.event_type for e in _events(db, play.session_id)]
    assert "request_help" in stored and "request_hint" not in stored


def test_both_capability_flags_are_present_on_an_item_screen(
    client: TestClient, picker_world: World
) -> None:
    play = Play(client, picker_world)
    assert "can_request_help" in play.action and "can_request_hint" in play.action
    assert play.action["can_request_help"] == play.action["can_request_hint"]


def test_a_step_hint_comes_from_the_item_and_uses_no_ladder_level(
    client: TestClient, picker_world: World
) -> None:
    play = Play(client, picker_world)
    play.send("request_help")
    assert play.send("stuck_choice", choice="step")["type"] == "ask_stuck_step"
    hint = play.send("stuck_step", index=1)
    assert hint["type"] == "hint" and hint["text"] == STEP_HINTS[1]
    assert hint["hint_level_shown"] == 0
    assert hint["extras"] == {"kind": "step", "step": 1}


def test_restate_uses_the_authored_paraphrase(client: TestClient, picker_world: World) -> None:
    play = Play(client, picker_world)
    play.send("request_help")
    hint = play.send("stuck_choice", choice="restate")
    assert hint["text"] == RESTATE and hint["extras"]["kind"] == "restate"


def test_the_picker_and_later_answers_are_one_bkt_update(
    client: TestClient, db: Session, picker_world: World
) -> None:
    play = Play(client, picker_world)
    play.send("request_help")
    play.send("stuck_choice", choice="start")
    play.send("answer", response="999", latency_ms=9000)
    play.send("answer", response="999", latency_ms=9000)
    row = _mastery(db, picker_world)
    assert row is not None and row.attempts == 1


def test_a_wrong_answer_stores_its_diagnosis_on_the_event(
    client: TestClient, db: Session, picker_world: World
) -> None:
    play = Play(client, picker_world)
    play.send("answer", response="999", latency_ms=9000)
    answers = [e for e in _events(db, play.session_id) if e.event_type == "answer"]
    assert answers[-1].payload["diagnosis"] == {"class": "generic", "detail": None}
    assert answers[-1].payload["response"] == "999"  # the client's own fields are kept


def test_a_misconception_answer_gets_the_targeted_hint_in_the_students_language(
    client: TestClient, db: Session, picker_world: World
) -> None:
    db.add(
        MisconceptionRow(
            id="MC.TEST",
            title={"en": "One side only"},
            explanation={"en": "It looks like only one side changed.", "ne": None, "as": None},
            remedial_skill="SK.A",
            status="draft",
        )
    )
    for row in db.scalars(select(ItemRow).where(ItemRow.id.like("PK.%"))):
        row.misconception_rules = [{"id": "MC.TEST", "when_answer_equals": ["13"]}]
    db.commit()
    play = Play(client, picker_world)
    hint = play.send("answer", response="13", latency_ms=9000)
    assert hint["type"] == "hint" and hint["misconception_id"] == "MC.TEST"
    assert hint["text"] == "It looks like only one side changed."
    answers = [e for e in _events(db, play.session_id) if e.event_type == "answer"]
    assert answers[-1].payload["diagnosis"]["class"] == "misconception"


def test_a_slip_on_a_level_4_skill_gets_check_your_work_through_the_api(
    client: TestClient, db: Session, picker_world: World
) -> None:
    for item_id, answer in (("AP.1", "6"), ("AP.2", "8")):
        db.add(_full_item(item_id, answer, role="apply", difficulty=0.25))
    from tests.learner.test_chapters import _mastery as add_mastery

    add_mastery(db, picker_world, "SK.A", 4)
    add_mastery(db, picker_world, "SK.B", 4)
    play = Play.__new__(Play)
    play.client, play.world = client, picker_world
    play.headers = auth_header(picker_world.student_token)
    started = client.post(
        "/sessions",
        json={
            "student_id": picker_world.student_share_id,
            "type": "practice",
            "chapter_id": "CH.ONE",
        },
        headers=play.headers,
    )
    play.session_id = started.json()["id"]
    play.action = started.json()["action"]
    assert play.action["type"] == "show_item", play.action["type"]
    answer = {"AP.1": "6", "AP.2": "8"}[play.action["item_id"]]
    flipped = f"-{answer}"
    action = play.send("answer", response=flipped, latency_ms=9000)
    assert action["type"] == "check_your_work"
    assert action["extras"]["check_kind"] == "sign_flip"
    assert action["hint_level_shown"] == 0
    assert action["rule_id"] == "R31"
    answers = [e for e in _events(db, play.session_id) if e.event_type == "answer"]
    assert answers[-1].payload["diagnosis"] == {"class": "slip", "detail": "sign_flip"}


def test_unknown_picker_choices_are_flagged_not_crashed(
    client: TestClient, picker_world: World
) -> None:
    play = Play(client, picker_world)
    play.send("request_help")
    action = play.send("stuck_choice", choice="give_me_the_answer")
    assert action["rejected"] is True and action["guardrail_flag"] == "bad_choice"


def test_the_student_record_is_untouched_by_the_picker(
    client: TestClient, db: Session, picker_world: World
) -> None:
    play = Play(client, picker_world)
    play.send("request_help")
    play.send("stuck_choice", choice="restate")
    student = db.get(StudentRow, uuid.UUID(picker_world.student_share_id))
    assert student is not None


def test_openapi_marks_the_old_hint_names_as_deprecated(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    text = spec["paths"]["/sessions/{session_id}/events"]["post"]["description"]
    assert "request_hint" in text and "deprecated" in text and "can_request_help" in text
