"""The teacher mistake list and warm-up through the API (in-memory database)."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.config import settings
from app.db.models import (
    ClassMembershipRow,
    ConsentRow,
    ItemRow,
    MisconceptionHitRow,
    MisconceptionRow,
    SessionRow,
    SkillRow,
    StudentRow,
)
from tests.conftest import World, auth_header, seed_user, signup

BKT = {"p_init": 0.2, "p_learn": 0.2, "p_slip": 0.1, "p_guess": 0.2}


def _clone_student(db: Session, world: World, index: int, share: bool = True) -> StudentRow:
    base = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert base is not None
    sid = uuid.uuid4()
    row = StudentRow(
        id=sid,
        parent_id=base.parent_id,
        display_name=f"Kid {index}",
        grade=base.grade,
        board=base.board,
        curriculum_id=base.curriculum_id,
        book_id=base.book_id,
        home_language=base.home_language,
        exam_language=base.exam_language,
        timezone=base.timezone,
        created_at=now_utc(),
    )
    db.add(row)
    db.flush()
    db.add(
        ConsentRow(
            id=uuid.uuid4(),
            student_id=sid,
            parent_id=base.parent_id,
            version="v1",
            scopes=["tutoring", "teacher_share"] if share else ["tutoring"],
            granted_at=now_utc(),
        )
    )
    db.add(ClassMembershipRow(class_id=uuid.UUID(world.class_id), student_id=sid))
    return row


def _item(item_id: str, mid: str, status: str = "approved", pool: str = "practice") -> ItemRow:
    return ItemRow(
        id=item_id,
        skill_ids=["SK.1"],
        primary_skill="SK.1",
        difficulty=0.5,
        type="mcq",
        pool=pool,
        role="procedure",
        stem={"en": f"Solve it ({item_id})"},
        answer={"sympy": "a", "accept": ["a"]},
        solution_steps=[{"en": "Do the right thing."}, {"en": "x = 3"}],
        hints=[],
        prediction_prompt={"en": ""},
        misconception_rules=[{"id": mid, "when_answer_equals": ["b"]}],
        options=[{"id": "a", "en": "3"}, {"id": "b", "en": "-3"}],
        status=status,
    )


def _hit(student: uuid.UUID, mid: str, item: str, days_ago: int) -> MisconceptionHitRow:
    return MisconceptionHitRow(
        id=uuid.uuid4(),
        student_id=student,
        misconception_id=mid,
        item_id=item,
        created_at=now_utc() - timedelta(days=days_ago),
    )


@pytest.fixture
def class_of_six(db: Session, world: World) -> None:
    """Six sharing students (five make MC.ADD, four make MC.SIDE) and one not shared."""
    db.add(
        SkillRow(
            id="SK.1",
            title={"en": "Solving pairs"},
            grade_band=[9],
            subject="math",
            prerequisites=[],
            related=[],
            misconceptions=[],
            bkt=BKT,
            status="approved",
        )
    )
    for mid, title in (("MC.ADD", "Adds instead of subtracts"), ("MC.SIDE", "Forgets a side")):
        db.add(
            MisconceptionRow(
                id=mid,
                title={"en": title},
                explanation={"en": "Why."},
                remedial_skill="SK.1",
                status="approved",
            )
        )
    for n in range(8):
        db.add(_item(f"IT.ADD.{n}", "MC.ADD", status="approved" if n < 4 else "draft"))
    db.add(_item("IT.SIDE.0", "MC.SIDE"))
    db.add(_item("IT.ADD.CP", "MC.ADD", pool="checkpoint"))
    db.flush()
    kids = [_clone_student(db, world, i) for i in range(6)]
    kids.append(_clone_student(db, world, 99, share=False))  # not shared: never counted
    for i, kid in enumerate(kids):
        db.add(
            SessionRow(
                id=uuid.uuid4(),
                student_id=kid.id,
                started_at=now_utc() - timedelta(days=1),
                type="practice",
                last_active_at=now_utc() - timedelta(days=1),
                plan={},
            )
        )
        if i < 5 or i == 6:
            db.add(_hit(kid.id, "MC.ADD", "IT.ADD.0", 2))
        if i < 4:
            db.add(_hit(kid.id, "MC.SIDE", "IT.SIDE.0", 3))
    db.commit()


def _get(client: TestClient, token: str, world: World, what: str, qs: str = "") -> Any:
    return client.get(f"/teacher/classes/{world.class_id}/{what}{qs}", headers=auth_header(token))


def test_mistake_list_shows_counts_only_and_hides_rows_under_five(
    client: TestClient, world: World, class_of_six: None
) -> None:
    res = _get(client, world.teacher_token, world, "mistakes")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["state"] == "ok"
    (row,) = body["mistakes"]  # MC.SIDE has four students: suppressed
    assert row["misconception_id"] == "MC.ADD"
    assert row["label"] == "Adds instead of subtracts"
    assert (row["students"], row["occurrences"]) == (5, 5)  # the unshared student is not counted
    assert row["skill_title"] == "Solving pairs"
    assert row["example"]["steps"] == ["Do the right thing.", "x = 3"]
    text = json.dumps(body)
    assert "Kid " not in text
    assert world.student_share_id not in text


def test_window_is_configurable(client: TestClient, world: World, class_of_six: None) -> None:
    body = _get(client, world.teacher_token, world, "mistakes", "?days=1").json()
    assert body["mistakes"] == []  # hits were 2 to 3 days ago
    assert _get(client, world.teacher_token, world, "mistakes", "?days=0").status_code == 422
    assert _get(client, world.teacher_token, world, "mistakes", "?days=91").status_code == 422


def test_small_class_gets_only_the_not_enough_state(client: TestClient, world: World) -> None:
    body = _get(client, world.teacher_token, world, "mistakes").json()
    assert body["state"] == "not_enough_students"
    assert body["mistakes"] == [] and body["minimum_students"] == 5
    warm = _get(client, world.teacher_token, world, "warmup").json()
    assert warm["state"] == "not_enough_students" and warm["items"] == []


def test_warmup_uses_only_servable_practice_items_and_is_repeatable(
    client: TestClient, world: World, class_of_six: None
) -> None:
    assert settings.allow_draft_content is False
    first = _get(client, world.teacher_token, world, "warmup", "?seed=abc").json()
    again = _get(client, world.teacher_token, world, "warmup", "?seed=abc").json()
    assert first == again
    ids = {i["item_id"] for i in first["items"]}
    assert ids <= {f"IT.ADD.{n}" for n in range(4)}  # no drafts, no checkpoint item
    assert len(ids) == 4 and first["short_by"] == 1  # four servable items: said plainly, no padding
    assert all(i["targets"]["label"] == "Adds instead of subtracts" for i in first["items"])
    assert all(i["answer"] == "3" for i in first["items"])


def test_warmup_with_nothing_servable_says_so(
    client: TestClient, world: World, class_of_six: None, db: Session
) -> None:
    for row in db.query(ItemRow).all():
        row.status = "draft"
    db.commit()
    body = _get(client, world.teacher_token, world, "warmup").json()
    assert body["state"] == "no_items" and body["items"] == [] and body["short_by"] == 5


def test_other_people_are_refused(
    client: TestClient, sender: Any, db: Session, world: World, class_of_six: None
) -> None:
    other = seed_user(db, "teacher", "teacher2@example.com")
    other_token = signup(client, sender, other.email)
    for what in ("mistakes", "warmup"):
        assert _get(client, other_token, world, what).status_code == 403
        assert _get(client, world.parent_token, world, what).status_code == 403
        assert _get(client, world.student_token, world, what).status_code == 403
        assert client.get(f"/teacher/classes/{world.class_id}/{what}").status_code in (401, 403)
        assert _get(client, world.admin_token, world, what).status_code == 200
