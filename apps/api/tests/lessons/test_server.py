"""Lessons inside a real practice session: events, server re-checks, BKT/FSRS isolation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import (
    EventRow,
    ItemRow,
    MasteryRow,
    OverlayRow,
    ReviewCardRow,
    SkillRow,
    StudentRow,
)
from tests.conftest import World, auth_header

LESSON_SKILL = "MATH.ALG.LIN1.SOLVE_TWO_STEP"
PLAIN_SKILL = "MATH.PLAIN.NO_LESSON"
OVERLAY = "OV.LESSON"
SOLVED = {"lb": 1, "lw": 0, "rb": 0, "rw": 4}
UNSOLVED = {"lb": 2, "lw": 3, "rb": 0, "rw": 11}
ANSWERS = {"LES.P1": "6", "LES.P2": "8", "LES.P3": "7"}
STEMS = {
    "LES.P1": "Solve for x: x + 4 = 10",
    "LES.P2": "Find x if x - 3 = 5",
    "LES.P3": "What number x makes 2x = 14 true?",
}


def _skill(db: Session, skill_id: str) -> None:
    db.add(
        SkillRow(
            id=skill_id,
            title={"en": skill_id},
            grade_band=[9],
            subject="math",
            prerequisites=[],
            related=[],
            misconceptions=[],
            bkt={"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
            status="approved",
        )
    )


def _items(db: Session, skill_id: str, prefix: str) -> None:
    for item_id, answer in ANSWERS.items():
        db.add(
            ItemRow(
                id=item_id.replace("LES", prefix),
                skill_ids=[skill_id],
                primary_skill=skill_id,
                difficulty=0.25,
                type="expression",
                pool="practice",
                role="procedure",
                stem={"en": STEMS[item_id], "ne": None, "as": None},
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


def _seed(db: Session, world: World, skill_id: str) -> None:
    settings.allow_draft_content = True
    _skill(db, skill_id)
    db.add(
        OverlayRow(
            id=OVERLAY,
            curriculum_id="bhutan",
            grade=9,
            chapter="linear_equations",
            skill_ids=[skill_id],
            live=False,
        )
    )
    _items(db, skill_id, "LES")
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    student.current_chapter_id = OVERLAY
    student.context_key = {**(student.context_key or {}), "chapter_id": OVERLAY}
    db.commit()


class Player:
    def __init__(self, client: TestClient, world: World) -> None:
        self.client = client
        self.headers = auth_header(world.student_token)
        started = client.post(
            "/sessions",
            json={"student_id": world.student_share_id, "type": "practice"},
            headers=self.headers,
        )
        assert started.status_code == 200, started.text
        self.session_id = started.json()["id"]
        self.action = started.json()["action"]
        self.last: dict = started.json()

    def send(
        self, event_type: str, item_id: str | None = None, *, event_id: str | None = None, **payload
    ):
        body = {
            "client_event_id": event_id or str(uuid.uuid4()),
            "event_type": event_type,
            "payload": payload,
        }
        if item_id:
            body["item_id"] = item_id
        response = self.client.post(
            f"/sessions/{self.session_id}/events", json=body, headers=self.headers
        )
        assert response.status_code == 200, response.text
        self.last = response.json()
        self.action = self.last["action"]
        return self.action


def _mastery(db: Session, world: World) -> MasteryRow | None:
    db.expire_all()
    return db.get(MasteryRow, (uuid.UUID(world.student_share_id), LESSON_SKILL))


def _count(db: Session, model: type, world: World) -> int:
    db.expire_all()
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _events(db: Session, session_id: str, event_type: str) -> list[EventRow]:
    db.expire_all()
    return list(
        db.scalars(
            select(EventRow).where(
                EventRow.session_id == uuid.UUID(session_id), EventRow.event_type == event_type
            )
        ).all()
    )


# --- the lesson reaches the player -----------------------------------------------------------


def test_predict_and_worked_example_actions_carry_the_lesson(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    player = Player(client, world)
    assert player.action["type"] == "predict"
    lesson = player.action["lesson"]
    assert lesson["id"] == "LESSON.TWO_STEP" and lesson["skill_id"] == LESSON_SKILL
    assert [beat["kind"] for beat in lesson["beats"]][0] == "predict"
    player.send("predict_response", response="4")
    assert player.action["type"] == "worked_example"
    assert player.action["lesson"]["id"] == "LESSON.TWO_STEP"


def test_ready_student_gets_every_beat_in_the_authored_order(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    ready = Player(client, world)
    kinds = [beat["kind"] for beat in ready.action["lesson"]["beats"]]
    assert kinds == [
        "predict",
        "explore",
        "explain_scene",
        "worked_example",
        "faded_example",
        "explore",
        "check",
    ]
    assert ready.action["lesson"]["order"] == "problem_first"


def test_novice_gets_worked_example_first_and_keeps_it_after_the_prediction(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    # a prerequisite the student has not practised: R38 picks worked-example-first
    skill = db.get(SkillRow, LESSON_SKILL)
    assert skill is not None
    skill.prerequisites = ["MATH.PREREQ.EARLIER"]
    # known well enough that it is not taught first (p_known 0.9), but ladder level only 2
    db.add(
        MasteryRow(
            student_id=uuid.UUID(world.student_share_id),
            skill_id="MATH.PREREQ.EARLIER",
            p_known=0.9,
            attempts=3,
            unhinted_correct=2,
            hinted_correct=0,
            last_updated=datetime.now(UTC),
            ladder_level=2,
        )
    )
    db.commit()
    novice = Player(client, world)
    beats = [beat["kind"] for beat in novice.action["lesson"]["beats"]]
    assert beats == ["predict", "worked_example", "faded_example", "explore", "check"]
    assert novice.action["lesson"]["order"] == "worked_example_first"
    novice.send("predict_response", response="4")
    assert [b["kind"] for b in novice.action["lesson"]["beats"]] == beats


def test_faded_answer_is_checked_by_the_server_and_never_writes_bkt_or_fsrs(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    player = Player(client, world)
    mastery_before = _count(db, MasteryRow, world)
    cards_before = _count(db, ReviewCardRow, world)
    # a client "correct" flag is ignored: the server compares the response itself
    wrong = player.send("faded_answer", faded=0, response="7", correct=True)
    assert wrong["type"] == player.action["type"] and wrong["lesson_correct"] is False
    right = player.send("faded_answer", faded=0, response="x = 4")
    assert right["type"] == player.action["type"] and right["lesson_correct"] is True
    rows = _events(db, player.session_id, "faded_answer")
    assert [row.correct for row in rows] == [False, True]
    assert _count(db, MasteryRow, world) == mastery_before
    assert _count(db, ReviewCardRow, world) == cards_before
    assert _mastery(db, world) is None


def test_a_malformed_faded_answer_is_rejected(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    player = Player(client, world)
    player.send("faded_answer", faded=3, response="4")  # the lesson has no fourth faded example
    assert [r.correct for r in _events(db, player.session_id, "faded_answer")] == [False]
    assert player.action["rejected"] is True


def test_a_skill_without_a_lesson_keeps_the_plain_flow(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, PLAIN_SKILL)
    player = Player(client, world)
    assert player.action["type"] == "predict"
    assert "lesson" not in player.action


def test_draft_lessons_are_hidden_unless_drafts_are_allowed(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    settings.allow_draft_content = False
    player = Player(client, world)
    assert player.action["type"] == "predict"
    assert "lesson" not in player.action


# --- lesson beats never write BKT or FSRS; the check item writes once --------------------------


def test_lesson_beats_never_write_bkt_or_fsrs_and_the_check_item_writes_once(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    player = Player(client, world)
    player.send("predict_response", response="4")
    player.send("scene_answer", scene_id="SCENE.TWO_STEP.EXPLAIN", step=2, choice=0)
    player.send("scene_answer", scene_id="SCENE.TWO_STEP.EXPLAIN", step=2, choice=1)
    player.send(
        "interactive_result",
        widget_id="W.TWO_STEP.BALANCE",
        final_state=SOLVED,
        actions_count=9,
    )
    player.send(
        "interactive_result",
        widget_id="W.TWO_STEP.GRAPH",
        final_state={"x": 4},
        actions_count=3,
    )
    assert _mastery(db, world) is None  # no BKT row yet
    assert _count(db, ReviewCardRow, world) == 0
    player.send("continue")  # lesson finished: the first practice item is the check
    row = _mastery(db, world)
    assert row is not None
    assert (row.attempts, row.unhinted_correct, row.hinted_correct) == (0, 0, 0)
    assert abs(row.p_known - 0.2) < 1e-9  # p_init: nothing was learned from beats
    assert _count(db, ReviewCardRow, world) == 0
    assert player.action["type"] == "show_item"

    item_id = player.action["item_id"]
    player.send("answer", item_id, response="999", latency_ms=500)  # wrong first
    after_wrong = _mastery(db, world)
    assert after_wrong is not None and after_wrong.attempts == 1  # exactly one BKT update
    player.send("answer", item_id, response=ANSWERS[item_id], latency_ms=500)
    row = _mastery(db, world)
    assert row is not None and row.attempts == 1  # the retry does not update again
    assert row.p_known != 0.2


# --- server re-check of widget results ------------------------------------------------------------


def test_a_solved_widget_result_is_accepted_and_recorded(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    player = Player(client, world)
    player.send("predict_response", response="4")
    action = player.send(
        "interactive_result", widget_id="W.TWO_STEP.BALANCE", final_state=SOLVED, actions_count=9
    )
    assert action["rejected"] is False and action["type"] == "worked_example"
    (event,) = _events(db, player.session_id, "interactive_result")
    assert event.correct is True and event.payload["_verdict"] == {"ok": True, "code": None}


def test_a_forged_widget_result_is_rejected_and_flagged(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    player = Player(client, world)
    player.send("predict_response", response="4")
    action = player.send(
        "interactive_result",
        widget_id="W.TWO_STEP.BALANCE",
        final_state=UNSOLVED,
        goal_met=True,  # the client's own claim is ignored
        solved=True,
    )
    assert action["rejected"] is True and action["guardrail_flag"] == "widget_goal_not_met"
    assert action["type"] == "worked_example"  # the session did not move
    (event,) = _events(db, player.session_id, "interactive_result")
    assert event.correct is False
    assert event.payload["_verdict"] == {"ok": False, "code": "widget_goal_not_met"}
    forged_graph = player.send(
        "interactive_result", widget_id="W.TWO_STEP.GRAPH", final_state={"x": 3.9}
    )
    assert forged_graph["rejected"] is True
    assert _mastery(db, world) is None


def test_unknown_and_malformed_widget_results_are_rejected(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    player = Player(client, world)
    player.send("predict_response", response="4")
    unknown = player.send("interactive_result", widget_id="W.NOPE", final_state=SOLVED)
    assert unknown["guardrail_flag"] == "widget_unknown"
    malformed = player.send("interactive_result", widget_id="W.TWO_STEP.BALANCE")
    assert malformed["guardrail_flag"] == "widget_result_malformed"


def test_lesson_events_outside_the_lesson_phase_are_rejected(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    player = Player(client, world)
    player.send("predict_response", response="4")
    player.send("continue")  # now in practice
    action = player.send("interactive_result", widget_id="W.TWO_STEP.BALANCE", final_state=SOLVED)
    assert action["rejected"] is True and action["guardrail_flag"] == "lesson_event_out_of_phase"


def test_scene_answers_are_checked_by_the_server_and_never_change_state(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    player = Player(client, world)
    player.send("predict_response", response="4")
    right = player.send("scene_answer", scene_id="SCENE.TWO_STEP.EXPLAIN", step=2, choice=0)
    wrong = player.send("scene_answer", scene_id="SCENE.TWO_STEP.EXPLAIN", step=2, choice=2)
    assert right["type"] == wrong["type"] == "worked_example"
    assert right["rejected"] is False and wrong["rejected"] is False
    events = _events(db, player.session_id, "scene_answer")
    assert [e.correct for e in sorted(events, key=lambda e: e.created_at)] == [True, False]
    bad = player.send("scene_answer", scene_id="SCENE.NOPE", step=0, choice=0)
    assert bad["guardrail_flag"] == "scene_unknown"


def test_a_repeated_lesson_event_is_not_recorded_twice(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world, LESSON_SKILL)
    player = Player(client, world)
    player.send("predict_response", response="4")
    event_id = str(uuid.uuid4())
    for _ in range(2):
        player.send(
            "interactive_result",
            event_id=event_id,
            widget_id="W.TWO_STEP.BALANCE",
            final_state=SOLVED,
        )
    assert player.last["duplicate"] is True
    assert len(_events(db, player.session_id, "interactive_result")) == 1


# --- dev endpoints ------------------------------------------------------------------------------


def test_dev_lesson_endpoints_are_404_unless_dev_tools(client: TestClient) -> None:
    for path in ("/dev/lessons", "/dev/lessons/LESSON.TWO_STEP"):
        assert client.get(path).status_code == 404
    verify = client.post("/dev/widgets/verify", json={})
    assert verify.status_code == 404


def test_dev_lessons_list_get_and_verify(client: TestClient) -> None:
    settings.dev_tools = True
    settings.allow_draft_content = True
    listed = client.get("/dev/lessons").json()["lessons"]
    ids = [row["id"] for row in listed]
    assert ids == sorted(ids) and len(ids) == 12
    assert {"LESSON.FRACTION", "LESSON.INVERSE", "LESSON.ONE_STEP", "LESSON.TWO_STEP"} <= set(ids)
    assert all(row["skill_id"] and row["title"] and row["beats"] for row in listed)
    one = client.get("/dev/lessons/LESSON.TWO_STEP").json()
    assert one["skill_id"] == LESSON_SKILL and len(one["beats"]) == 7
    assert client.get("/dev/lessons/LESSON.NOPE").status_code == 404
    ok = client.post(
        "/dev/widgets/verify",
        json={
            "lesson_id": "LESSON.TWO_STEP",
            "widget_id": "W.TWO_STEP.BALANCE",
            "final_state": SOLVED,
        },
    )
    assert ok.json() == {"ok": True, "code": None}
    forged = client.post(
        "/dev/widgets/verify",
        json={
            "lesson_id": "LESSON.TWO_STEP",
            "widget_id": "W.TWO_STEP.BALANCE",
            "final_state": UNSOLVED,
        },
    )
    assert forged.json() == {"ok": False, "code": "widget_goal_not_met"}
    missing = client.post(
        "/dev/widgets/verify",
        json={"lesson_id": "LESSON.TWO_STEP", "widget_id": "W.NOPE", "final_state": SOLVED},
    )
    assert missing.json() == {"ok": False, "code": "widget_unknown"}
