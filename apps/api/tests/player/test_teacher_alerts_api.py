"""G2b: wheel-spinning writes a teacher alert row only with the teacher_share scope."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.db.models import ConsentRow, MasteryRow, TeacherAlertRow
from tests.conftest import World
from tests.learner.test_chapters import chapters_world  # noqa: F401  (fixture)
from tests.player.test_stuck_picker_api import Play, _full_item

SKILL = "SK.A"


@pytest.fixture
def alert_world(db: Session, chapters_world: World) -> World:  # noqa: F811
    for n in range(1, 6):
        db.add(_full_item(f"AL.{n}", str(5 + n)))
    db.commit()
    return chapters_world


def _scopes(db: Session, world: World, scopes: list[str]) -> None:
    for row in db.scalars(
        select(ConsentRow).where(ConsentRow.student_id == uuid.UUID(world.student_share_id))
    ):
        row.scopes = scopes
    db.commit()


def _alerts(db: Session, world: World) -> list[TeacherAlertRow]:
    db.expire_all()
    return list(
        db.scalars(
            select(TeacherAlertRow).where(
                TeacherAlertRow.student_id == uuid.UUID(world.student_share_id)
            )
        )
    )


def _fail_three_items(play: Play) -> None:
    """A non-learner: wrong on the first attempt of three different items."""
    seen: set[str] = set()
    for _ in range(40):
        action = play.action
        if action["type"] in {"show_item", "similar_item", "hint", "check_your_work"}:
            if action.get("extras", {}).get("probe"):
                break
            seen.add(str(action["item_id"]))
            play.send("answer", response="999999", latency_ms=9000)
        elif action["type"] == "reveal_solution":
            play.send("continue")
        elif action["type"] in {"ask_stuck_point", "ask_stuck_step"}:
            play.send("stuck_choice", choice="start")
        else:
            break
        if len(seen) >= 3 and play.action["type"] != "hint":
            pass


def test_a_wheel_spinning_student_with_teacher_share_gets_one_alert_row(
    client: TestClient, db: Session, alert_world: World
) -> None:
    _scopes(db, alert_world, ["tutoring", "teacher_share"])
    play = Play(client, alert_world)
    _fail_three_items(play)
    rows = _alerts(db, alert_world)
    assert [(r.skill_id, r.type) for r in rows] == [(SKILL, "wheel_spinning")]
    assert rows[0].resolved_at is None


def test_no_alert_row_without_the_teacher_share_scope(
    client: TestClient, db: Session, alert_world: World
) -> None:
    _scopes(db, alert_world, ["tutoring"])
    play = Play(client, alert_world)
    _fail_three_items(play)
    assert _alerts(db, alert_world) == []


def test_the_student_is_still_probed_or_helped_without_the_scope(
    client: TestClient, db: Session, alert_world: World
) -> None:
    _scopes(db, alert_world, ["tutoring"])
    play = Play(client, alert_world)
    _fail_three_items(play)
    assert play.action["type"] in {"show_item", "worked_example", "hint", "reveal_solution"}


def test_a_second_session_does_not_duplicate_the_open_alert(
    client: TestClient, db: Session, alert_world: World
) -> None:
    _scopes(db, alert_world, ["tutoring", "teacher_share"])
    _fail_three_items(Play(client, alert_world))
    db.expire_all()
    first_session = Play(client, alert_world)
    assert first_session.session_id
    assert len(_alerts(db, alert_world)) == 1


def test_the_alert_resolves_when_the_skill_reaches_level_4(
    client: TestClient, db: Session, alert_world: World
) -> None:
    _scopes(db, alert_world, ["tutoring", "teacher_share"])
    play = Play(client, alert_world)
    _fail_three_items(play)
    assert _alerts(db, alert_world)[0].resolved_at is None
    row = db.get(MasteryRow, (uuid.UUID(alert_world.student_share_id), SKILL))
    assert row is not None
    row.ladder_level = 4
    row.ladder_evidence = {"4": ["e1"]}
    row.ladder_memory = {}
    row.last_updated = now_utc()
    db.commit()
    play.send("nudge") if False else None
    play.send("idle_nudge", idle_ms=1000)
    alerts = _alerts(db, alert_world)
    assert alerts and alerts[0].resolved_at is not None


def _unused(_: Any) -> None:
    return None
