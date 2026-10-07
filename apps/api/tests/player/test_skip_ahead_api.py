"""Skip ahead through the API: server-checked, no BKT, level 4 with evidence=test_out."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.db.models import EventRow, ItemRow, MasteryRow, SessionRow
from app.learner.ladder import SkillLadder
from app.player.ladder_log import recompute_ladders
from tests.conftest import World, auth_header
from tests.learner.test_chapters import chapters_world  # noqa: F401  (fixture)

SKILL = "SK.A"
ANSWERS = {"TO.H1": "6", "TO.H2": "8", "TO.T1": "7"}


def _item(item_id: str, answer: str, *, role: str, difficulty: float = 0.9, skill: str = SKILL):
    return ItemRow(
        id=item_id,
        skill_ids=[skill],
        primary_skill=skill,
        difficulty=difficulty,
        type="expression",
        pool="practice",
        role=role,
        stem={"en": f"Solve to get {answer}", "ne": None, "as": None},
        verify=None,
        options=[],
        answer={"sympy": answer, "accept": [answer, f"x={answer}"]},
        solution_steps=[{"en": f"x = {answer}"}],
        hints=[{"level": 1, "en": "h1"}, {"level": 2, "en": "h2"}, {"level": 3, "en": "h3"}],
        prediction_prompt={"en": "?"},
        misconception_rules=[],
        status="approved",
    )


@pytest.fixture
def world_with_items(db: Session, chapters_world: World) -> World:  # noqa: F811
    db.add(_item("TO.H1", "6", role="procedure"))
    db.add(_item("TO.H2", "8", role="procedure"))
    db.add(_item("TO.T1", "7", role="transfer"))
    db.commit()
    return chapters_world


class Skip:
    def __init__(
        self, client: TestClient, world: World, chapter: str = "CH.ONE", skill: str = SKILL
    ):
        self.client = client
        self.world = world
        self.headers = auth_header(world.student_token)
        self.response = client.post(
            f"/students/{world.student_share_id}/chapters/{chapter}/skills/{skill}/skip-ahead",
            headers=self.headers,
        )

    @property
    def view(self) -> dict:
        assert self.response.status_code == 200, self.response.text
        return self.response.json()

    def answer(self, response: str, event_id: str | None = None) -> dict:
        view = self.view
        sent = self.client.post(
            f"/sessions/{view['id']}/events",
            json={
                "client_event_id": event_id or str(uuid.uuid4()),
                "event_type": "answer",
                "item_id": self.last_action["item_id"],
                "payload": {"response": response, "latency_ms": 4000},
            },
            headers=self.headers,
        )
        assert sent.status_code == 200, sent.text
        self.last = sent.json()
        return self.last

    @property
    def last_action(self) -> dict:
        last = getattr(self, "last", None)
        return (last or self.view)["action"]


def _correct(action: dict) -> str:
    return ANSWERS[action["item_id"]]


def _mastery(db: Session, world: World, skill: str = SKILL) -> MasteryRow | None:
    db.expire_all()
    return db.get(MasteryRow, (uuid.UUID(world.student_share_id), skill))


def _events(db: Session, session_id: str, event_type: str) -> int:
    db.expire_all()
    return int(
        db.scalar(
            select(func.count())
            .select_from(EventRow)
            .where(EventRow.session_id == uuid.UUID(session_id), EventRow.event_type == event_type)
        )
        or 0
    )


def test_starts_an_assessment_without_hints(client: TestClient, world_with_items: World) -> None:
    skip = Skip(client, world_with_items)
    view = skip.view
    assert view["type"] == "test_out"
    action = view["action"]
    assert action["type"] == "show_item"
    assert action["item_id"] in ANSWERS
    assert action["can_request_hint"] is False and action["can_show_solution"] is False
    assert action["extras"]["assessment"] is True
    assert action["extras"]["test_out"] == {"index": 1, "of": 2}
    assert "answer" not in (action["item"] or {})


def test_two_correct_answers_move_the_skill_to_level_4(
    client: TestClient, db: Session, world_with_items: World
) -> None:
    skip = Skip(client, world_with_items)
    first = skip.answer(_correct(skip.last_action))
    assert first["action"]["type"] == "show_item"
    assert first["action"]["extras"]["test_out"] == {"index": 2, "of": 2}
    done = skip.answer(_correct(skip.last_action))
    action = done["action"]
    assert action["type"] == "test_out_result"
    assert action["extras"]["passed"] is True
    assert action["extras"]["level"] == 4
    row = _mastery(db, world_with_items)
    assert row is not None
    assert row.ladder_level == 4
    assert row.p_known >= 0.95  # level 4 implies mastery, so the policy stops treating it as weak
    assert row.flags["evidence"] == "test_out"
    assert len(row.ladder_evidence["4"]) == 1
    assert _events(db, skip.view["id"], "test_out_passed") == 1


def test_the_two_items_include_an_apply_or_transfer_one(
    client: TestClient, world_with_items: World
) -> None:
    skip = Skip(client, world_with_items)
    seen = [skip.last_action["item_id"]]
    skip.answer(_correct(skip.last_action))
    seen.append(skip.last_action["item_id"])
    assert "TO.T1" in seen


def test_a_miss_returns_to_the_path_without_penalty(
    client: TestClient, db: Session, world_with_items: World
) -> None:
    skip = Skip(client, world_with_items)
    skip.answer("999")
    done = skip.answer(_correct(skip.last_action))
    action = done["action"]
    assert action["type"] == "test_out_result"
    assert action["extras"]["passed"] is False
    assert _mastery(db, world_with_items) is None  # nothing written for a miss
    assert _events(db, skip.view["id"], "test_out_passed") == 0


def test_answers_never_touch_bkt_or_the_review_schedule(
    client: TestClient, db: Session, world_with_items: World
) -> None:
    skip = Skip(client, world_with_items)
    skip.answer(_correct(skip.last_action))
    skip.answer(_correct(skip.last_action))
    row = _mastery(db, world_with_items)
    assert row is not None
    assert row.attempts == 0 and row.unhinted_correct == 0 and row.hinted_correct == 0
    assert row.p_known >= 0.95  # set by the pass itself, not by the answers


def test_hints_and_solutions_are_refused(client: TestClient, world_with_items: World) -> None:
    skip = Skip(client, world_with_items)
    view = skip.view
    for event_type in ("request_hint", "show_solution"):
        sent = client.post(
            f"/sessions/{view['id']}/events",
            json={
                "client_event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "item_id": skip.last_action["item_id"],
                "payload": {},
            },
            headers=skip.headers,
        )
        assert sent.status_code == 200
        body = sent.json()["action"]
        assert body["type"] == "show_item"
        assert body["rejected"] is True
        assert body["guardrail_flag"] == "no_hint_in_assessment"


def test_a_repeated_event_is_not_counted_twice(client: TestClient, world_with_items: World) -> None:
    skip = Skip(client, world_with_items)
    event_id = str(uuid.uuid4())
    first = skip.answer(_correct(skip.last_action), event_id=event_id)
    again = client.post(
        f"/sessions/{skip.view['id']}/events",
        json={
            "client_event_id": event_id,
            "event_type": "answer",
            "item_id": first["action"]["item_id"],
            "payload": {"response": "1"},
        },
        headers=skip.headers,
    )
    assert again.json()["duplicate"] is True
    assert again.json()["action"]["extras"]["test_out"] == {"index": 2, "of": 2}


def test_the_ladder_recomputed_from_the_log_agrees(
    client: TestClient, db: Session, world_with_items: World
) -> None:
    from app.player.runtime import load_catalog

    skip = Skip(client, world_with_items)
    skip.answer(_correct(skip.last_action))
    skip.answer(_correct(skip.last_action))
    ladders = recompute_ladders(
        db,
        uuid.UUID(world_with_items.student_share_id),
        load_catalog(db, allow_draft=True),
        {},
        now=now_utc() + timedelta(seconds=1),
    )
    assert isinstance(ladders[SKILL], SkillLadder)
    assert ladders[SKILL].level == 4


def test_a_skill_that_is_not_in_the_chapter_is_404(
    client: TestClient, world_with_items: World
) -> None:
    assert Skip(client, world_with_items, skill="SK.C").response.status_code == 404


def test_coming_soon_chapter_is_refused(client: TestClient, world_with_items: World) -> None:
    response = Skip(client, world_with_items, chapter="CH.SOON", skill=SKILL).response
    assert response.status_code == 409
    assert response.json()["detail"] == "chapter_coming_soon"


def test_unavailable_without_hard_items_for_the_skill(
    client: TestClient, world_with_items: World
) -> None:
    response = Skip(client, world_with_items, skill="SK.B").response
    assert response.status_code == 409
    assert response.json()["detail"] == "test_out_unavailable"


def test_another_family_cannot_skip_ahead(client: TestClient, world_with_items: World) -> None:
    response = client.post(
        f"/students/{world_with_items.student_share_id}/chapters/CH.ONE/skills/{SKILL}/skip-ahead",
        headers=auth_header(world_with_items.other_parent_token),
    )
    assert response.status_code == 403


def test_a_finished_skip_ahead_does_not_show_up_as_resume(
    client: TestClient, db: Session, world_with_items: World
) -> None:
    skip = Skip(client, world_with_items)
    skip.answer(_correct(skip.last_action))
    today = client.get("/students/me/today", headers=skip.headers).json()
    assert today["resume"] is None  # an open skip-ahead is never offered as Resume
    db.expire_all()
    row = db.get(SessionRow, uuid.UUID(skip.view["id"]))
    assert row is not None and row.type == "test_out"
