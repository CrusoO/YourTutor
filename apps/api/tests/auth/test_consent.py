from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import SessionRow
from tests.conftest import World, auth_header


def test_no_session_without_tutoring(client: TestClient, world: World) -> None:
    created = client.post(
        "/students",
        json={"display_name": "No Consent", "grade": 9, "board": "bhutan"},
        headers=auth_header(world.parent_token),
    )
    student_id = created.json()["id"]
    client.post(
        f"/students/{student_id}/pin",
        json={"pin": "2222"},
        headers=auth_header(world.parent_token),
    )
    pin = client.post(f"/students/{student_id}/pin/verify", json={"pin": "2222"})
    response = client.post(
        "/sessions",
        json={"student_id": student_id, "type": "practice"},
        headers=auth_header(pin.json()["access_token"]),
    )
    assert response.status_code == 403
    assert "tutoring" in response.json()["detail"]


def test_consent_revoked_mid_session(
    client: TestClient, world: World, db: Session
) -> None:
    started = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "practice"},
        headers=auth_header(world.student_token),
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["id"]
    revoke = client.post(
        f"/students/{world.student_share_id}/consent/revoke",
        headers=auth_header(world.parent_token),
    )
    assert revoke.status_code == 200
    event = client.post(
        f"/sessions/{session_id}/events",
        json={
            "client_event_id": str(uuid.uuid4()),
            "event_type": "answer",
            "item_id": "ITEM.1",
            "payload": {"response": "5", "latency_ms": 1000},
        },
        headers=auth_header(world.student_token),
    )
    assert event.status_code == 200, event.text
    body = event.json()
    assert body["action"]["type"] == "end_session"
    assert body["action"]["reason"] == "consent_revoked"
    assert body["llm_called"] is False
    db.expire_all()
    row = db.get(SessionRow, uuid.UUID(session_id))
    assert row is not None
    assert row.ended_reason == "consent_revoked"
    assert row.llm_called is False
