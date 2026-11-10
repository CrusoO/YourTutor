"""Group lessons through the API: publish, open by link, send results, the organiser's view."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.config import settings
from app.db.models import GroupLessonRow, GroupResultRow
from app.llm.rules import default_rules
from tests.conftest import World, auth_header
from tests.groups.test_service import CHECK, PREDICT, blocks


def publish(client: TestClient, token: str, body: dict[str, Any] | None = None) -> Any:
    payload = {"prompt": "what is quantum tunnelling?", "language": "en", "blocks": blocks()}
    return client.post("/groups", json={**payload, **(body or {})}, headers=auth_header(token))


def send(client: TestClient, token: str, code: str, items: list[dict[str, Any]]) -> Any:
    return client.post(f"/groups/{code}/results", json={"items": items}, headers=auth_header(token))


def answer(
    question: str, right: bool, confidence: str | None = None, idea: str | None = None
) -> dict:
    kind = "predict" if question == PREDICT else "check"
    return {
        "question": question,
        "kind": kind,
        "right": right,
        "confidence": confidence,
        "idea": idea,
    }


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


# ── publishing ───────────────────────────────────────────────────────────────


def test_a_teacher_publishes_a_lesson_and_gets_a_link(client: TestClient, world: World) -> None:
    r = publish(client, world.teacher_token)
    assert r.status_code == 200, r.text
    assert r.json()["path"] == f"/brownie-chat?group={r.json()['code']}"


def test_only_a_teacher_or_admin_may_publish(client: TestClient, world: World) -> None:
    assert publish(client, world.student_token).status_code == 403
    assert publish(client, world.parent_token).status_code == 403
    assert publish(client, world.admin_token).status_code == 200
    assert client.post("/groups", json={"prompt": "x y", "blocks": blocks()}).status_code in {
        401,
        403,
    }


@pytest.mark.parametrize(
    "bad",
    [
        [],  # nothing
        blocks()[1:],  # no hook first
        [b for b in blocks() if b["kind"] != "check"],  # nothing to land on
        [{"kind": "quiz"}] * 6,  # not a lesson
    ],
)
def test_a_lesson_that_is_not_usable_is_refused(
    client: TestClient, world: World, bad: list
) -> None:
    r = publish(client, world.teacher_token, {"blocks": bad})
    assert r.status_code == 422, r.text


def test_a_lesson_with_a_blocked_term_is_refused(client: TestClient, world: World) -> None:
    term = sorted(default_rules().blocked_terms)[0]
    tainted = blocks()
    tainted[0]["text"] = f"about {term} today"
    assert publish(client, world.teacher_token, {"blocks": tainted}).status_code == 422


def test_the_prompt_and_language_are_checked(client: TestClient, world: World) -> None:
    assert publish(client, world.teacher_token, {"prompt": "x"}).status_code == 422
    assert publish(client, world.teacher_token, {"prompt": "y" * 301}).status_code == 422
    assert publish(client, world.teacher_token, {"language": "fr"}).status_code == 422


def test_what_is_stored_is_the_cleaned_lesson_not_what_was_sent(
    client: TestClient, world: World, db: Session
) -> None:
    sent = blocks()
    sent[0]["text"] = "t " * 1000
    sent.append({"kind": "quiz", "text": "ignored"})
    code = publish(client, world.teacher_token, {"blocks": sent}).json()["code"]
    row = db.scalar(select(GroupLessonRow).where(GroupLessonRow.code == code))
    assert row is not None
    assert len(row.blocks[0]["text"]) <= 500
    assert all(b["kind"] != "quiz" for b in row.blocks)


# ── opening by link ──────────────────────────────────────────────────────────


def test_anyone_with_the_link_can_open_the_lesson_without_signing_in(
    client: TestClient, world: World
) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    r = client.get(f"/groups/{code}")
    assert r.status_code == 200
    body = r.json()
    assert body["prompt"] == "what is quantum tunnelling?" and body["closed"] is False
    assert body["results_open"] is True
    assert [b["kind"] for b in body["blocks"]][0] == "hook"
    assert "owner_id" not in body and "owner" not in body


@pytest.mark.parametrize("code", ["nope", "a" * 40, "../etc", "ABCDEFGH", "bad code!"])
def test_an_unknown_or_malformed_code_is_not_found(client: TestClient, code: str) -> None:
    assert client.get(f"/groups/{code}").status_code == 404


def test_results_are_not_offered_when_learners_are_not_assumed_to_be_adults(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    monkeypatch.setattr(settings, "adult_learners_assumed", False)
    assert client.get(f"/groups/{code}").json()["results_open"] is False


# ── sending results ──────────────────────────────────────────────────────────


def test_a_participant_sends_results_and_only_what_matches_is_kept(
    client: TestClient, world: World, db: Session
) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    r = send(
        client,
        world.student_token,
        code,
        [
            answer(PREDICT, False, "sure", "thinks a ball can pass through the hill"),
            answer("A question the lesson never asked", False),
            answer(CHECK, False, "unsure", "an invented idea"),
        ],
    )
    assert r.status_code == 200 and r.json() == {"accepted": 2}
    row = db.scalar(select(GroupResultRow))
    assert row is not None
    assert [(i["question"], i["idea"]) for i in row.items] == [
        (PREDICT, "thinks a ball can pass through the hill"),
        (CHECK, None),
    ]


def test_sending_again_replaces_the_earlier_answer_so_each_person_counts_once(
    client: TestClient, world: World, db: Session
) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    send(client, world.student_token, code, [answer(CHECK, False, "sure")])
    send(client, world.student_token, code, [answer(CHECK, True, "sure")])
    assert count(db, GroupResultRow) == 1
    assert db.scalar(select(GroupResultRow)).items[0]["right"] is True  # type: ignore[union-attr]


def test_nothing_in_a_stored_result_identifies_the_person(
    client: TestClient, world: World, db: Session
) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    send(client, world.student_token, code, [answer(CHECK, False, "sure")])
    row = db.scalar(select(GroupResultRow))
    assert row is not None
    stored = f"{row.participant} {row.items}"
    assert world.student_share_id not in stored and world.student_token not in stored
    assert set(vars(row)) >= {"participant", "items", "submitted_at"}
    assert not any("student" in column for column in GroupResultRow.__table__.columns.keys())


def test_only_a_learner_may_send_and_it_must_name_something(
    client: TestClient, world: World
) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    assert send(client, world.teacher_token, code, [answer(CHECK, True)]).status_code == 403
    assert client.post(
        f"/groups/{code}/results", json={"items": [answer(CHECK, True)]}
    ).status_code in {401, 403}
    assert send(client, world.student_token, code, []).status_code == 422
    assert (
        send(client, world.student_token, code, [answer("not in the lesson", True)]).status_code
        == 422
    )
    assert send(client, world.student_token, "nope", [answer(CHECK, True)]).status_code == 404


def test_results_are_refused_while_there_is_no_age_gate_to_rely_on(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch, db: Session
) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    monkeypatch.setattr(settings, "adult_learners_assumed", False)
    r = send(client, world.student_token, code, [answer(CHECK, True)])
    assert r.status_code == 403 and r.json()["detail"] == "age_gate_required"
    assert count(db, GroupResultRow) == 0


def test_a_closed_group_takes_no_more_results(client: TestClient, world: World) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    assert (
        client.post(f"/groups/{code}/close", headers=auth_header(world.teacher_token)).status_code
        == 200
    )
    assert send(client, world.student_token, code, [answer(CHECK, True)]).status_code == 409
    opened = client.get(f"/groups/{code}").json()
    assert opened["closed"] is True and opened["results_open"] is False


def test_only_the_owner_or_an_admin_may_close(client: TestClient, world: World) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    assert (
        client.post(f"/groups/{code}/close", headers=auth_header(world.parent_token)).status_code
        == 403
    )
    assert (
        client.post(f"/groups/{code}/close", headers=auth_header(world.student_token)).status_code
        == 403
    )


# ── the organiser's view ─────────────────────────────────────────────────────


# A key no random join code or id can contain by chance (a short "p3" could, now and then).
PARTICIPANT_PREFIX = "participant-key-"


def add_people(db: Session, code: str, n: int, wrong: int) -> None:
    group = db.scalar(select(GroupLessonRow).where(GroupLessonRow.code == code))
    assert group is not None
    for i in range(n):
        right = i >= wrong
        db.add(
            GroupResultRow(
                id=uuid.uuid4(),
                group_id=group.id,
                participant=f"{PARTICIPANT_PREFIX}{i}",
                submitted_at=now_utc(),
                items=[
                    {
                        "question": CHECK,
                        "kind": "check",
                        "right": right,
                        "confidence": "sure" if i % 2 == 0 else "unsure",
                        "idea": None if right else "thinks thicker helps",
                    }
                ],
            )
        )
    db.commit()


def test_the_organiser_sees_nothing_until_enough_people_have_answered(
    client: TestClient, world: World, db: Session
) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    add_people(db, code, 4, wrong=4)
    body = client.get(f"/groups/{code}/summary", headers=auth_header(world.teacher_token)).json()
    assert body["ready"] is False and body["participants"] == 4 and body["questions"] == []


def test_the_organiser_sees_where_the_group_is_stuck_once_enough_have_answered(
    client: TestClient, world: World, db: Session
) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    add_people(db, code, 9, wrong=6)
    body = client.get(f"/groups/{code}/summary", headers=auth_header(world.teacher_token)).json()
    assert body["ready"] is True and body["participants"] == 9
    (row,) = body["questions"]
    assert row["question"] == CHECK and row["answered"] == 9 and row["wrong"] == 6
    assert row["ideas"] == [{"idea": "thinks thicker helps", "count": 6}]
    assert "right" not in row
    assert PARTICIPANT_PREFIX not in str(body)  # no stored participant key


def test_nobody_else_may_see_the_summary(client: TestClient, world: World, db: Session) -> None:
    code = publish(client, world.teacher_token).json()["code"]
    add_people(db, code, 9, wrong=6)
    for token in (world.parent_token, world.student_token):
        assert client.get(f"/groups/{code}/summary", headers=auth_header(token)).status_code == 403
    assert client.get(f"/groups/{code}/summary").status_code in {401, 403}
    assert (
        client.get(f"/groups/{code}/summary", headers=auth_header(world.admin_token)).status_code
        == 200
    )


def test_the_list_shows_my_groups_with_how_many_have_answered(
    client: TestClient, world: World, db: Session
) -> None:
    first = publish(client, world.teacher_token).json()["code"]
    publish(client, world.admin_token, {"prompt": "someone else's lesson"})
    add_people(db, first, 3, wrong=1)
    groups = client.get("/groups", headers=auth_header(world.teacher_token)).json()["groups"]
    assert [(g["code"], g["participants"]) for g in groups] == [(first, 3)]
    assert client.get("/groups", headers=auth_header(world.student_token)).status_code == 403
