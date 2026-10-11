"""G5 step 2: first run and the warm-up offer. Login creates no session, "start from the
beginning" leads to practice, the warm-up is offered again after the second finished session, and
"not now" is remembered."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ItemRow, OverlayRow, SessionRow, SkillRow, StudentRow
from app.player.onboarding import (
    FIRST_RUN,
    REOFFER,
    InvalidChoice,
    apply_choice,
    offer_for,
)
from tests.conftest import auth_header

# --- pure rules ---------------------------------------------------------------------------------


def test_a_new_student_with_no_sessions_gets_the_first_run_offer() -> None:
    assert offer_for(None, total_sessions=0, ended_practice=0) == FIRST_RUN


def test_students_who_already_have_sessions_and_no_record_are_not_pestered() -> None:
    assert offer_for(None, total_sessions=3, ended_practice=3) is None


@pytest.mark.parametrize(
    ("state", "ended", "expected"),
    [
        ({"first_run": "start_beginning"}, 0, None),
        ({"first_run": "start_beginning"}, 1, None),
        ({"first_run": "start_beginning"}, 2, REOFFER),
        ({"first_run": "start_beginning"}, 9, REOFFER),
        ({"first_run": "warmup"}, 5, None),  # took it: never offered again
        ({"first_run": "start_beginning", "reoffer": "not_now"}, 9, None),  # respected
        ({"first_run": "start_beginning", "reoffer": "warmup"}, 9, None),
    ],
)
def test_the_reoffer_comes_after_the_second_finished_session_and_only_once(
    state: dict, ended: int, expected: str | None
) -> None:
    assert offer_for(state, total_sessions=ended, ended_practice=ended) == expected


def test_choices_must_match_the_offer() -> None:
    assert apply_choice(None, FIRST_RUN, "warmup")["first_run"] == "warmup"
    assert apply_choice(None, FIRST_RUN, "start_beginning")["first_run"] == "start_beginning"
    again = apply_choice({"first_run": "start_beginning"}, REOFFER, "not_now")
    assert again["reoffer"] == "not_now" and again["first_run"] == "start_beginning"
    for offer, choice in [(FIRST_RUN, "not_now"), (REOFFER, "start_beginning"), (None, "warmup")]:
        with pytest.raises(InvalidChoice):
            apply_choice(None, offer, choice)


# --- through the API ----------------------------------------------------------------------------

SKILL = "MATH.ONB.T"
OVERLAY = "OV.ONB"


def _guest(client: TestClient) -> tuple[dict, dict]:
    body = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    return body, auth_header(body["token"])


def _seed_content(db: Session, student_id: str) -> None:
    settings.allow_draft_content = True
    db.add(
        SkillRow(
            id=SKILL, title={"en": SKILL}, grade_band=[9], subject="math", prerequisites=[],
            related=[], misconceptions=[], status="approved",
            bkt={"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
        )
    )  # fmt: skip
    db.add(
        OverlayRow(id=OVERLAY, curriculum_id="bhutan", grade=9, chapter="linear_equations",
                   skill_ids=[SKILL], live=False)
    )  # fmt: skip
    for n, (stem, ans) in enumerate([("x + 4 = 10", "6"), ("x - 3 = 5", "8"), ("2x = 14", "7")]):
        db.add(
            ItemRow(
                id=f"ONB.P{n}", skill_ids=[SKILL], primary_skill=SKILL, difficulty=0.25,
                type="expression", pool="practice", role="procedure",
                stem={"en": f"Solve for x: {stem}", "ne": None, "as": None}, verify=None,
                options=[], answer={"sympy": ans, "accept": [ans]},
                solution_steps=[{"en": f"x = {ans}"}],
                hints=[{"level": 1, "en": "a"}, {"level": 2, "en": "b"}, {"level": 3, "en": ans}],
                prediction_prompt={"en": "?"}, misconception_rules=[], status="draft",
            )
        )  # fmt: skip
    student = db.get(StudentRow, uuid.UUID(student_id))
    assert student is not None
    student.current_chapter_id = OVERLAY
    student.context_key = {**(student.context_key or {}), "chapter_id": OVERLAY}
    db.commit()


def _end_practice_sessions(db: Session, student_id: str, how_many: int) -> None:
    now = datetime.now(UTC)
    for _ in range(how_many):
        db.add(
            SessionRow(
                id=uuid.uuid4(), student_id=uuid.UUID(student_id), started_at=now, ended_at=now,
                ended_reason="soft_cap", resumable=False, type="practice", active_ms=1000,
                last_active_at=now, plan={},
            )
        )  # fmt: skip
    db.commit()


def test_first_login_creates_no_session_and_offers_the_warmup(
    client: TestClient, db: Session
) -> None:
    guest, headers = _guest(client)
    today = client.get("/students/me/today", headers=headers).json()
    assert today["offer"] == "first_run" and today["resume"] is None
    assert db.scalar(select(func.count()).select_from(SessionRow)) == 0


def test_start_from_the_beginning_leads_to_practice_on_the_first_skill_to_learn(
    client: TestClient, db: Session
) -> None:
    guest, headers = _guest(client)
    _seed_content(db, guest["student_id"])
    answer = client.post(
        "/students/me/onboarding", json={"choice": "start_beginning"}, headers=headers
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["next"] == {"session_type": "practice"}
    assert client.get("/students/me/today", headers=headers).json()["offer"] is None
    started = client.post(
        "/sessions", json={"student_id": guest["student_id"], "type": "practice"}, headers=headers
    )
    assert started.status_code == 200, started.text
    action = started.json()["action"]
    assert action["skill_id"] == SKILL  # T: the first overlay skill below level 4
    assert action["type"] == "predict"


def test_choosing_the_warmup_points_at_a_diagnostic_and_stops_the_offers(
    client: TestClient, db: Session
) -> None:
    guest, headers = _guest(client)
    answer = client.post("/students/me/onboarding", json={"choice": "warmup"}, headers=headers)
    assert answer.json()["next"] == {"session_type": "diagnostic"}
    _end_practice_sessions(db, guest["student_id"], 3)
    assert client.get("/students/me/today", headers=headers).json()["offer"] is None


def test_the_warmup_is_offered_again_after_the_second_session_and_not_now_is_remembered(
    client: TestClient, db: Session
) -> None:
    guest, headers = _guest(client)
    client.post("/students/me/onboarding", json={"choice": "start_beginning"}, headers=headers)
    _end_practice_sessions(db, guest["student_id"], 1)
    assert client.get("/students/me/today", headers=headers).json()["offer"] is None
    _end_practice_sessions(db, guest["student_id"], 1)
    assert client.get("/students/me/today", headers=headers).json()["offer"] == "warmup_reoffer"
    no = client.post("/students/me/onboarding", json={"choice": "not_now"}, headers=headers)
    assert no.status_code == 200 and no.json()["next"] == {"session_type": "practice"}
    _end_practice_sessions(db, guest["student_id"], 5)
    assert client.get("/students/me/today", headers=headers).json()["offer"] is None


def test_a_choice_that_does_not_match_the_offer_is_refused(client: TestClient) -> None:
    _, headers = _guest(client)
    wrong = client.post("/students/me/onboarding", json={"choice": "not_now"}, headers=headers)
    assert wrong.status_code == 409
    assert (
        client.post(
            "/students/me/onboarding", json={"choice": "nonsense"}, headers=headers
        ).status_code
        == 422
    )
    client.post("/students/me/onboarding", json={"choice": "start_beginning"}, headers=headers)
    again = client.post("/students/me/onboarding", json={"choice": "warmup"}, headers=headers)
    assert again.status_code == 409  # nothing is on offer any more


def test_the_onboarding_endpoint_needs_a_student_login(client: TestClient) -> None:
    assert client.post("/students/me/onboarding", json={"choice": "warmup"}).status_code in {
        401,
        403,
    }
