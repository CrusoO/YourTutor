"""The reason model through the real endpoints: off changes nothing, on keeps one open episode."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import EventRow
from app.learner.reason.moves import FAMILIES
from tests.conftest import World
from tests.learner.test_chapters import chapters_world  # noqa: F401  (fixture)
from tests.player.test_g2b_api import g2b_world  # noqa: F401  (fixture)
from tests.player.test_signals import misconception_world  # noqa: F401  (fixture)
from tests.player.test_stuck_picker_api import Play


@pytest.fixture
def world(request: pytest.FixtureRequest) -> World:
    found: World = request.getfixturevalue("misconception_world")
    return found


WRONG = "-2"  # matches the authored misconception MC.SAME on every G2 item


def _events(db: Session, event_type: str) -> list[EventRow]:
    db.expire_all()
    rows = db.scalars(select(EventRow).where(EventRow.event_type == event_type))
    return sorted(rows, key=lambda r: r.created_at)


def _side(client: TestClient, play: Play, event_type: str, **payload: Any) -> None:
    sent = client.post(
        f"/sessions/{play.session_id}/events",
        json={
            "client_event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "item_id": play.action.get("item_id"),
            "payload": payload,
        },
        headers=play.headers,
    )
    assert sent.status_code == 200, sent.text


def test_off_by_default_nothing_about_reasons_is_stored_or_shown(
    client: TestClient,
    db: Session,
    world: World,
) -> None:
    assert settings.reason_first_enabled is False
    play = Play(client, world)
    action = play.send("answer", response=WRONG, latency_ms=4000)
    assert "reason" not in (action.get("extras") or {})
    assert "reason" not in _events(db, "answer")[-1].payload
    _side(client, play, "move_chosen", family="picture")
    assert _events(db, "move_chosen")[-1].payload == {"family": "picture"}


@pytest.fixture
def reasons_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "reason_first_enabled", True)


def test_a_wrong_answer_shows_how_to_help_and_stores_the_episode(
    client: TestClient,
    db: Session,
    world: World,
    reasons_on: None,
) -> None:
    play = Play(client, world)
    action = play.send("answer", response=WRONG, latency_ms=4000, confidence="sure")
    shown = action["extras"]["reason"]
    assert shown["band"] in {"likely", "maybe", "unclear"}
    assert set(shown["offer"]) <= set(FAMILIES) and 1 <= len(shown["offer"]) <= 3
    assert 0 <= shown["level"] <= 3
    stored = _events(db, "answer")[-1].payload["reason"]
    assert stored["skill"] and stored["weights"] and abs(sum(stored["weights"].values()) - 1) < 1e-6
    assert stored["offered"] == shown["offer"]


def test_a_second_wrong_answer_builds_on_the_first(
    client: TestClient,
    db: Session,
    world: World,
    reasons_on: None,
) -> None:
    play = Play(client, world)
    play.send("answer", response=WRONG, latency_ms=4000)
    first = _events(db, "answer")[-1].payload["reason"]["weights"]
    play.send("answer", response=WRONG, latency_ms=4000)
    second = _events(db, "answer")[-1].payload["reason"]["weights"]
    top = max(first, key=first.get)  # type: ignore[arg-type]
    assert second[top] >= first[top]


def test_the_chosen_help_is_credited_to_the_next_answer(
    client: TestClient,
    db: Session,
    world: World,
    reasons_on: None,
) -> None:
    play = Play(client, world)
    play.send("answer", response=WRONG, latency_ms=4000)
    offered = _events(db, "answer")[-1].payload["reason"]["offered"]
    _side(client, play, "move_chosen", family=offered[0])
    moved = _events(db, "move_chosen")[-1].payload
    assert moved["family"] == offered[0] and moved["reason"]["pending"] == offered[0]

    item = play.action["item_id"]
    play.send("answer", response=str(5 + int(item.split(".")[1])), latency_ms=5000)
    closing = _events(db, "answer")[-1].payload["reason"]
    assert closing["effect"] == {"family": offered[0], "correct": True}
    assert closing["weights"] == {} and closing["pending"] is None


def test_that_is_not_why_lowers_the_stored_belief(
    client: TestClient,
    db: Session,
    world: World,
    reasons_on: None,
) -> None:
    play = Play(client, world)
    play.send("answer", response=WRONG, latency_ms=4000)
    before = _events(db, "answer")[-1].payload["reason"]["weights"]
    _side(client, play, "diagnosis_correction", diagnosed="misconception")
    saved = _events(db, "diagnosis_correction")[-1].payload
    assert saved["diagnosed"] == "misconception"
    after = saved["reason"]["weights"]
    cause = "misconception:MC.SAME"
    assert after[cause] < before[cause]


def test_an_unknown_help_family_is_dropped_and_never_breaks_the_session(
    client: TestClient,
    db: Session,
    world: World,
    reasons_on: None,
) -> None:
    play = Play(client, world)
    play.send("answer", response=WRONG, latency_ms=4000)
    _side(client, play, "move_chosen", family="<script>")
    saved = _events(db, "move_chosen")[-1].payload
    assert "family" not in saved
    assert saved["reason"]["pending"] is None


def test_a_move_with_no_open_episode_is_recorded_without_one(
    client: TestClient,
    db: Session,
    world: World,
    reasons_on: None,
) -> None:
    play = Play(client, world)
    _side(client, play, "move_chosen", family="steps")
    assert _events(db, "move_chosen")[-1].payload == {"family": "steps"}
