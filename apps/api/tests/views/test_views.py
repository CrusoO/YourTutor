"""G10: guardian and teacher views from real events: no rankings, shared students only."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ClassMembershipRow,
    LlmCallRow,
    SessionRow,
    StudentRow,
    TeacherAlertRow,
    UserRow,
)
from tests.conftest import World, auth_header
from tests.offline.sim import NS, play, seed_content


@pytest.fixture
def content(db: Session) -> None:
    seed_content(db)


def _student(db: Session, world: World, which: str = "share") -> StudentRow:
    sid = world.student_share_id if which == "share" else world.student_noshare_id
    student = db.get(StudentRow, uuid.UUID(sid))
    assert student is not None
    return student


def _sync(client: TestClient, world: World, played: dict[str, Any], name: str):
    body = {
        "client_session_id": str(uuid.uuid5(NS, name)),
        "started_at": played["started_at"],
        "events": played["events"],
    }
    res = client.post("/sync/events", json=body, headers=auth_header(world.student_token))
    assert res.status_code == 200, res.text
    return res.json()


def _days_ago(days: float) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def _practise(
    client: TestClient,
    world: World,
    db: Session,
    name: str,
    *,
    days_ago: float = 2,
    steps: int = 40,
    wrong_every: int = 4,
    wrong_response: str = "999",
    help_at: int | None = 5,
):
    played = play(
        db,
        _student(db, world),
        steps=steps,
        wrong_every=wrong_every,
        t0=_days_ago(days_ago),
        wrong_response=wrong_response,
        help_at=help_at,
    )
    return _sync(client, world, played, name)


# ---- guardian -------------------------------------------------------------------------------


def test_the_guardian_sees_progress_and_what_was_learned_this_week_from_real_events(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _practise(client, world, db, "week")
    res = client.get(
        f"/students/{world.student_share_id}/guardian-view", headers=auth_header(world.parent_token)
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["student"]["display_name"] == "Share Kid"
    week = body["this_week"]
    assert week["sessions"] == 1 and week["questions_answered"] >= 3
    assert week["days_active"] == 1 and week["active_minutes"] >= 0
    assert week["learned"], "a skill should have moved up this week"
    first = week["learned"][0]
    assert first["from_level"] == 0 and first["to_level"] >= 1
    assert first["skill_id"] in {"OFF.S1", "OFF.S2"}
    assert body["skills_started"] >= 1
    chapter = next(c for c in body["chapters"] if c["live"])
    assert {s["id"] for s in chapter["skills"]} == {"OFF.S1", "OFF.S2"}
    assert any(s["level"] >= 1 for s in chapter["skills"])


def test_a_week_with_no_practice_reads_as_nothing_this_week(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _practise(client, world, db, "old", days_ago=30)
    week = client.get(
        f"/students/{world.student_share_id}/guardian-view", headers=auth_header(world.parent_token)
    ).json()["this_week"]
    assert week["sessions"] == 0 and week["learned"] == [] and week["questions_answered"] == 0


def test_there_is_nothing_that_ranks_scores_or_compares_children(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _practise(client, world, db, "norank")
    text = client.get(
        f"/students/{world.student_share_id}/guardian-view", headers=auth_header(world.parent_token)
    ).text.lower()
    for word in ("rank", "percentile", "score", "streak", "leaderboard", "class average", "behind"):
        assert word not in text, word


def test_only_the_guardian_or_an_admin_can_open_a_guardian_view(
    client: TestClient, world: World, content: None
) -> None:
    url = f"/students/{world.student_share_id}/guardian-view"
    assert client.get(url, headers=auth_header(world.parent_token)).status_code == 200
    assert client.get(url, headers=auth_header(world.admin_token)).status_code == 200
    for token in (world.other_parent_token, world.teacher_token, world.student_token):
        assert client.get(url, headers=auth_header(token)).status_code == 403
    assert client.get(url).status_code == 401


def test_the_guardian_can_switch_the_language_of_the_view_and_of_the_child(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    url = f"/students/{world.student_share_id}/guardian-view"
    ne = client.get(url, params={"lang": "ne"}, headers=auth_header(world.parent_token)).json()
    assert ne["language"] == "ne"  # texts without a reviewed translation fall back to English
    put = client.put(
        f"/students/{world.student_share_id}/language",
        json={"home_language": "ne"},
        headers=auth_header(world.parent_token),
    )
    assert put.status_code == 200 and put.json()["home_language"] == "ne"
    db.expire_all()
    assert _student(db, world).home_language == "ne"
    other = client.put(
        f"/students/{world.student_share_id}/language",
        json={"home_language": "en"},
        headers=auth_header(world.other_parent_token),
    )
    assert other.status_code == 403
    bad = client.put(
        f"/students/{world.student_share_id}/language",
        json={"home_language": "zz"},
        headers=auth_header(world.parent_token),
    )
    assert bad.status_code in (400, 422)


def test_the_guardian_can_still_export_and_delete(
    client: TestClient, world: World, content: None
) -> None:
    assert (
        client.get("/parents/me/export", headers=auth_header(world.parent_token)).status_code == 200
    )
    assert client.delete("/parents/me", headers=auth_header(world.parent_token)).status_code == 200


# ---- teacher --------------------------------------------------------------------------------


def _members(db: Session, world: World) -> None:
    rows = db.scalars(
        select(ClassMembershipRow).where(ClassMembershipRow.class_id == uuid.UUID(world.class_id))
    ).all()
    assert len(rows) == 2  # the shared and the unshared child are both in the class


def test_the_heatmap_shows_ladder_levels_for_shared_students_only(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _members(db, world)
    _practise(client, world, db, "heat")
    res = client.get(
        f"/teacher/classes/{world.class_id}/heatmap", headers=auth_header(world.teacher_token)
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert [s["display_name"] for s in body["students"]] == ["Share Kid"]
    assert "Private Kid" not in res.text and world.student_noshare_id not in res.text
    assert {s["id"] for s in body["skills"]} == {"OFF.S1", "OFF.S2"}
    row = body["students"][0]["levels"]
    assert row["OFF.S1"] >= 1
    assert body["levels"] == list(range(8))
    assert sum(body["counts"]["OFF.S1"].values()) == 1  # one visible student, counted once


def test_the_heatmap_lists_students_alphabetically_not_by_how_they_are_doing(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    other = _student(db, world, "noshare")
    other.display_name = "Aaron"
    client.post(
        f"/students/{world.student_noshare_id}/consent",
        json={"version": "v2", "scopes": ["tutoring", "teacher_share"]},
        headers=auth_header(world.parent_token),
    )
    db.commit()
    _practise(client, world, db, "alpha")
    names = [
        s["display_name"]
        for s in client.get(
            f"/teacher/classes/{world.class_id}/heatmap", headers=auth_header(world.teacher_token)
        ).json()["students"]
    ]
    assert names == ["Aaron", "Share Kid"]  # Share Kid has done more, and still comes second


def test_a_teacher_cannot_see_a_student_without_teacher_share_anywhere(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    hidden = _student(db, world, "noshare")
    now = datetime.now(UTC)
    db.add(
        TeacherAlertRow(
            id=uuid.uuid4(),
            student_id=hidden.id,
            skill_id="OFF.S1",
            type="wheel_spinning",
            created_at=now,
        )
    )
    db.add(
        SessionRow(
            id=uuid.uuid4(),
            student_id=hidden.id,
            started_at=now,
            type="practice",
            last_active_at=now,
            plan={"phase": "stuck", "current_skill": "OFF.S1"},
        )
    )
    db.commit()
    head = auth_header(world.teacher_token)
    for view in ("heatmap", "stuck", "alerts"):
        res = client.get(f"/teacher/classes/{world.class_id}/{view}", headers=head)
        assert res.status_code == 200
        assert "Private Kid" not in res.text and world.student_noshare_id not in res.text, view
    admin = client.get(
        f"/teacher/classes/{world.class_id}/alerts", headers=auth_header(world.admin_token)
    )
    assert "Private Kid" in admin.text  # an admin sees every member


def test_stuck_now_lists_students_waiting_at_the_help_picker(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    played = play(db, _student(db, world), steps=3, t0=datetime.now(UTC) - timedelta(minutes=2))
    played["events"] = played["events"][:2]
    ask: dict[str, Any] = {
        "client_event_id": str(uuid.uuid5(NS, "ask")),
        "event_type": "request_help",
        "at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        "item_id": None,
        "payload": {},
    }
    played["events"].append(ask)
    _sync(client, world, played, "stuck")
    res = client.get(
        f"/teacher/classes/{world.class_id}/stuck", headers=auth_header(world.teacher_token)
    ).json()
    assert [s["display_name"] for s in res["students"]] == ["Share Kid"]
    assert res["students"][0]["phase"] in {"stuck", "practice"}


def test_wheel_spinning_and_repeated_misconception_alerts_appear_and_resolve_at_level_4(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    _practise(
        client, world, db, "struggle", days_ago=3, steps=60, wrong_every=1, wrong_response="77"
    )
    head = auth_header(world.teacher_token)
    alerts = client.get(f"/teacher/classes/{world.class_id}/alerts", headers=head).json()["alerts"]
    kinds = {a["type"] for a in alerts}
    assert "wheel_spinning" in kinds and "repeated_misconception" in kinds
    assert all(a["display_name"] == "Share Kid" and a["label"] for a in alerts)
    # fresh sessions of correct answers bring the skill to level 4: the alerts close
    levels: dict[str, int] = {}
    for index in range(8):
        _practise(
            client,
            world,
            db,
            f"recover{index}",
            days_ago=2.5 - index * 0.25,
            steps=60,
            wrong_every=1000,
        )
        levels = client.get(f"/teacher/classes/{world.class_id}/heatmap", headers=head).json()[
            "students"
        ][0]["levels"]
        if levels["OFF.S1"] >= 4:
            break
    assert levels["OFF.S1"] >= 4, levels
    after = client.get(f"/teacher/classes/{world.class_id}/alerts", headers=head).json()["alerts"]
    assert not [a for a in after if a["skill_id"] == "OFF.S1"]


def test_only_teachers_of_the_class_and_admins_can_open_class_views(
    client: TestClient, world: World, content: None
) -> None:
    for view in ("heatmap", "stuck", "alerts"):
        url = f"/teacher/classes/{world.class_id}/{view}"
        assert client.get(url, headers=auth_header(world.teacher_token)).status_code == 200
        assert client.get(url, headers=auth_header(world.admin_token)).status_code == 200
        for token in (world.parent_token, world.student_token, world.comparison_token):
            assert client.get(url, headers=auth_header(token)).status_code == 403, view


# ---- review queue ---------------------------------------------------------------------------


def _sampled(db: Session, student: StudentRow, text: str) -> uuid.UUID:
    now = datetime.now(UTC)
    session = SessionRow(
        id=uuid.uuid4(),
        student_id=student.id,
        started_at=now,
        type="practice",
        last_active_at=now,
        plan={},
    )
    db.add(session)
    db.flush()
    call = LlmCallRow(
        id=uuid.uuid4(),
        created_at=now,
        session_id=session.id,
        purpose="personalise_hint",
        prompt_version="v1",
        band_id="lower_secondary",
        language="en",
        outcome="llm",
        sampled=True,
        output_text=text,
        review_status="pending",
    )
    db.add(call)
    db.commit()
    return call.id


def test_the_review_queue_holds_sampled_ai_replies_of_shared_students_and_nobody_elses(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    visible = _sampled(db, _student(db, world), "Think about what undoes the plus.")
    hidden = _sampled(db, _student(db, world, "noshare"), "A secret about Private Kid.")
    head = auth_header(world.teacher_token)
    items = client.get("/teacher/review-queue", headers=head).json()["items"]
    assert [i["id"] for i in items] == [str(visible)]
    assert items[0]["text"].startswith("Think about") and items[0]["display_name"] == "Share Kid"
    assert (
        client.post(
            f"/teacher/review-queue/{hidden}", json={"decision": "ok"}, headers=head
        ).status_code
        == 404
    )
    done = client.post(f"/teacher/review-queue/{visible}", json={"decision": "bad"}, headers=head)
    assert done.status_code == 200 and done.json()["review_status"] == "bad"
    assert client.get("/teacher/review-queue", headers=head).json()["items"] == []
    admin = client.get("/teacher/review-queue", headers=auth_header(world.admin_token)).json()
    assert [i["id"] for i in admin["items"]] == [str(hidden)]
    assert client.post(
        f"/teacher/review-queue/{visible}", json={"decision": "meh"}, headers=head
    ).status_code in (404, 422)


def test_a_student_or_parent_cannot_read_the_review_queue(
    client: TestClient, world: World, content: None
) -> None:
    for token in (world.parent_token, world.student_token):
        assert client.get("/teacher/review-queue", headers=auth_header(token)).status_code == 403


def test_users_exist_for_the_roles_used_here(db: Session, world: World) -> None:
    roles = {u.role for u in db.scalars(select(UserRow)).all()}
    assert {"parent", "teacher", "admin"} <= roles
