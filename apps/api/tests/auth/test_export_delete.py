from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.sender import MemoryOtpSender
from app.db.models import StudentRow, UserRow
from tests.conftest import auth_header, signup


def test_parent_export_and_delete(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    token = signup(client, sender, "export@example.com")
    created = client.post(
        "/students",
        json={"display_name": "Export Kid", "grade": 9, "board": "bhutan"},
        headers=auth_header(token),
    )
    student_id = created.json()["id"]
    exported = client.get("/parents/me/export", headers=auth_header(token))
    assert exported.status_code == 200
    body = exported.json()
    assert body["user"]["email"] == "export@example.com"
    assert body["students"][0]["id"] == student_id
    deleted = client.delete("/parents/me", headers=auth_header(token))
    assert deleted.status_code == 200
    assert db.scalar(select(UserRow).where(UserRow.email == "export@example.com")) is None
    assert db.scalar(select(StudentRow).where(StudentRow.id == uuid.UUID(student_id))) is None
