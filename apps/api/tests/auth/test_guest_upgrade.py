"""G6 step 2: a guest becomes a family student, with every record kept."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.consent import active_scopes
from app.db.models import ConsentRow, EventRow, MasteryRow, SessionRow, StudentRow, UserRow
from tests.conftest import auth_header, signup


def _guest(client: TestClient) -> dict:
    res = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9})
    assert res.status_code == 200, res.text
    return res.json()


def _play(client: TestClient, guest: dict) -> str:
    headers = auth_header(guest["token"])
    session = client.post(
        "/sessions",
        json={"student_id": guest["student_id"], "type": "practice"},
        headers=headers,
    )
    assert session.status_code == 200, session.text
    return session.json()["id"]


def _body(guest: dict, **over: object) -> dict:
    body = {
        "guest_token": guest["token"],
        "version": "v1",
        "scopes": ["tutoring", "ai_processing"],
        "display_name": "Asha",
    }
    body.update(over)
    return body


def test_upgrade_moves_the_guest_to_the_guardian_and_keeps_every_record(
    client: TestClient, sender, db: Session
) -> None:
    guest = _guest(client)
    session_id = _play(client, guest)
    sid = uuid.UUID(guest["student_id"])
    counts_before = (
        db.scalar(select(func.count()).select_from(EventRow)),
        db.scalar(select(func.count()).select_from(SessionRow)),
        db.scalar(select(func.count()).select_from(MasteryRow)),
    )
    parent_token = signup(client, sender, "guardian@example.com")
    res = client.post(
        f"/guest/{guest['student_id']}/upgrade",
        json=_body(guest),
        headers=auth_header(parent_token),
    )
    assert res.status_code == 200, res.text
    assert res.json()["family_code"]

    db.expire_all()
    student = db.get(StudentRow, sid)
    assert student is not None and student.display_name == "Asha"
    owner = db.get(UserRow, student.parent_id)
    assert owner is not None and owner.role == "parent" and owner.email == "guardian@example.com"
    assert (
        db.scalar(select(func.count()).select_from(EventRow)),
        db.scalar(select(func.count()).select_from(SessionRow)),
        db.scalar(select(func.count()).select_from(MasteryRow)),
    ) == counts_before
    assert db.get(SessionRow, uuid.UUID(session_id)) is not None
    assert db.scalar(select(func.count()).select_from(UserRow).where(UserRow.role == "guest")) == 0
    assert active_scopes(db, sid) == {"tutoring", "ai_processing"}
    # the guest's own token still works, and the guardian now sees the child
    today = client.get("/students/me/today", headers=auth_header(guest["token"]))
    assert today.status_code == 200 and today.json()["student_id"] == guest["student_id"]
    mine = client.get(f"/students/{guest['student_id']}", headers=auth_header(parent_token))
    assert mine.status_code == 200


def test_upgrade_needs_tutoring_consent_and_a_known_scope(
    client: TestClient, sender, db: Session
) -> None:
    guest = _guest(client)
    parent_token = signup(client, sender, "g2@example.com")
    url = f"/guest/{guest['student_id']}/upgrade"
    no_tutoring = client.post(
        url, json=_body(guest, scopes=["ai_processing"]), headers=auth_header(parent_token)
    )
    assert no_tutoring.status_code == 400
    unknown = client.post(
        url, json=_body(guest, scopes=["tutoring", "nope"]), headers=auth_header(parent_token)
    )
    assert unknown.status_code == 400
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(ConsentRow)) == 0
    student = db.get(StudentRow, uuid.UUID(guest["student_id"]))
    assert student is not None
    owner = db.get(UserRow, student.parent_id)
    assert owner is not None and owner.role == "guest"  # unchanged


def test_upgrade_needs_the_guests_own_token_and_a_guardian_login(
    client: TestClient, sender
) -> None:
    guest, other = _guest(client), _guest(client)
    parent_token = signup(client, sender, "g3@example.com")
    url = f"/guest/{guest['student_id']}/upgrade"
    wrong = client.post(
        url, json=_body(guest, guest_token=other["token"]), headers=auth_header(parent_token)
    )
    assert wrong.status_code == 403
    by_student = client.post(url, json=_body(guest), headers=auth_header(guest["token"]))
    assert by_student.status_code == 403
    anonymous = client.post(url, json=_body(guest))
    assert anonymous.status_code == 401
    extra = client.post(url, json=_body(guest, school="X"), headers=auth_header(parent_token))
    assert extra.status_code == 422


def test_a_family_student_cannot_be_upgraded_again(client: TestClient, sender) -> None:
    guest = _guest(client)
    parent_token = signup(client, sender, "g4@example.com")
    url = f"/guest/{guest['student_id']}/upgrade"
    first = client.post(url, json=_body(guest), headers=auth_header(parent_token))
    assert first.status_code == 200
    again = client.post(url, json=_body(guest), headers=auth_header(parent_token))
    assert again.status_code == 409
