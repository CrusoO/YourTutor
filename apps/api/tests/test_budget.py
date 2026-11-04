"""Spending limits: the day's model budget and the video queue."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.budget import DailyBudget, llm_budget, video_jobs_today, video_queue_full
from app.config import settings
from app.db.models import VideoJobRow
from tests.conftest import World, auth_header


def test_the_daily_budget_counts_then_refuses_and_starts_again_tomorrow() -> None:
    budget = DailyBudget()
    day1 = datetime(2026, 11, 4, 9, tzinfo=UTC)
    assert [budget.charge(2, day1) for _ in range(3)] == [True, True, False]
    assert budget.used() == 2
    assert budget.charge(2, day1 + timedelta(days=1)) is True  # a new UTC day


def test_a_limit_of_zero_means_no_limit() -> None:
    budget = DailyBudget()
    assert all(budget.charge(0) for _ in range(50))
    assert budget.used() == 0


def _job(student_id: uuid.UUID, status: str = "queued", hours_ago: float = 0) -> VideoJobRow:
    return VideoJobRow(
        id=uuid.uuid4(),
        student_id=student_id,
        node_id="n",
        request_json={},
        idempotency_key=str(uuid.uuid4()),
        status=status,
        events=[],
        created_at=now_utc() - timedelta(hours=hours_ago),
    )


def test_the_queue_counts_only_waiting_jobs(world: World, db: Session) -> None:
    student = uuid.UUID(world.student_share_id)
    db.add_all([_job(student), _job(student), _job(student, status="done")])
    db.commit()
    assert video_queue_full(db, 2) and not video_queue_full(db, 3)
    assert not video_queue_full(db, 0)  # off


def test_a_learners_jobs_today_ignore_older_ones(world: World, db: Session) -> None:
    student = uuid.UUID(world.student_share_id)
    db.add_all([_job(student), _job(student, hours_ago=30)])
    db.commit()
    assert video_jobs_today(db, student) == 1


@pytest.fixture
def budget_reset() -> Any:
    llm_budget.reset()
    yield
    llm_budget.reset()


def test_the_model_endpoints_say_busy_once_the_daily_budget_is_spent(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch, budget_reset: Any
) -> None:
    monkeypatch.setattr(settings, "llm_daily_cap", 1)
    head = auth_header(world.student_token)
    first = client.post("/explain/lesson/opening", json={"prompt": "tides"}, headers=head)
    second = client.post("/explain/lesson/opening", json={"prompt": "tides"}, headers=head)
    assert first.json().get("reason") != "daily_limit"
    assert second.json() == {"kind": "unavailable", "reason": "daily_limit"}
    for path in ("/explain", "/explain/lesson", "/explain/story"):
        assert client.post(path, json={"prompt": "tides"}, headers=head).json()["reason"] == (
            "daily_limit"
        )


def test_a_full_queue_and_a_daily_video_limit_are_refused_plainly(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    student = uuid.UUID(world.student_share_id)
    db.add(_job(student))
    db.commit()
    body = {"idempotency_key": str(uuid.uuid4()), "node_id": "cbse.10.maths.ch02.s2_3"}
    head = auth_header(world.student_token)
    monkeypatch.setattr(settings, "video_queue_max", 1)
    assert client.post("/video-jobs", json=body, headers=head).status_code == 503
    monkeypatch.setattr(settings, "video_queue_max", 0)
    monkeypatch.setattr(settings, "video_jobs_per_day", 1)
    again = {**body, "idempotency_key": str(uuid.uuid4())}
    assert client.post("/video-jobs", json=again, headers=head).status_code == 429
