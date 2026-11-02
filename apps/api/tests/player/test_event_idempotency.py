"""A retried or replayed event id must never be recorded twice or act on another session."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.db.models import EventRow, SafetyFlagRow, SessionRow
from tests.conftest import World, auth_header

DISTRESS = {"text": "I want to die"}


def _session(db: Session, world: World) -> uuid.UUID:
    row = SessionRow(
        id=uuid.uuid4(),
        student_id=uuid.UUID(world.student_share_id),
        started_at=now_utc(),
        type="practice",
        last_active_at=now_utc(),
    )
    db.add(row)
    db.commit()
    return row.id


def _send(client: TestClient, world: World, session_id: uuid.UUID, event_id: uuid.UUID):
    return client.post(
        f"/sessions/{session_id}/events",
        json={"client_event_id": str(event_id), "event_type": "explain_back", "payload": DISTRESS},
        headers=auth_header(world.student_token),
    )


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_a_retried_distress_message_is_recorded_and_alerted_once(
    client: TestClient, db: Session, world: World
) -> None:
    session_id = _session(db, world)
    event_id = uuid.uuid4()

    first = _send(client, world, session_id, event_id)
    again = _send(client, world, session_id, event_id)

    assert first.status_code == 200, first.text
    assert again.status_code == 200, again.text
    assert again.json()["duplicate"] is True
    assert _count(db, SafetyFlagRow) == 1
    assert _count(db, EventRow) == 1


def test_an_event_id_from_another_session_is_a_conflict_not_a_duplicate(
    client: TestClient, db: Session, world: World
) -> None:
    first_session = _session(db, world)
    second_session = _session(db, world)
    event_id = uuid.uuid4()
    assert _send(client, world, first_session, event_id).status_code == 200

    clash = _send(client, world, second_session, event_id)

    assert clash.status_code == 409
    assert clash.json()["detail"] == "event_id_conflict"
    assert _count(db, EventRow) == 1
    assert _count(db, SafetyFlagRow) == 1
