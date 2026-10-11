"""G10: the weekly guardian report, from real events, with quiet hours and no repeats."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ReportLogRow, StudentRow, UserRow
from app.registries.loaders import JurisdictionProfile
from app.reports.senders import MemoryReportSender
from app.reports.weekly import run_weekly, week_key
from tests.conftest import World, auth_header
from tests.offline.sim import NS, play, seed_content


@pytest.fixture
def content(db: Session) -> None:
    seed_content(db)


def _practise(client: TestClient, world: World, db: Session, days_ago: float, name: str) -> None:
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    played = play(db, student, t0=datetime.now(UTC) - timedelta(days=days_ago))
    body = {
        "client_session_id": str(uuid.uuid5(NS, name)),
        "started_at": played["started_at"],
        "events": played["events"],
    }
    res = client.post("/sync/events", json=body, headers=auth_header(world.student_token))
    assert res.status_code == 200, res.text


def _local(db: Session, world: World, hour: int, *, days: int = 0) -> datetime:
    """Today at this local hour in the child's time zone, as a UTC moment."""
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    tz = ZoneInfo(student.timezone or "UTC")
    local = datetime.now(tz).replace(hour=hour, minute=0, second=0, microsecond=0)
    return (local + timedelta(days=days)).astimezone(UTC)


def _sender() -> MemoryReportSender:
    return MemoryReportSender()


def test_the_report_is_built_from_the_childs_real_week_and_sent_to_the_guardian(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _practise(client, world, db, 1, "w1")
    sender = _sender()
    out = run_weekly(db, _local(db, world, 12), senders={"email": sender})
    assert out.sent == [world.student_share_id]
    destination, subject, body = sender.sent[0]
    assert destination == "parent@example.com" and subject == "Share Kid's week on YourTutor"
    assert "practised on 1 day(s) this week" in body
    assert "New this week:" in body and ("OFF.S1" in body or "OFF.S2" in body)
    assert "http://localhost:3000/guardian" in body
    lowered = body.lower()
    for word in ("rank", "score", "streak", "behind", "compared", "percent"):
        assert word not in lowered.replace("never compares", ""), word
    assert "never compares" in lowered  # the footer says so


def test_a_week_is_sent_once_and_the_next_week_again(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _practise(client, world, db, 9, "w1")
    sender = _sender()
    first = _local(db, world, 12, days=-8)
    run_weekly(db, first, senders={"email": sender})
    again = run_weekly(db, first + timedelta(hours=2), senders={"email": sender})
    assert len(sender.sent) == 1
    assert again.skipped[world.student_share_id] == "already_sent"
    assert db.scalar(select(func.count()).select_from(ReportLogRow)) == 1
    _practise(client, world, db, 1, "w2")
    now = _local(db, world, 12)
    later = run_weekly(db, now, senders={"email": sender})
    assert later.sent == [world.student_share_id] and len(sender.sent) == 2
    assert week_key(first) != week_key(now)


def test_nothing_is_sent_in_quiet_hours_and_it_is_sent_when_they_end(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _practise(client, world, db, 1, "w1")
    sender = _sender()
    night = _local(db, world, 23)  # 23:00 in the family's zone: inside 21:00 to 07:00
    held = run_weekly(db, night, senders={"email": sender})
    assert held.skipped[world.student_share_id] == "quiet_hours" and sender.sent == []
    morning = run_weekly(db, _local(db, world, 12), senders={"email": sender})
    assert morning.sent == [world.student_share_id]


def test_a_week_without_practice_sends_nothing(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _practise(client, world, db, 30, "old")
    sender = _sender()
    out = run_weekly(db, _local(db, world, 12), senders={"email": sender})
    assert out.skipped[world.student_share_id] == "no_activity" and sender.sent == []


def test_guests_and_families_without_consent_get_nothing(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    client.post(
        f"/students/{world.student_share_id}/consent/revoke",
        headers=auth_header(world.parent_token),
    )
    sender = _sender()
    out = run_weekly(db, _local(db, world, 12), senders={"email": sender})
    assert out.skipped[guest["student_id"]] == "guest"
    assert out.skipped[world.student_share_id] == "no_consent"
    assert sender.sent == []


def test_only_channels_the_profile_allows_are_used(
    client: TestClient,
    world: World,
    db: Session,
    content: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    from app.registries.startup import deployment_jurisdiction_profile as real

    _practise(client, world, db, 1, "w1")

    def none_allowed(pid: str | None = None) -> JurisdictionProfile:
        return replace(real(pid), report_channels=())

    monkeypatch.setattr("app.reports.weekly.deployment_jurisdiction_profile", none_allowed)
    sender = _sender()
    out = run_weekly(db, _local(db, world, 12), senders={"email": sender})
    assert out.skipped[world.student_share_id] == "no_channel" and sender.sent == []

    def sms_only(pid: str | None = None) -> JurisdictionProfile:
        return replace(real(pid), report_channels=("sms",))

    monkeypatch.setattr("app.reports.weekly.deployment_jurisdiction_profile", sms_only)
    out = run_weekly(db, _local(db, world, 12), senders={"email": sender})
    assert out.skipped[world.student_share_id] == "no_channel"  # sms is not built


def test_a_language_without_a_reviewed_text_falls_back_to_english(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _practise(client, world, db, 1, "w1")
    parent = db.scalar(select(UserRow).where(UserRow.email == "parent@example.com"))
    assert parent is not None
    parent.locale = "ne"
    db.commit()
    sender = _sender()
    run_weekly(db, _local(db, world, 12), senders={"email": sender})
    assert sender.sent[0][1] == "Share Kid's week on YourTutor"


def test_the_report_does_not_leak_other_children(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _practise(client, world, db, 1, "w1")
    sender = _sender()
    run_weekly(db, _local(db, world, 12), senders={"email": sender})
    texts: list[Any] = [m[2] for m in sender.sent]
    assert all("Private Kid" not in t for t in texts)
