"""What an answer records beyond right or wrong, and what the learner is told back."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import EventRow, ItemRow, MisconceptionHitRow, MisconceptionRow
from app.orchestrator.types import SessionState
from app.player.signals import (
    clean_correction,
    clean_signals,
    public_diagnosis,
    record_misconception_hit,
)
from tests.conftest import World, auth_header
from tests.learner.test_chapters import chapters_world  # noqa: F401  (fixture)
from tests.player.test_g2b_api import g2b_world  # noqa: F401  (fixture)
from tests.player.test_stuck_picker_api import Play


def _state(kind: str | None, session_type: str = "practice") -> SessionState:
    state = SessionState(
        session_type=session_type,
        now=datetime.now(UTC),
        catalog=(),
        overlay_skill_ids=(),
        bkt_params={},
    )
    state.last_diagnosis = {"class": kind, "detail": "internal"} if kind else None
    return state


# ── cleaning ─────────────────────────────────────────────────────────────────


def test_confidence_is_kept_only_on_an_answer_and_only_when_it_is_a_known_value() -> None:
    assert clean_signals("answer", {"confidence": "sure"})["confidence"] == "sure"
    assert clean_signals("answer", {"confidence": "unsure"})["confidence"] == "unsure"
    for bad in ("SURE", "maybe", 1, None, ["sure"]):
        assert "confidence" not in clean_signals("answer", {"confidence": bad})
    assert "confidence" not in clean_signals("request_help", {"confidence": "sure"})


@pytest.mark.parametrize("bad", [True, False, "400", None, -1, -0.5, [], {}])
def test_an_unusable_answer_time_is_dropped_not_guessed(bad: object) -> None:
    assert "latency_ms" not in clean_signals("answer", {"response": "3", "latency_ms": bad})


def test_a_real_answer_time_is_kept_as_whole_milliseconds() -> None:
    assert clean_signals("answer", {"latency_ms": 1234})["latency_ms"] == 1234
    assert clean_signals("answer", {"latency_ms": 1234.9})["latency_ms"] == 1234
    assert clean_signals("answer", {"latency_ms": 0})["latency_ms"] == 0


def test_cleaning_never_changes_the_other_fields_or_the_input() -> None:
    original = {"response": "x", "confidence": "bogus", "latency_ms": "no"}
    cleaned = clean_signals("answer", original)
    assert cleaned == {"response": "x"}
    assert original == {"response": "x", "confidence": "bogus", "latency_ms": "no"}


def test_a_correction_keeps_only_a_known_diagnosis_class() -> None:
    assert clean_correction({"diagnosed": "slip"}) == {"diagnosed": "slip"}
    assert clean_correction({"diagnosed": "<script>"}) == {}
    assert clean_correction({}) == {}


# ── what the learner is told ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "kind", ["misconception", "slip", "prerequisite_gap", "incomplete_procedure"]
)
def test_an_explainable_wrong_answer_tells_the_learner_its_class(kind: str) -> None:
    shown = public_diagnosis("answer", _state(kind), {}, None)
    assert shown is not None and shown["class"] == kind
    assert "detail" not in shown


def test_the_misconception_id_is_shown_only_for_a_misconception() -> None:
    assert public_diagnosis("answer", _state("misconception"), {}, "MC.1") == {
        "class": "misconception",
        "misconception_id": "MC.1",
    }
    assert "misconception_id" not in (public_diagnosis("answer", _state("slip"), {}, "MC.1") or {})


@pytest.mark.parametrize("kind", [None, "none", "generic", "disengagement"])
def test_nothing_is_said_when_the_class_explains_nothing(kind: str | None) -> None:
    assert public_diagnosis("answer", _state(kind), {}, None) is None


def test_nothing_is_said_after_a_hint_request_or_in_an_assessment() -> None:
    assert public_diagnosis("request_help", _state("slip"), {}, None) is None
    assert public_diagnosis("answer", _state("slip", "diagnostic"), {}, None) is None
    assert public_diagnosis("answer", _state("slip", "checkpoint"), {}, None) is None
    assert public_diagnosis("answer", _state("slip"), {"assessment": True}, None) is None


# ── the stored misconception hit ─────────────────────────────────────────────


def _fake_session(known_misconception: bool, known_item: bool):
    def get(model, key):
        if model is MisconceptionRow:
            return object() if known_misconception else None
        if model is ItemRow:
            return object() if known_item else None
        raise AssertionError(model)

    added: list[object] = []
    return SimpleNamespace(get=get, add=added.append, added=added)


def test_a_hit_is_written_only_for_a_known_misconception_on_a_known_item() -> None:
    now = datetime.now(UTC)
    student = uuid.uuid4()
    ok = _fake_session(True, True)
    assert record_misconception_hit(ok, student, "answer", _state("misconception"), "MC", "IT", now)
    assert len(ok.added) == 1 and isinstance(ok.added[0], MisconceptionHitRow)

    for known_mc, known_item in [(False, True), (True, False)]:
        unknown = _fake_session(known_mc, known_item)
        assert not record_misconception_hit(
            unknown, student, "answer", _state("misconception"), "MC", "IT", now
        )
        assert unknown.added == []


def test_no_hit_for_other_classes_other_events_or_missing_ids() -> None:
    now = datetime.now(UTC)
    student = uuid.uuid4()
    for event, state, mc, item in [
        ("answer", _state("slip"), "MC", "IT"),
        ("answer", _state(None), "MC", "IT"),
        ("request_help", _state("misconception"), "MC", "IT"),
        ("answer", _state("misconception"), None, "IT"),
        ("answer", _state("misconception"), "MC", None),
    ]:
        fake = _fake_session(True, True)
        assert not record_misconception_hit(fake, student, event, state, mc, item, now)
        assert fake.added == []


# ── through the API ──────────────────────────────────────────────────────────


@pytest.fixture
def misconception_world(db: Session, g2b_world: World) -> World:  # noqa: F811
    db.add(
        MisconceptionRow(
            id="MC.SAME",
            title={"en": "Same skill idea"},
            explanation={"en": "A common idea.", "ne": None, "as": None},
            remedial_skill="SK.A",
            status="draft",
        )
    )
    for row in db.scalars(select(ItemRow).where(ItemRow.id.like("G2.%"))):
        row.misconception_rules = [{"id": "MC.SAME", "when_answer_equals": ["-2"]}]
    db.commit()
    return g2b_world


def _events(db: Session, event_type: str) -> list[EventRow]:
    return list(db.scalars(select(EventRow).where(EventRow.event_type == event_type)))


def test_a_misconception_answer_is_recorded_explained_and_stored_with_its_confidence(
    client: TestClient, db: Session, misconception_world: World
) -> None:
    play = Play(client, misconception_world)
    action = play.send("answer", response="-2", latency_ms=4200, confidence="sure")

    assert action["extras"]["diagnosis"] == {
        "class": "misconception",
        "misconception_id": "MC.SAME",
    }
    hits = list(db.scalars(select(MisconceptionHitRow)))
    assert [(h.misconception_id, h.item_id) for h in hits] == [("MC.SAME", action["item_id"])]
    stored = _events(db, "answer")[-1]
    assert stored.payload["confidence"] == "sure"
    assert stored.latency_ms == 4200
    assert stored.payload["diagnosis"]["class"] == "misconception"


def test_a_right_answer_writes_no_hit_and_shows_no_diagnosis(
    client: TestClient, db: Session, misconception_world: World
) -> None:
    play = Play(client, misconception_world)
    item = play.action["item_id"]
    action = play.send("answer", response=str(5 + int(item.split(".")[1])), latency_ms=5000)
    assert "diagnosis" not in (action.get("extras") or {})
    assert db.scalar(select(func.count()).select_from(MisconceptionHitRow)) == 0


def test_a_bad_confidence_or_time_never_breaks_the_answer(
    client: TestClient, db: Session, misconception_world: World
) -> None:
    play = Play(client, misconception_world)
    action = play.send("answer", response="-2", latency_ms="soon", confidence="whatever")
    assert action["type"] in {"hint", "show_item", "check_your_work", "show_solution", "feedback"}
    stored = _events(db, "answer")[-1]
    assert "confidence" not in stored.payload
    assert stored.latency_ms is None


def test_that_is_not_why_is_recorded_and_changes_nothing_else(
    client: TestClient, db: Session, misconception_world: World
) -> None:
    play = Play(client, misconception_world)
    hint = play.send("answer", response="-2", latency_ms=4200)
    before = client.get(f"/sessions/{play.session_id}", headers=play.headers).json()["action"]

    sent = client.post(
        f"/sessions/{play.session_id}/events",
        json={
            "client_event_id": str(uuid.uuid4()),
            "event_type": "diagnosis_correction",
            "item_id": hint["item_id"],
            "payload": {"diagnosed": "misconception", "junk": "dropped"},
        },
        headers=auth_header(misconception_world.student_token),
    )
    assert sent.status_code == 200, sent.text
    after = client.get(f"/sessions/{play.session_id}", headers=play.headers).json()["action"]
    assert after["type"] == before["type"] and after["item_id"] == before["item_id"]
    saved = _events(db, "diagnosis_correction")
    assert len(saved) == 1 and saved[0].payload == {"diagnosed": "misconception"}


def test_a_retried_correction_is_recorded_once(
    client: TestClient, db: Session, misconception_world: World
) -> None:
    play = Play(client, misconception_world)
    play.send("answer", response="-2", latency_ms=4200)
    body = {
        "client_event_id": str(uuid.uuid4()),
        "event_type": "diagnosis_correction",
        "payload": {"diagnosed": "slip"},
    }
    headers = auth_header(misconception_world.student_token)
    first = client.post(f"/sessions/{play.session_id}/events", json=body, headers=headers)
    again = client.post(f"/sessions/{play.session_id}/events", json=body, headers=headers)
    assert first.status_code == again.status_code == 200
    assert again.json()["duplicate"] is True
    assert len(_events(db, "diagnosis_correction")) == 1
