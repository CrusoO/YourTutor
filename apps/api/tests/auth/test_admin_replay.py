from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.auth.security import now_utc
from app.db.models import EventRow, SessionRow
from tests.conftest import World, auth_header


def test_admin_replay_is_admin_only(client: TestClient, world: World, db) -> None:
    session = SessionRow(
        id=uuid.uuid4(),
        student_id=uuid.UUID(world.student_share_id),
        started_at=now_utc(),
        type="practice",
        active_ms=0,
        last_active_at=now_utc(),
        plan={},
    )
    db.add(session)
    db.flush()
    db.add(
        EventRow(
            session_id=session.id,
            event_type="answer",
            payload={"response": "5"},
            correct=True,
            created_at=now_utc(),
            state_before="practice",
            state_after="explain_back",
            rule_id="R08",
        )
    )
    db.commit()
    denied = client.get(
        f"/admin/sessions/{session.id}/replay",
        headers=auth_header(world.parent_token),
    )
    assert denied.status_code == 403
    ok = client.get(
        f"/admin/sessions/{session.id}/replay",
        headers=auth_header(world.admin_token),
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["session_id"].startswith("sess_")
    assert body["student_id"].startswith("stu_")
    assert body["events"][0]["rule_id"] == "R08"
