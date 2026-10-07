"""S1b fix: Resume on Today reopens an idle-ended session instead of showing "Done for now"."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import SessionRow
from app.orchestrator.policy import IDLE_END_MS
from tests.conftest import World, auth_header
from tests.learner.test_chapters import chapters_world  # noqa: F401  (fixture)
from tests.player.test_skip_ahead_api import _item


@pytest.fixture
def idle_world(db: Session, chapters_world: World) -> World:  # noqa: F811
    for item_id, answer in (("RS.1", "6"), ("RS.2", "8"), ("RS.3", "7")):
        db.add(_item(item_id, answer, role="procedure", difficulty=0.25))
    db.commit()
    return chapters_world


def _start(client: TestClient, world: World) -> dict:
    response = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "practice", "chapter_id": "CH.ONE"},
        headers=auth_header(world.student_token),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _go_idle(client: TestClient, world: World, session_id: str) -> dict:
    response = client.post(
        f"/sessions/{session_id}/events",
        json={
            "client_event_id": str(uuid.uuid4()),
            "event_type": "idle_nudge",
            "payload": {"idle_ms": IDLE_END_MS + 1},
        },
        headers=auth_header(world.student_token),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_an_idle_session_ends_resumable(client: TestClient, idle_world: World) -> None:
    started = _start(client, idle_world)
    ended = _go_idle(client, idle_world, started["id"])
    assert ended["action"]["type"] == "end_session"
    assert ended["action"]["reason"] == "idle"
    today = client.get("/students/me/today", headers=auth_header(idle_world.student_token)).json()
    assert today["resume"]["session_id"] == started["id"]
    assert today["resume"]["resumable"] is True


def test_resume_reopens_the_idle_session(
    client: TestClient, db: Session, idle_world: World
) -> None:
    started = _start(client, idle_world)
    _go_idle(client, idle_world, started["id"])
    opened = client.get(f"/sessions/{started['id']}", headers=auth_header(idle_world.student_token))
    assert opened.status_code == 200, opened.text
    action = opened.json()["action"]
    assert action["type"] != "end_session"
    assert action["reason"] != "idle"
    db.expire_all()
    row = db.get(SessionRow, uuid.UUID(started["id"]))
    assert row is not None
    assert row.ended_at is None and row.resumable is False


def test_resume_then_continues_to_accept_events(client: TestClient, idle_world: World) -> None:
    started = _start(client, idle_world)
    _go_idle(client, idle_world, started["id"])
    action = client.get(
        f"/sessions/{started['id']}", headers=auth_header(idle_world.student_token)
    ).json()["action"]
    sent = client.post(
        f"/sessions/{started['id']}/events",
        json={
            "client_event_id": str(uuid.uuid4()),
            "event_type": "predict_response" if action["type"] == "predict" else "continue",
            "item_id": action.get("item_id"),
            "payload": {"response": "yes", "latency_ms": 500},
        },
        headers=auth_header(idle_world.student_token),
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["action"]["type"] != "end_session"


def test_a_session_that_really_ended_is_not_reopened(
    client: TestClient, db: Session, idle_world: World
) -> None:
    started = _start(client, idle_world)
    db.expire_all()
    row = db.get(SessionRow, uuid.UUID(started["id"]))
    assert row is not None
    row.ended_at = row.started_at
    row.ended_reason = "soft_cap"
    row.resumable = False
    plan = dict(row.plan or {})
    plan["last_action"] = {"type": "end_session", "ended_reason": "soft_cap"}
    row.plan = plan
    db.commit()
    again = client.get(f"/sessions/{started['id']}", headers=auth_header(idle_world.student_token))
    assert again.json()["action"]["type"] == "end_session"
