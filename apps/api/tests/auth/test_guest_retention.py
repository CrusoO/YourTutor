"""G6 step 3: idle guests are deleted after the profile's window (time-travel test)."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.db.models import (
    AuthSessionRow,
    EventRow,
    MasteryRow,
    SessionRow,
    StudentRow,
    UserRow,
)
from app.retention import purge_guests
from tests.conftest import World, auth_header


def _guest(client: TestClient, play: bool = False) -> dict:
    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    if play:
        res = client.post(
            "/sessions",
            json={"student_id": guest["student_id"], "type": "practice"},
            headers=auth_header(guest["token"]),
        )
        assert res.status_code == 200, res.text
    return guest


def _count(db: Session, table: type) -> int:
    return db.scalar(select(func.count()).select_from(table)) or 0


def test_a_guest_idle_past_the_window_is_deleted_with_everything_recorded(
    client: TestClient, db: Session
) -> None:
    _guest(client, play=True)
    assert _count(db, SessionRow) == 1
    later = now_utc() + timedelta(days=31)  # default_strict keeps guests 30 days
    assert purge_guests(db, now=later) == 1
    db.expire_all()
    for table in (StudentRow, SessionRow, EventRow, MasteryRow, AuthSessionRow):
        assert _count(db, table) == 0, table
    assert db.scalar(select(func.count()).select_from(UserRow).where(UserRow.role == "guest")) == 0


def test_a_guest_inside_the_window_is_kept(client: TestClient, db: Session) -> None:
    _guest(client, play=True)
    assert purge_guests(db, now=now_utc() + timedelta(days=29)) == 0
    assert _count(db, StudentRow) == 1


def test_activity_restarts_the_clock(client: TestClient, db: Session) -> None:
    guest = _guest(client, play=True)
    row = db.scalars(select(SessionRow)).one()
    row.last_active_at = now_utc() + timedelta(days=20)  # played on day 20
    db.commit()
    assert purge_guests(db, now=now_utc() + timedelta(days=40)) == 0  # 20 idle days
    assert purge_guests(db, now=now_utc() + timedelta(days=51)) == 1  # 31 idle days
    assert db.get(StudentRow, uuid.UUID(guest["student_id"])) is None


def test_family_students_are_never_purged(db: Session, world: World) -> None:
    assert purge_guests(db, now=now_utc() + timedelta(days=3650)) == 0
    assert db.get(StudentRow, uuid.UUID(world.student_share_id)) is not None


def test_a_profile_can_set_a_shorter_window(client: TestClient, db: Session, monkeypatch) -> None:
    from dataclasses import replace

    from app.registries import startup

    real = startup.deployment_jurisdiction_profile
    monkeypatch.setattr(
        "app.retention.deployment_jurisdiction_profile",
        lambda pid=None: replace(real(pid), guest_retention_days=3),
    )
    _guest(client)
    assert purge_guests(db, now=now_utc() + timedelta(days=2)) == 0
    assert purge_guests(db, now=now_utc() + timedelta(days=4)) == 1


def test_the_family_delete_also_removes_mastery_and_review_records(
    client: TestClient, db: Session, world: World
) -> None:
    from app.db.models import ReviewCardRow

    res = client.delete("/parents/me", headers=auth_header(world.parent_token))
    assert res.status_code == 200, res.text
    db.expire_all()
    for table in (MasteryRow, ReviewCardRow):
        assert _count(db, table) == 0
