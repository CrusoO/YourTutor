"""G12: pilot metrics from real events, aggregate only, admin only."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import StudentRow
from app.metrics.pilot import pilot_metrics
from tests.conftest import World, auth_header
from tests.offline.sim import NS, play, seed_content


@pytest.fixture
def played(client: TestClient, world: World, db: Session) -> None:
    seed_content(db)
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    run = play(db, student, steps=40, wrong_every=3, t0=datetime.now(UTC) - timedelta(days=1))
    body = {
        "client_session_id": str(uuid.uuid5(NS, "metrics")),
        "started_at": run["started_at"],
        "events": run["events"],
    }
    assert (
        client.post("/sync/events", json=body, headers=auth_header(world.student_token)).status_code
        == 200
    )


def test_the_metrics_come_from_the_event_log(db: Session, played: None) -> None:
    m = pilot_metrics(db)
    assert m["students_with_practice"] == 1
    mistakes = m["mistakes_with_intervention"]
    assert mistakes["mistakes"] >= 3 and mistakes["share"] == 1.0  # every miss got a response
    assert mistakes["target"] == 0.9
    assert sum(m["diagnosis_mix"].values()) >= 1
    rate = m["unhinted_correct_rate"]
    assert rate["first_answers"] >= 5 and 0 <= rate["share"] <= 1
    assert m["ladder"]["skills_started"] >= 1
    assert m["engagement"]["sessions"] == 1 and m["engagement"]["mean_active_days_last_7"] == 1.0


def test_an_empty_deployment_reports_nothing_without_dividing_by_zero(db: Session) -> None:
    m = pilot_metrics(db)
    assert m["mistakes_with_intervention"]["share"] is None
    assert m["unhinted_correct_rate"]["share"] is None and m["llm"]["fallback_share"] is None


def test_the_report_has_no_names_or_identifiers(db: Session, played: None) -> None:
    text = str(pilot_metrics(db)).lower()
    for word in ("share kid", "private kid", "parent@", "student_id", "display_name", "rank"):
        assert word not in text


def test_only_an_admin_can_read_the_pilot_metrics(
    client: TestClient, world: World, played: None
) -> None:
    url = "/admin/metrics/pilot"
    assert client.get(url, headers=auth_header(world.admin_token)).status_code == 200
    for token in (world.parent_token, world.teacher_token, world.student_token):
        assert client.get(url, headers=auth_header(token)).status_code == 403
    assert client.get(url).status_code == 401
