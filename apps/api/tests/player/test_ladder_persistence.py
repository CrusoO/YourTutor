"""G1 persistence: ladder columns on `mastery`, event ids/correctness in the log, recompute."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import EventRow, ItemRow, MasteryRow, OverlayRow, SkillRow, StudentRow
from app.learner.bkt import BktParams
from app.learner.ladder import SkillLadder
from app.learner.types import LearnerState, Mastery
from app.player.runtime import (
    load_catalog,
    load_learner,
    persist_learner,
    recompute_ladders,
)
from tests.conftest import World, auth_header

SKILL = "MATH.LADDER.ONE"
OVERLAY = "OV.LADDER"
ANSWERS = {"LAD.P1": "6", "LAD.P2": "8", "LAD.P3": "7", "LAD.P4": "12"}
STEMS = {
    "LAD.P1": "Solve for x: x + 4 = 10",
    "LAD.P2": "Find x if x - 3 = 5",
    "LAD.P3": "What number x makes 2x = 14 true?",
    "LAD.P4": "x/3 = 4. What is x?",
}
PARAMS = BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)


def _item(db: Session, item_id: str, *, pool: str = "practice", role: str = "procedure") -> None:
    answer = ANSWERS.get(item_id, "5")
    db.add(
        ItemRow(
            id=item_id,
            skill_ids=[SKILL],
            primary_skill=SKILL,
            difficulty=0.25,
            type="expression",
            pool=pool,
            role=role,
            stem={"en": STEMS.get(item_id, "Solve for x: x + 2 = 7"), "ne": None, "as": None},
            verify=None,
            options=[],
            answer={"sympy": answer, "accept": [answer, f"x={answer}"]},
            solution_steps=[{"en": f"x = {answer}"}],
            hints=[
                {"level": 1, "en": "Undo the operation."},
                {"level": 2, "en": "Do the opposite to the number."},
                {"level": 3, "en": f"x = {answer}"},
            ],
            prediction_prompt={"en": "Is x small?"},
            misconception_rules=[],
            status="draft",
        )
    )


def _seed(db: Session, world: World) -> None:
    settings.allow_draft_content = True
    db.add(
        SkillRow(
            id=SKILL,
            title={"en": "Ladder skill"},
            grade_band=[9],
            subject="math",
            prerequisites=[],
            related=[],
            misconceptions=[],
            bkt={"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
            status="approved",
        )
    )
    db.add(
        OverlayRow(
            id=OVERLAY,
            board="bhutan",
            grade=9,
            chapter="linear_equations",
            skill_ids=[SKILL],
            live=False,
        )
    )
    for item_id in ANSWERS:
        _item(db, item_id)
    _item(db, "LAD.C1", pool="checkpoint")
    _item(db, "LAD.C2", pool="checkpoint")
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    student.current_chapter_id = OVERLAY
    student.context_key = {**(student.context_key or {}), "chapter_id": OVERLAY}
    db.commit()


class Player:
    def __init__(self, client: TestClient, world: World, session_type: str = "practice") -> None:
        self.client = client
        self.headers = auth_header(world.student_token)
        self.student_id = world.student_share_id
        started = client.post(
            "/sessions",
            json={"student_id": self.student_id, "type": session_type},
            headers=self.headers,
        )
        assert started.status_code == 200, started.text
        self.session_id = started.json()["id"]
        self.action = started.json()["action"]
        self.event_ids: list[str] = []
        self.answer_event_ids: list[str] = []

    def send(self, event_type: str, item_id: str | None = None, **payload) -> dict:
        event_id = str(uuid.uuid4())
        body = {
            "client_event_id": event_id,
            "event_type": event_type,
            "payload": payload,
        }
        if item_id:
            body["item_id"] = item_id
        response = self.client.post(
            f"/sessions/{self.session_id}/events", json=body, headers=self.headers
        )
        assert response.status_code == 200, response.text
        self.event_ids.append(event_id)
        if event_type == "answer":
            self.answer_event_ids.append(event_id)
        self.action = response.json()["action"]
        return self.action

    def lesson(self) -> None:
        if self.action["type"] == "predict":
            self.send("predict_response", response="a guess")
        if self.action["type"] == "worked_example":
            self.send("continue")

    def settle(self) -> None:
        while self.action["type"] in {"explain_back_prompt", "explain_back_result"}:
            self.send("continue")

    def answer_current(self, *, hinted: bool = False) -> None:
        item_id = self.action["item_id"]
        if hinted:
            self.send("request_hint", item_id)
        self.send("answer", item_id, response=ANSWERS[item_id], latency_ms=900)
        self.settle()


def _stored(db: Session, world: World) -> MasteryRow:
    db.expire_all()
    row = db.get(MasteryRow, (uuid.UUID(world.student_share_id), SKILL))
    assert row is not None
    return row


def test_three_unhinted_answers_persist_level_4_with_event_ids(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world)
    player = Player(client, world)
    player.lesson()
    for _ in range(3):
        player.answer_current()
    row = _stored(db, world)
    assert row.ladder_level == 4
    assert row.ladder_evidence["4"] == player.answer_event_ids[:3]
    assert 1 in {int(k) for k in row.ladder_evidence}  # lesson flow + first item correct
    assert row.ladder_memory["skill_id"] == SKILL


def test_recompute_from_event_log_equals_stored_ladder(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world)
    player = Player(client, world)
    player.lesson()
    for _ in range(3):
        player.answer_current()
    stored = _stored(db, world)
    ladders = recompute_ladders(
        db,
        uuid.UUID(world.student_share_id),
        load_catalog(db, allow_draft=True),
        {SKILL: PARAMS},
        now=datetime.now(UTC),
    )
    assert ladders[SKILL].level == stored.ladder_level == 4
    assert ladders[SKILL].summary()["evidence"] == stored.ladder_evidence
    assert ladders[SKILL].summary()["flags"] == stored.flags


def test_hinted_answers_stay_below_level_4_and_recompute_agrees(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world)
    player = Player(client, world)
    player.lesson()
    for _ in range(3):
        player.answer_current(hinted=True)
    stored = _stored(db, world)
    assert stored.ladder_level == 3
    assert "4" not in stored.ladder_evidence
    ladders = recompute_ladders(
        db,
        uuid.UUID(world.student_share_id),
        load_catalog(db, allow_draft=True),
        {SKILL: PARAMS},
        now=datetime.now(UTC),
    )
    assert ladders[SKILL].summary()["evidence"] == stored.ladder_evidence


def test_explain_back_does_not_change_the_stored_ladder(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world)
    player = Player(client, world)
    player.lesson()
    item_id = player.action["item_id"]
    player.send("answer", item_id, response=ANSWERS[item_id], latency_ms=700)
    assert player.action["type"] == "explain_back_prompt"
    before = _stored(db, world)
    snapshot = (before.ladder_level, dict(before.ladder_evidence), dict(before.ladder_memory))
    player.send("explain_back", text="because I did the same to both sides")
    after = _stored(db, world)
    assert (after.ladder_level, dict(after.ladder_evidence), dict(after.ladder_memory)) == snapshot


def test_checkpoint_and_diagnostic_sessions_never_write_ladder_columns(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world)
    for session_type in ("checkpoint", "diagnostic"):
        player = Player(client, world, session_type)
        for _ in range(2):
            if player.action["type"] != "show_item":
                break
            player.send("answer", player.action["item_id"], response="5")
    db.expire_all()
    rows = db.scalars(select(MasteryRow).where(MasteryRow.skill_id == SKILL)).all()
    assert all(row.ladder_level == 0 and not row.ladder_evidence for row in rows)


def test_event_log_stores_verified_correctness_and_client_event_ids(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world)
    player = Player(client, world)
    player.lesson()
    item_id = player.action["item_id"]
    player.send("answer", item_id, response="999", latency_ms=500)  # wrong
    player.send("answer", item_id, response=ANSWERS[item_id], latency_ms=500)  # right
    rows = db.scalars(
        select(EventRow).where(
            EventRow.session_id == uuid.UUID(player.session_id), EventRow.event_type == "answer"
        )
    ).all()
    by_id = {str(row.client_event_id): row.correct for row in rows}
    assert by_id[player.answer_event_ids[0]] is False
    assert by_id[player.answer_event_ids[1]] is True


def test_load_and_persist_round_trip_keeps_ladder_memory(db: Session, world: World) -> None:
    student_id = uuid.UUID(world.student_share_id)
    ladder = SkillLadder(
        skill_id=SKILL,
        achieved=[3, 4],
        evidence={3: ["a"], 4: ["a", "b", "c"]},
        flags={"retention_stage": 1},
        seen=["x1", "x2"],
        run=[("a", "s1")],
    )
    learner = LearnerState()
    learner.mastery[SKILL] = Mastery(skill_id=SKILL, p_known=0.97)
    learner.ladders[SKILL] = ladder
    db.add(
        SkillRow(
            id=SKILL,
            title={"en": "x"},
            grade_band=[9],
            subject="math",
            prerequisites=[],
            related=[],
            misconceptions=[],
            bkt={"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
            status="approved",
        )
    )
    persist_learner(db, student_id, learner)
    db.commit()
    again = load_learner(db, student_id)
    assert again.ladders[SKILL].to_json() == ladder.to_json()
    row = db.get(MasteryRow, (student_id, SKILL))
    assert row is not None and row.ladder_level == 4 and row.flags == {"retention_stage": 1}
