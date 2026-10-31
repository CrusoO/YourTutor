"""G11: rate limits, the distress pause and flag, PII stripping, and quiet hours in many zones."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import EventRow, SafetyFlagRow, SessionRow, StudentRow, TeacherAlertRow
from app.ratelimit import Limiter, Limits, limiter
from app.registries.quiet_hours import in_quiet_hours
from app.registries.startup import deployment_jurisdiction_profile
from app.safety import is_distress, is_paused, raise_distress, strip_pii
from tests.conftest import World, auth_header

# ---- rate limits ------------------------------------------------------------------------------


def test_the_limiter_counts_per_address_and_group_and_forgets_after_the_window() -> None:
    lim = Limiter(Limits(60, 3, (("/auth/", 2),), ("/health",)))
    assert [lim.check("a", "/auth/x", now=t) for t in (0, 1, 2)] == [None, None, 58]
    assert lim.check("b", "/auth/x", now=2) is None  # another address has its own count
    assert lim.check("a", "/other", now=2) is None  # another group too
    assert lim.check("a", "/auth/x", now=61) is None  # the window has passed
    assert all(lim.check("a", "/health", now=t) is None for t in range(10))  # exempt


def test_the_api_answers_429_with_retry_after_when_a_client_goes_over(client: TestClient) -> None:
    settings.rate_limit_enabled = True
    limiter.reset()
    body = {"curriculum_id": "bhutan", "grade": 9}
    codes = [client.post("/guest/start", json=body).status_code for _ in range(25)]
    assert 429 in codes and codes.index(429) <= 20
    blocked = client.post("/guest/start", json=body)
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) >= 1
    assert client.get("/health").status_code == 200  # health is never limited
    limiter.reset()


def test_a_made_up_forwarded_address_does_not_escape_the_limit(client: TestClient) -> None:
    settings.rate_limit_enabled = True
    settings.trusted_proxies = ""
    limiter.reset()
    body = {"curriculum_id": "bhutan", "grade": 9}
    codes = [
        client.post(
            "/guest/start", json=body, headers={"X-Forwarded-For": f"198.51.100.{i}"}
        ).status_code
        for i in range(25)
    ]
    assert 429 in codes
    limiter.reset()


def test_behind_a_trusted_proxy_each_visitor_has_their_own_limit(client: TestClient) -> None:
    from app.main import app

    settings.rate_limit_enabled = True
    settings.trusted_proxies = "127.0.0.1"
    limiter.reset()
    body = {"curriculum_id": "bhutan", "grade": 9}
    proxied = TestClient(app, client=("127.0.0.1", 50000))  # the proxy's connection
    visitor_a = {"X-Forwarded-For": "198.51.100.1"}
    visitor_b = {"X-Forwarded-For": "198.51.100.2"}
    first = [
        proxied.post("/guest/start", json=body, headers=visitor_a).status_code for _ in range(25)
    ]
    assert 429 in first  # visitor A went over
    assert proxied.post("/guest/start", json=body, headers=visitor_b).status_code != 429
    limiter.reset()


def test_behind_a_proxy_without_the_setting_everyone_shares_one_limit(client: TestClient) -> None:
    from app.main import app

    settings.rate_limit_enabled = True
    settings.trusted_proxies = ""
    limiter.reset()
    body = {"curriculum_id": "bhutan", "grade": 9}
    proxied = TestClient(app, client=("127.0.0.1", 50000))
    for i in range(25):
        proxied.post("/guest/start", json=body, headers={"X-Forwarded-For": f"198.51.100.{i}"})
    other = proxied.post("/guest/start", json=body, headers={"X-Forwarded-For": "192.0.2.1"})
    assert other.status_code == 429  # no uvicorn here: what a proxy without the setting looks like
    assert proxied.get("/ready").json()["forwarded_header_ignored"] is True
    limiter.reset()


# ---- distress ---------------------------------------------------------------------------------


def _student(db: Session, world: World) -> StudentRow:
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    return student


def test_distress_words_are_recognised_and_pii_is_stripped() -> None:
    assert is_distress("I want to die", "en") and not is_distress("I want to dive in", "en")
    cleaned = strip_pii("mail me kid@example.com or +975 17 123 456 or https://x.org/a")
    assert "@" not in cleaned and "975" not in cleaned and "http" not in cleaned


def test_a_distress_flag_pauses_tutoring_ends_the_session_and_alerts_the_teacher(
    client: TestClient, world: World, db: Session
) -> None:
    student = _student(db, world)
    now = datetime.now(UTC)
    db.add(
        SessionRow(
            id=uuid.uuid4(),
            student_id=student.id,
            started_at=now,
            type="practice",
            last_active_at=now,
            plan={},
        )
    )
    db.commit()
    raise_distress(db, student, "ask")
    db.commit()
    assert is_paused(db, student.id)
    assert db.scalars(select(SessionRow).where(SessionRow.ended_at.is_(None))).all() == []
    alert = db.scalars(select(TeacherAlertRow).where(TeacherAlertRow.type == "distress")).one()
    assert alert.student_id == student.id  # the family shared with the teacher
    start = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "practice"},
        headers=auth_header(world.student_token),
    )
    assert start.status_code == 409 and "paused" in start.text
    today = client.get("/students/me/today", headers=auth_header(world.student_token)).json()
    assert today["paused"] is True


def test_the_guardian_sees_the_flag_and_acknowledging_it_lifts_the_pause(
    client: TestClient, world: World, db: Session
) -> None:
    student = _student(db, world)
    flag = raise_distress(db, student, "explain_back")
    db.commit()
    head = auth_header(world.parent_token)
    view = client.get(f"/students/{world.student_share_id}/guardian-view", headers=head).json()
    assert [f["id"] for f in view["safety_flags"]] == [str(flag.id)]
    url = f"/students/{world.student_share_id}/safety-flags/{flag.id}/acknowledge"
    assert client.post(url, headers=auth_header(world.other_parent_token)).status_code == 403
    assert client.post(url, headers=head).status_code == 200
    db.expire_all()
    assert not is_paused(db, student.id)
    alert = db.scalars(select(TeacherAlertRow).where(TeacherAlertRow.type == "distress")).one()
    assert alert.resolved_at is not None


def test_a_flag_that_nobody_acknowledges_stops_pausing_after_a_day(
    db: Session, world: World
) -> None:
    student = _student(db, world)
    flag = raise_distress(db, student, "ask", datetime.now(UTC) - timedelta(hours=25))
    db.commit()
    assert db.get(SafetyFlagRow, flag.id) is not None
    assert not is_paused(db, student.id)


def test_distress_in_an_explain_back_ends_the_session_and_keeps_none_of_the_words(
    client: TestClient, world: World, db: Session
) -> None:
    started = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "practice"},
        headers=auth_header(world.student_token),
    )
    assert started.status_code == 200, started.text
    sid = started.json()["id"]
    res = client.post(
        f"/sessions/{sid}/events",
        json={
            "client_event_id": str(uuid.uuid4()),
            "event_type": "explain_back",
            "payload": {"text": "i want to die, call me on +975 17 123 456"},
        },
        headers=auth_header(world.student_token),
    )
    assert res.status_code == 200, res.text
    assert res.json()["action"]["ended_reason"] == "paused_distress"
    db.expire_all()
    assert is_paused(db, uuid.UUID(world.student_share_id))
    stored = " ".join(str(e.payload) for e in db.scalars(select(EventRow)).all())
    assert "die" not in stored and "975" not in stored


# ---- profile and quiet hours in many zones -----------------------------------------------------

WINDOW_START, WINDOW_END = time(21, 0), time(7, 0)


@pytest.mark.parametrize(
    ("zone", "utc_time", "quiet"),
    [
        ("Asia/Thimphu", (15, 0), True),  # +6: 21:00 local
        ("Asia/Thimphu", (14, 59), False),
        ("Asia/Kathmandu", (15, 14), False),  # +5:45: 20:59 local
        ("Asia/Kathmandu", (15, 15), True),
        ("Asia/Kolkata", (1, 29), True),  # +5:30: 06:59 local
        ("Asia/Kolkata", (1, 30), False),  # 07:00 local
        ("America/St_Johns", (0, 29), False),  # -3:30 in January: 20:59 local
        ("America/St_Johns", (0, 30), True),  # 21:00 local
        ("UTC", (21, 0), True),
        ("UTC", (6, 59), True),
        ("UTC", (7, 0), False),
        ("Pacific/Auckland", (8, 0), False),  # +13 in January: 21:00 local
    ],
)
def test_quiet_hours_follow_the_local_clock_in_each_zone(
    zone: str, utc_time: tuple[int, int], quiet: bool
) -> None:
    profile = deployment_jurisdiction_profile()
    moment = datetime(2026, 1, 15, *utc_time, tzinfo=UTC)
    local = moment.astimezone(ZoneInfo(zone)).time()
    by_hand = local >= WINDOW_START or local < WINDOW_END
    assert in_quiet_hours(moment, ZoneInfo(zone), profile) is by_hand
    if zone == "Pacific/Auckland":
        assert by_hand is True  # 21:00 local is the first quiet minute
    else:
        assert by_hand is quiet, (zone, local)


def test_the_strict_profile_is_the_default_and_keeps_every_scope_and_a_retention_window() -> None:
    profile = deployment_jurisdiction_profile()
    assert profile.id == "default_strict" and settings.jurisdiction_profile == "default_strict"
    assert profile.guest_retention_days == 90
    assert profile.quiet_hours.start == "21:00" and profile.quiet_hours.end == "07:00"
    assert "tutoring" in profile.consent_scopes and "free_text" in profile.consent_scopes
