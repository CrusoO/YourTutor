"""G2: a session can be resumed only until local midnight in the student's time zone."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import SessionRow, StudentRow
from app.dev.clock import frozen
from app.orchestrator.policy import IDLE_END_MS
from app.registries.timezone import same_local_day
from tests.conftest import World, auth_header
from tests.learner.test_chapters import chapters_world  # noqa: F401  (fixture)
from tests.player.test_resume_idle import idle_world  # noqa: F401  (fixture)

THIMPHU = "Asia/Thimphu"  # UTC+6: local midnight is 18:00 UTC
DAY = datetime(2026, 10, 7, tzinfo=UTC)


def at(hour: int, minute: int = 0, *, days: int = 0) -> datetime:
    return DAY + timedelta(days=days, hours=hour, minutes=minute)


# ---- pure ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "b", "tz", "same"),
    [
        (at(17, 59), at(17, 59, days=0), THIMPHU, True),
        (at(17, 59), at(18, 0), THIMPHU, False),  # exactly local midnight is the next day
        (at(18, 0), at(23, 59), THIMPHU, True),
        (at(17, 59), at(18, 1), "UTC", True),
        (at(23, 59), at(0, 1, days=1), "UTC", False),
        (at(0, 0), at(23, 59), "UTC", True),
        (at(20, 0), at(2, 0, days=1), "America/New_York", True),  # 16:00 and 22:00 local
    ],
)
def test_same_local_day(a: datetime, b: datetime, tz: str, same: bool) -> None:
    assert same_local_day(a, b, tz) is same


def test_same_local_day_is_symmetric_and_falls_back_to_utc_for_unknown_zones() -> None:
    assert same_local_day(at(1), at(2), "Not/AZone") is True
    assert same_local_day(at(1), at(2), THIMPHU) == same_local_day(at(2), at(1), THIMPHU)


# ---- through the API ----------------------------------------------------------------------


def _set_zone(db: Session, world: World, zone: str) -> None:
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    student.timezone = zone
    db.commit()


def _start(client: TestClient, world: World) -> dict:
    response = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "practice", "chapter_id": "CH.ONE"},
        headers=auth_header(world.student_token),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _idle(client: TestClient, world: World, session_id: str) -> None:
    sent = client.post(
        f"/sessions/{session_id}/events",
        json={
            "client_event_id": str(uuid.uuid4()),
            "event_type": "idle_nudge",
            "payload": {"idle_ms": IDLE_END_MS + 1},
        },
        headers=auth_header(world.student_token),
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["action"]["type"] == "end_session"


def _today(client: TestClient, world: World) -> dict:
    return client.get("/students/me/today", headers=auth_header(world.student_token)).json()


@pytest.fixture
def thimphu(db: Session, idle_world: World) -> World:  # noqa: F811
    settings.allow_draft_content = True
    _set_zone(db, idle_world, THIMPHU)
    return idle_world


def test_resume_is_offered_before_local_midnight(client: TestClient, thimphu: World) -> None:
    with frozen(at(17, 40)):
        started = _start(client, thimphu)
        _idle(client, thimphu, started["id"])
    with frozen(at(17, 59)):
        assert _today(client, thimphu)["resume"]["session_id"] == started["id"]
        again = _start(client, thimphu)
    assert again["id"] == started["id"]


def test_resume_is_not_offered_after_local_midnight(
    client: TestClient, db: Session, thimphu: World
) -> None:
    with frozen(at(17, 40)):
        started = _start(client, thimphu)
        _idle(client, thimphu, started["id"])
    with frozen(at(18, 1)):
        assert _today(client, thimphu)["resume"] is None
        fresh = _start(client, thimphu)
    assert fresh["id"] != started["id"]
    db.expire_all()
    old = db.get(SessionRow, uuid.UUID(started["id"]))
    assert old is not None
    assert old.resumable is False
    assert old.ended_reason == "day_rollover"


def test_the_same_instant_is_still_today_in_a_zone_where_it_is_before_midnight(
    client: TestClient,
    db: Session,
    idle_world: World,  # noqa: F811
) -> None:
    settings.allow_draft_content = True
    _set_zone(db, idle_world, "UTC")
    with frozen(at(17, 40)):
        started = _start(client, idle_world)
        _idle(client, idle_world, started["id"])
    with frozen(at(18, 1)):
        assert _today(client, idle_world)["resume"]["session_id"] == started["id"]


def test_an_open_session_from_yesterday_is_closed_and_a_new_one_starts(
    client: TestClient, db: Session, thimphu: World
) -> None:
    with frozen(at(17, 40)):
        started = _start(client, thimphu)
    with frozen(at(19, 0)):
        assert _today(client, thimphu)["resume"] is None
        fresh = _start(client, thimphu)
    assert fresh["id"] != started["id"]
    db.expire_all()
    old = db.get(SessionRow, uuid.UUID(started["id"]))
    assert old is not None and old.ended_at is not None
    assert old.ended_reason == "day_rollover"


def test_opening_an_expired_idle_session_shows_the_end_screen_instead_of_reopening(
    client: TestClient, db: Session, thimphu: World
) -> None:
    with frozen(at(17, 40)):
        started = _start(client, thimphu)
        _idle(client, thimphu, started["id"])
    with frozen(at(18, 30)):
        opened = client.get(
            f"/sessions/{started['id']}", headers=auth_header(thimphu.student_token)
        )
    assert opened.json()["action"]["type"] == "end_session"
    db.expire_all()
    row = db.get(SessionRow, uuid.UUID(started["id"]))
    assert row is not None and row.resumable is False


def test_progress_carries_over_to_the_new_day(client: TestClient, thimphu: World) -> None:
    with frozen(at(17, 40)):
        started = _start(client, thimphu)
        _idle(client, thimphu, started["id"])
    with frozen(at(19, 0)):
        fresh = _start(client, thimphu)
    assert fresh["action"]["type"] in {"predict", "show_item", "warmup_item"}


def test_same_day_resume_still_works_across_the_whole_day(
    client: TestClient, thimphu: World
) -> None:
    with frozen(at(0, 5)):  # 06:05 local
        started = _start(client, thimphu)
        _idle(client, thimphu, started["id"])
    with frozen(at(17, 55)):  # 23:55 local, same day
        assert _today(client, thimphu)["resume"]["session_id"] == started["id"]
