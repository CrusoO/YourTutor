"""S1b: chapter map and skill path. Status derivation, one recommendation, coming soon."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.config import settings
from app.db.models import (
    BookRow,
    ChapterRow,
    MasteryRow,
    OverlayRow,
    ReviewCardRow,
    SkillRow,
    StudentRow,
)
from app.learner.chapters import ChapterSummary, recommend_chapter, skill_path
from app.learner.status import (
    CAN_DO_IT,
    LEARNING,
    NOT_STARTED,
    REVIEW_DUE,
    SOLID,
    chapter_status,
    skill_status,
)
from tests.conftest import World, auth_header

# ---- pure -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("level", "overdue", "expected"),
    [
        (0, False, NOT_STARTED),
        (1, False, LEARNING),
        (3, False, LEARNING),
        (4, False, CAN_DO_IT),
        (6, False, CAN_DO_IT),
        (7, False, SOLID),
        (4, True, REVIEW_DUE),
        (7, True, REVIEW_DUE),
        (2, True, LEARNING),
        (0, True, NOT_STARTED),
    ],
)
def test_skill_status_for_each_state(level: int, overdue: bool, expected: str) -> None:
    assert skill_status(level, review_overdue=overdue) == expected


def test_chapter_status_is_the_weakest_skill_or_review_due() -> None:
    assert chapter_status([SOLID, CAN_DO_IT]) == CAN_DO_IT
    assert chapter_status([SOLID, LEARNING, NOT_STARTED]) == NOT_STARTED
    assert chapter_status([SOLID, REVIEW_DUE]) == REVIEW_DUE
    assert chapter_status([]) == NOT_STARTED


def _summary(chapter_id: str, status: str, *, live: bool = True) -> ChapterSummary:
    return ChapterSummary(id=chapter_id, title=chapter_id, live=live, status=status)


def test_recommendation_is_the_first_live_chapter_that_is_not_solid() -> None:
    rows = [_summary("a", SOLID), _summary("b", LEARNING), _summary("c", NOT_STARTED)]
    assert recommend_chapter(rows) == "b"


def test_recommendation_skips_coming_soon_and_is_always_exactly_one() -> None:
    rows = [_summary("a", "coming_soon", live=False), _summary("b", NOT_STARTED)]
    assert recommend_chapter(rows) == "b"
    all_solid = [_summary("a", SOLID), _summary("b", SOLID)]
    assert recommend_chapter(all_solid) == "a"  # revisit the first one
    assert recommend_chapter([_summary("a", "coming_soon", live=False)]) is None


def test_review_due_chapter_is_recommended_before_a_later_not_started_one() -> None:
    rows = [_summary("a", REVIEW_DUE), _summary("b", NOT_STARTED)]
    assert recommend_chapter(rows) == "a"


def test_skill_path_unlocks_the_next_skill_when_the_previous_is_can_do_it() -> None:
    rows = skill_path([("S1", 0, False), ("S2", 0, False), ("S3", 0, False)])
    assert [r["unlocked"] for r in rows] == [True, False, False]
    assert [r["current"] for r in rows] == [True, False, False]
    rows = skill_path([("S1", 4, False), ("S2", 2, False), ("S3", 0, False)])
    assert [r["unlocked"] for r in rows] == [True, True, False]
    assert [r["current"] for r in rows] == [False, True, False]
    assert [r["status"] for r in rows] == [CAN_DO_IT, LEARNING, NOT_STARTED]


def test_skill_path_review_due_shows_review_due() -> None:
    rows = skill_path([("S1", 5, True)])
    assert rows[0]["status"] == REVIEW_DUE


# ---- API --------------------------------------------------------------------------------

BOOK = "BK.CHAPTERS"


def _skill(db: Session, skill_id: str, title: str, prereq: list[str] | None = None) -> None:
    db.add(
        SkillRow(
            id=skill_id,
            title={"en": title, "ne": None},
            grade_band=[9],
            subject="math",
            prerequisites=prereq or [],
            related=[],
            misconceptions=[],
            bkt={"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
            status="approved",
        )
    )


@pytest.fixture
def chapters_world(db: Session, world: World) -> World:
    settings.allow_draft_content = False
    for sid in ("SK.A", "SK.B", "SK.C"):
        _skill(db, sid, f"Skill {sid}")
    db.add(BookRow(id=BOOK, curriculum_id="bhutan", grade=9, default_chapter_id="CH.ONE"))
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    student.book_id = BOOK
    db.flush()
    spec = [
        ("CH.ONE", "OV.ONE", {"en": "Chapter one", "ne": "अध्याय एक"}, 1, ["SK.A", "SK.B"], True),
        ("CH.TWO", "OV.TWO", {"en": "Chapter two"}, 2, ["SK.C"], True),
        ("CH.SOON", "OV.SOON", {"en": "Chapter three"}, 3, [], False),
        ("CH.DRAFT", "OV.DRAFT", {"en": "Chapter four"}, 4, ["SK.C"], False),
    ]
    for chapter_id, overlay_id, titles, position, skills, live in spec:
        db.add(
            OverlayRow(
                id=overlay_id,
                curriculum_id="bhutan",
                grade=9,
                chapter=chapter_id.lower(),
                skill_ids=skills,
                live=live,
            )
        )
        db.add(
            ChapterRow(
                id=chapter_id,
                book_id=BOOK,
                overlay_id=overlay_id,
                chapter_key=chapter_id.lower(),
                titles=titles,
                position=position,
            )
        )
    db.commit()
    return world


def _mastery(db: Session, world: World, skill: str, level: int, due_in_days: int | None = None):
    sid = uuid.UUID(world.student_share_id)
    db.add(
        MasteryRow(
            student_id=sid,
            skill_id=skill,
            p_known=0.5,
            attempts=3,
            unhinted_correct=1,
            hinted_correct=0,
            last_updated=now_utc(),
            ladder_level=level,
        )
    )
    if due_in_days is not None:
        db.add(
            ReviewCardRow(
                student_id=sid,
                skill_id=skill,
                fsrs_state={},
                due_at=now_utc() + timedelta(days=due_in_days),
            )
        )
    db.commit()


def _chapters(client: TestClient, world: World, token: str | None = None) -> dict:
    response = client.get(
        f"/students/{world.student_share_id}/chapters",
        headers=auth_header(token or world.student_token),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_chapter_list_has_titles_status_and_exactly_one_recommendation(
    client: TestClient, chapters_world: World
) -> None:
    body = _chapters(client, chapters_world)
    rows = body["chapters"]
    assert [r["id"] for r in rows] == ["CH.ONE", "CH.TWO", "CH.SOON", "CH.DRAFT"]
    assert [r["title"] for r in rows] == [
        "Chapter one",
        "Chapter two",
        "Chapter three",
        "Chapter four",
    ]
    assert [r["live"] for r in rows] == [True, True, False, False]
    assert [r["status"] for r in rows] == [
        "not_started",
        "not_started",
        "coming_soon",
        "coming_soon",
    ]
    assert [r["id"] for r in rows if r["recommended"]] == ["CH.ONE"]
    assert body["subject"] == "math"


def test_status_follows_mastery_and_the_recommendation_moves_on(
    client: TestClient, db: Session, chapters_world: World
) -> None:
    _mastery(db, chapters_world, "SK.A", 7)
    _mastery(db, chapters_world, "SK.B", 7)
    rows = {r["id"]: r for r in _chapters(client, chapters_world)["chapters"]}
    assert rows["CH.ONE"]["status"] == "solid"
    assert rows["CH.TWO"]["recommended"] is True
    assert rows["CH.ONE"]["recommended"] is False
    _mastery(db, chapters_world, "SK.C", 2)
    rows = {r["id"]: r for r in _chapters(client, chapters_world)["chapters"]}
    assert rows["CH.TWO"]["status"] == "learning"


def test_overdue_review_shows_review_due(
    client: TestClient, db: Session, chapters_world: World
) -> None:
    _mastery(db, chapters_world, "SK.A", 5, due_in_days=-1)
    _mastery(db, chapters_world, "SK.B", 5, due_in_days=3)
    rows = {r["id"]: r for r in _chapters(client, chapters_world)["chapters"]}
    assert rows["CH.ONE"]["status"] == "review_due"


def test_draft_chapter_is_live_only_when_drafts_are_allowed(
    client: TestClient, chapters_world: World
) -> None:
    settings.allow_draft_content = True
    rows = {r["id"]: r for r in _chapters(client, chapters_world)["chapters"]}
    assert rows["CH.DRAFT"]["live"] is True
    assert rows["CH.SOON"]["live"] is False  # no skills at all: always coming soon


def test_titles_fall_back_to_english(
    client: TestClient, db: Session, chapters_world: World
) -> None:
    student = db.get(StudentRow, uuid.UUID(chapters_world.student_share_id))
    assert student is not None
    student.home_language = "ne"
    db.commit()
    rows = {r["id"]: r for r in _chapters(client, chapters_world)["chapters"]}
    assert rows["CH.ONE"]["title"] == "Chapter one" or rows["CH.ONE"]["title"] == "अध्याय एक"
    assert rows["CH.TWO"]["title"] == "Chapter two"


def test_chapter_counts_for_the_card(
    client: TestClient, db: Session, chapters_world: World
) -> None:
    _mastery(db, chapters_world, "SK.A", 4)
    rows = {r["id"]: r for r in _chapters(client, chapters_world)["chapters"]}
    assert rows["CH.ONE"]["skills_total"] == 2
    assert rows["CH.ONE"]["skills_can_do_it"] == 1


def test_another_family_cannot_read_the_chapter_list(
    client: TestClient, chapters_world: World
) -> None:
    response = client.get(
        f"/students/{chapters_world.student_share_id}/chapters",
        headers=auth_header(chapters_world.other_parent_token),
    )
    assert response.status_code == 403


def test_skill_path_for_a_chapter(client: TestClient, db: Session, chapters_world: World) -> None:
    _mastery(db, chapters_world, "SK.A", 4)
    response = client.get(
        f"/students/{chapters_world.student_share_id}/chapters/CH.ONE/skills",
        headers=auth_header(chapters_world.student_token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["chapter"]["id"] == "CH.ONE"
    skills = body["skills"]
    assert [s["id"] for s in skills] == ["SK.A", "SK.B"]
    assert [s["status"] for s in skills] == ["can_do_it", "not_started"]
    assert [s["unlocked"] for s in skills] == [True, True]
    assert [s["current"] for s in skills] == [False, True]
    assert skills[0]["title"] == "Skill SK.A"


def test_skill_path_of_a_locked_follower_is_visual_only(
    client: TestClient, chapters_world: World
) -> None:
    response = client.get(
        f"/students/{chapters_world.student_share_id}/chapters/CH.ONE/skills",
        headers=auth_header(chapters_world.student_token),
    )
    skills = response.json()["skills"]
    assert [s["unlocked"] for s in skills] == [True, False]  # SK.B is shown locked, not blocked


def test_unknown_chapter_is_404(client: TestClient, chapters_world: World) -> None:
    response = client.get(
        f"/students/{chapters_world.student_share_id}/chapters/NOPE/skills",
        headers=auth_header(chapters_world.student_token),
    )
    assert response.status_code == 404


def test_coming_soon_chapter_cannot_be_started(client: TestClient, chapters_world: World) -> None:
    for chapter in ("CH.SOON", "CH.DRAFT"):
        response = client.post(
            "/sessions",
            json={
                "student_id": chapters_world.student_share_id,
                "type": "practice",
                "chapter_id": chapter,
            },
            headers=auth_header(chapters_world.student_token),
        )
        assert response.status_code == 409, (chapter, response.text)
        assert response.json()["detail"] == "chapter_coming_soon"


def test_live_chapter_can_be_started_and_unknown_one_is_404(
    client: TestClient, chapters_world: World
) -> None:
    ok = client.post(
        "/sessions",
        json={
            "student_id": chapters_world.student_share_id,
            "type": "practice",
            "chapter_id": "CH.ONE",
        },
        headers=auth_header(chapters_world.student_token),
    )
    assert ok.status_code == 200, ok.text
    missing = client.post(
        "/sessions",
        json={
            "student_id": chapters_world.student_share_id,
            "type": "practice",
            "chapter_id": "NOPE",
        },
        headers=auth_header(chapters_world.student_token),
    )
    assert missing.status_code == 404
