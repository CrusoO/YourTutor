from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ItemRow, OverlayRow, SkillRow, StudentRow
from tests.conftest import World, auth_header


def _skill(db: Session, skill_id: str = "MATH.ALG.LIN1.SOLVE_ONE_STEP") -> None:
    if db.get(SkillRow, skill_id):
        return
    db.add(
        SkillRow(
            id=skill_id,
            title={"en": "One step"},
            grade_band=[9],
            subject="math",
            prerequisites=[],
            related=[],
            misconceptions=[],
            bkt={"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
            status="approved",
        )
    )


def _item(
    db: Session,
    item_id: str,
    *,
    pool: str,
    stem: str,
    answer: str,
    item_type: str = "expression",
    options: list | None = None,
) -> None:
    db.add(
        ItemRow(
            id=item_id,
            skill_ids=["MATH.ALG.LIN1.SOLVE_ONE_STEP"],
            primary_skill="MATH.ALG.LIN1.SOLVE_ONE_STEP",
            difficulty=0.25,
            type=item_type,
            pool=pool,
            stem={"en": stem, "ne": stem, "as": stem},
            verify=stem.split(": ", 1)[-1] if ": " in stem else stem,
            options=options or [],
            answer={"sympy": answer, "accept": [answer]},
            solution_steps=[{"en": f"x = {answer}"}],
            hints=[
                {"level": 1, "en": "What undoes the added number?"},
                {"level": 2, "en": "Subtract 4 from both sides."},
                {"level": 3, "en": f"x = {answer}"},
            ],
            prediction_prompt={"en": "Will x be smaller than 12?"},
            misconception_rules=[],
            status="draft",
        )
    )


def _seed_catalog(db: Session) -> None:
    _skill(db)
    if db.get(OverlayRow, "OV.TEST") is None:
        db.add(
            OverlayRow(
                id="OV.TEST",
                board="bhutan",
                grade=9,
                chapter="linear_equations",
                skill_ids=["MATH.ALG.LIN1.SOLVE_ONE_STEP"],
                live=False,
            )
        )
    _item(db, "ITEM.P.A", pool="practice", stem="Solve for x: x + 4 = 10", answer="6")
    _item(db, "ITEM.P.B", pool="practice", stem="Solve for x: x + 5 = 12", answer="7")
    _item(db, "ITEM.P.C", pool="practice", stem="Solve for x: x + 6 = 11", answer="5")
    _item(db, "ITEM.D.A", pool="diagnostic", stem="Solve for x: x + 2 = 9", answer="7")
    _item(db, "ITEM.D.B", pool="diagnostic", stem="Solve for x: x + 3 = 8", answer="5")
    _item(db, "ITEM.C.A", pool="checkpoint", stem="Solve for x: x + 1 = 6", answer="5")
    _item(db, "ITEM.C.B", pool="checkpoint", stem="Solve for x: x + 8 = 15", answer="7")
    db.commit()


def test_family_login_and_today(client: TestClient, world: World, db: Session) -> None:
    from app.db.models import StudentRow

    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    assert student.family_code
    login = client.post(
        "/auth/student-login",
        json={"family_code": student.family_code, "pin": "1234"},
    )
    assert login.status_code == 200, login.text
    today = client.get("/students/me/today", headers=auth_header(login.json()["access_token"]))
    assert today.status_code == 200
    body = today.json()
    assert body["goal_minutes"] == 15
    assert body["remaining_active_minutes"] == 15
    assert body["student_id"] == world.student_share_id


def test_practice_wrong_hint_reveal(client: TestClient, world: World, db: Session) -> None:
    settings.allow_draft_content = True
    _seed_catalog(db)
    from app.db.models import StudentRow

    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    student.current_chapter_id = "OV.TEST"
    db.commit()
    headers = auth_header(world.student_token)
    started = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "practice"},
        headers=headers,
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["id"]
    action = started.json()["action"]
    if action["type"] == "predict":
        nxt = client.post(
            f"/sessions/{session_id}/events",
            json={"client_event_id": str(uuid.uuid4()), "event_type": "predict_response", "payload": {"response": "yes"}},
            headers=headers,
        )
        assert nxt.status_code == 200
        action = nxt.json()["action"]
        assert action["type"] == "worked_example"
        nxt = client.post(
            f"/sessions/{session_id}/events",
            json={"client_event_id": str(uuid.uuid4()), "event_type": "continue", "payload": {}},
            headers=headers,
        )
        action = nxt.json()["action"]
    assert action["type"] in {"show_item", "warmup_item"}
    item_id = action["item_id"]
    wrong = client.post(
        f"/sessions/{session_id}/events",
        json={
            "client_event_id": str(uuid.uuid4()),
            "event_type": "answer",
            "item_id": item_id,
            "payload": {"response": "0", "latency_ms": 800},
        },
        headers=headers,
    )
    assert wrong.json()["action"]["type"] == "hint"
    assert wrong.json()["action"]["hint_level"] == 1
    retry = client.post(
        f"/sessions/{session_id}/events",
        json={
            "client_event_id": str(uuid.uuid4()),
            "event_type": "answer",
            "item_id": item_id,
            "payload": {"response": "1", "latency_ms": 400},
        },
        headers=headers,
    )
    assert retry.json()["action"]["type"] == "hint"
    reveal = client.post(
        f"/sessions/{session_id}/events",
        json={"client_event_id": str(uuid.uuid4()), "event_type": "show_solution", "item_id": item_id, "payload": {}},
        headers=headers,
    )
    assert reveal.json()["action"]["type"] == "reveal_solution"


def test_diagnostic_and_checkpoint_hide_hints(client: TestClient, world: World, db: Session) -> None:
    settings.allow_draft_content = True
    _seed_catalog(db)
    from app.db.models import StudentRow

    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    student.current_chapter_id = "OV.TEST"
    db.commit()
    headers = auth_header(world.student_token)
    started = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "diagnostic"},
        headers=headers,
    )
    action = started.json()["action"]
    assert action["type"] == "show_item"
    assert action["allow_hint"] is False
    assert action["dont_know_option"] is True
    nxt = client.post(
        f"/sessions/{started.json()['id']}/events",
        json={
            "client_event_id": str(uuid.uuid4()),
            "event_type": "answer",
            "item_id": action["item_id"],
            "payload": {"response": "i don't know"},
        },
        headers=headers,
    )
    assert nxt.status_code == 200
    assert nxt.json()["action"]["type"] in {"show_item", "end_session"}

    check = client.post(
        "/sessions",
        json={"student_id": world.student_share_id, "type": "checkpoint"},
        headers=headers,
    )
    action = check.json()["action"]
    assert action["allow_hint"] is False
    assert action["dont_know_option"] is False


def test_pilot_enrol_card(client: TestClient) -> None:
    settings.pilot_onboarding = True
    settings.pilot_key = "dev-pilot"
    response = client.post(
        "/admin/pilot/enrol",
        json={
            "first_name": "Pema",
            "grade": 9,
            "board": "bhutan",
            "paper_ref": "paper-42",
            "scopes": ["tutoring", "research_pseudonymised"],
        },
        headers={"X-Pilot-Key": "dev-pilot"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["first_name"] == "Pema"
    assert body["family_code"]
    assert body["pin"]
    assert body["paper_ref"] == "paper-42"
    login = client.post(
        "/auth/student-login",
        json={"family_code": body["family_code"], "pin": body["pin"]},
    )
    assert login.status_code == 200
