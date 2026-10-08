"""G2b through the API: break_or_switch, the prerequisite probe, win and challenge extras."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.db.models import ItemRow, MasteryRow, MisconceptionRow, SkillRow
from tests.conftest import World, auth_header
from tests.learner.test_chapters import chapters_world  # noqa: F401  (fixture)
from tests.player.test_stuck_picker_api import Play, _full_item


@pytest.fixture
def g2b_world(db: Session, chapters_world: World) -> World:  # noqa: F811
    for n in range(1, 7):
        db.add(_full_item(f"G2.{n}", str(5 + n)))
    db.commit()
    return chapters_world


def _answer_for(item_id: str) -> str:
    return str(5 + int(item_id.split(".")[1]))


def _three_fast_answers(play: Play) -> None:
    given = 0
    for _ in range(12):
        if given == 3 or play.action["type"] == "break_or_switch":
            return
        if play.action["type"] in {"explain_back_prompt", "explain_back_result"}:
            play.send("continue")
        else:
            play.send("answer", response=_answer_for(play.action["item_id"]), latency_ms=200)
            given += 1


def test_three_fast_answers_offer_a_break_or_switch_and_a_break_can_be_resumed(
    client: TestClient, g2b_world: World
) -> None:
    play = Play(client, g2b_world)
    _three_fast_answers(play)
    assert play.action["type"] == "break_or_switch"
    assert play.action["extras"]["choices"] == ["break", "switch", "continue"]
    assert play.action["rule_id"] == "R35"
    assert play.action["can_request_help"] is False
    ended = play.send("break_choice", choice="break")
    assert ended["type"] == "end_session" and ended["ended_reason"] == "break"
    today = client.get("/students/me/today", headers=auth_header(g2b_world.student_token)).json()
    assert today["resume"]["session_id"] == play.session_id and today["resume"]["resumable"]


def test_continue_returns_to_the_same_question(client: TestClient, g2b_world: World) -> None:
    play = Play(client, g2b_world)
    _three_fast_answers(play)
    assert play.action["type"] == "break_or_switch"
    item = play.action["item_id"]
    back = play.send("break_choice", choice="continue")
    assert back["type"] == "show_item" and back["item_id"] == item


def test_an_unknown_break_choice_is_flagged(client: TestClient, g2b_world: World) -> None:
    play = Play(client, g2b_world)
    bad = play.send("break_choice", choice="break")
    assert bad["rejected"] is True and bad["guardrail_flag"] == "not_in_break_choice"


def _add_prerequisite(db: Session, g2b_student_id: str) -> None:
    db.add(
        SkillRow(
            id="SK.P",
            title={"en": "Prerequisite"},
            grade_band=[9],
            subject="math",
            prerequisites=[],
            related=[],
            misconceptions=[],
            bkt={"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
            status="approved",
        )
    )
    sk = db.get(SkillRow, "SK.A")
    assert sk is not None
    sk.prerequisites = ["SK.P"]
    db.add(  # the prerequisite is reasonably known, so the student practises SK.A first
        MasteryRow(
            student_id=uuid.UUID(g2b_student_id),
            skill_id="SK.P",
            p_known=0.8,
            attempts=4,
            unhinted_correct=2,
            hinted_correct=1,
            last_updated=now_utc(),
            ladder_level=3,
            ladder_evidence={"1": ["e"], "2": ["e"], "3": ["e"]},
        )
    )
    for n in range(1, 4):
        db.add(_full_item(f"PR.{n}", str(40 + n), skill="SK.P") if False else _prereq_item(n))
    db.add(
        MisconceptionRow(
            id="MC.PRE",
            title={"en": "Needs the earlier idea"},
            explanation={"en": "This step needs an earlier idea first.", "ne": None, "as": None},
            remedial_skill="SK.P",
            status="draft",
        )
    )
    for row in db.scalars(select(ItemRow).where(ItemRow.id.like("G2.%"))):
        row.misconception_rules = [{"id": "MC.PRE", "when_answer_equals": ["-2"]}]
    db.commit()


def _prereq_item(n: int) -> ItemRow:
    row = _full_item(f"PR.{n}", str(40 + n))
    row.skill_ids = ["SK.P"]
    row.primary_skill = "SK.P"
    return row


def test_a_prerequisite_gap_answer_probes_the_prerequisite_then_changes_the_view(
    client: TestClient, db: Session, g2b_world: World
) -> None:
    _add_prerequisite(db, g2b_world.student_share_id)
    play = Play(client, g2b_world)
    probe = play.send("answer", response="-2", latency_ms=9000)
    assert probe["type"] == "show_item" and probe["skill_id"] == "SK.P"
    assert probe["extras"] == {"probe": True, "for_skill": "SK.A"}
    assert probe["rule_id"] == "R33"
    assert probe["can_request_help"] is False and probe["can_show_solution"] is False
    shown = play.send(
        "answer", response=str(40 + int(probe["item_id"].split(".")[1])), latency_ms=9000
    )
    assert shown["type"] == "worked_example" and shown["extras"]["representation_change"] is True
    back = play.send("continue")
    assert back["type"] == "show_item" and back["skill_id"] == "SK.A"


def test_a_wrong_probe_sends_the_student_to_the_prerequisite_next(
    client: TestClient, db: Session, g2b_world: World
) -> None:
    _add_prerequisite(db, g2b_world.student_share_id)
    play = Play(client, g2b_world)
    play.send("answer", response="-2", latency_ms=9000)
    nxt = play.send("answer", response="999999", latency_ms=9000)
    assert nxt["skill_id"] == "SK.P" and not nxt["extras"].get("probe")


def test_help_is_refused_during_a_probe(client: TestClient, db: Session, g2b_world: World) -> None:
    _add_prerequisite(db, g2b_world.student_share_id)
    play = Play(client, g2b_world)
    play.send("answer", response="-2", latency_ms=9000)
    refused = play.send("request_help")
    assert refused["rejected"] is True and refused["guardrail_flag"] == "no_help_in_probe"


def test_the_probe_state_survives_between_requests(
    client: TestClient, db: Session, g2b_world: World
) -> None:
    _add_prerequisite(db, g2b_world.student_share_id)
    play = Play(client, g2b_world)
    play.send("answer", response="-2", latency_ms=9000)
    again = client.get(f"/sessions/{play.session_id}", headers=play.headers).json()["action"]
    assert again["extras"]["probe"] is True and again["skill_id"] == "SK.P"
    assert uuid.UUID(play.session_id)
