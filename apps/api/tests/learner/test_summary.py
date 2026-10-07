"""S1b Done screen: learned, skill statuses, next step, minutes left (no streaks or ranks)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.learner.summary import done_summary
from tests.conftest import World, auth_header
from tests.learner.test_chapters import _mastery, chapters_world  # noqa: F401  (fixtures)

PATH = [
    {"id": "A", "title": "Skill A", "level": 4, "status": "can_do_it", "current": False},
    {"id": "B", "title": "Skill B", "level": 2, "status": "learning", "current": True},
    {"id": "C", "title": "Skill C", "level": 0, "status": "not_started", "current": False},
]


def test_learned_lists_only_skills_that_went_up_this_session() -> None:
    out = done_summary(PATH, start_levels={"A": 3, "B": 2}, touched=["A", "B"], remaining=12)
    assert [row["id"] for row in out["learned"]] == ["A"]
    assert out["learned"][0]["status"] == "can_do_it"


def test_practised_lists_touched_skills_in_path_order_once() -> None:
    out = done_summary(PATH, start_levels={}, touched=["B", "A", "B"], remaining=12)
    assert [row["id"] for row in out["practised"]] == ["A", "B"]


def test_next_is_the_current_skill_with_its_title() -> None:
    out = done_summary(PATH, start_levels={}, touched=[], remaining=12)
    assert out["next"] == {"id": "B", "title": "Skill B"}


def test_next_is_none_when_every_skill_is_can_do_it() -> None:
    done = [{**row, "level": 5, "status": "can_do_it", "current": False} for row in PATH]
    assert done_summary(done, start_levels={}, touched=[], remaining=3)["next"] is None


def test_every_skill_status_is_listed_and_minutes_are_carried() -> None:
    out = done_summary(PATH, start_levels={}, touched=[], remaining=7)
    assert [(row["id"], row["status"]) for row in out["skills"]] == [
        ("A", "can_do_it"),
        ("B", "learning"),
        ("C", "not_started"),
    ]
    assert out["remaining_active_minutes"] == 7


def test_no_streaks_ranks_or_scores() -> None:
    out = done_summary(PATH, start_levels={}, touched=["A"], remaining=1)
    blob = str(out).lower()
    for word in ("streak", "rank", "score", "points", "leaderboard", "xp"):
        assert word not in blob


def test_a_new_skill_with_no_start_level_counts_as_learned_when_it_has_a_level() -> None:
    out = done_summary(PATH, start_levels={}, touched=["A"], remaining=1)
    assert [row["id"] for row in out["learned"]] == ["A", "B"]


# ---- through the API ---------------------------------------------------------------------


def test_chapter_complete_session_carries_the_summary(
    client: TestClient,
    db: Session,
    chapters_world: World,  # noqa: F811
) -> None:
    _mastery(db, chapters_world, "SK.A", 7)
    _mastery(db, chapters_world, "SK.B", 7)
    response = client.post(
        "/sessions",
        json={
            "student_id": chapters_world.student_share_id,
            "type": "practice",
            "chapter_id": "CH.ONE",
        },
        headers=auth_header(chapters_world.student_token),
    )
    assert response.status_code == 200, response.text
    action = response.json()["action"]
    assert action["type"] == "end_session"
    summary = action["extras"]["summary"]
    assert summary["chapter"] == {"id": "CH.ONE", "title": "Chapter one", "status": "solid"}
    assert [row["id"] for row in summary["skills"]] == ["SK.A", "SK.B"]
    assert summary["learned"] == []
    assert summary["next"] is None
    assert isinstance(summary["remaining_active_minutes"], int)
    assert summary["recommended_chapter"] == "CH.TWO"


def test_the_summary_is_only_on_end_session(
    client: TestClient,
    chapters_world: World,  # noqa: F811
) -> None:
    response = client.post(
        "/sessions",
        json={"student_id": chapters_world.student_share_id, "type": "practice"},
        headers=auth_header(chapters_world.student_token),
    )
    action = response.json()["action"]
    assert action["type"] != "end_session"
    assert "summary" not in (action.get("extras") or {})
    assert uuid.UUID(response.json()["id"])
