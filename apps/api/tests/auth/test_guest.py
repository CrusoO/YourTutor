"""G5 step 1: context options and guest start (no PII, no guardian, token for the student)."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ConsentRow, StudentRow, UserRow
from tests.conftest import auth_header


@pytest.fixture(autouse=True)
def _limit() -> Generator[None, None, None]:
    keep = settings.guest_start_limit_ip
    yield
    settings.guest_start_limit_ip = keep


def _start(client: TestClient, **over: object):
    body = {"curriculum_id": "bhutan", "grade": 9, "subject": "math"}
    body.update(over)
    return client.post("/guest/start", json=body)


def test_context_options_need_no_login_and_list_curriculum_grade_subject_and_languages(
    client: TestClient,
) -> None:
    response = client.get("/context/options")
    assert response.status_code == 200, response.text
    data = response.json()
    bhutan = next(c for c in data["curricula"] if c["id"] == "bhutan")
    nine = next(g for g in bhutan["grades"] if g["grade"] == 9)
    assert nine["subjects"][0]["id"] == "math"
    assert nine["subjects"][0]["books"][0]["id"] == "bhutan_class9"
    assert {lang["code"] for lang in data["languages"]} >= {"en"}
    assert "school" not in str(data).lower()  # no school list: students carry no school field


def test_guest_start_creates_a_student_with_a_working_token_and_no_personal_data(
    client: TestClient, db: Session
) -> None:
    response = _start(client, device_timezone="Asia/Kolkata", home_language="en")
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"student_id", "token", "display_name", "curriculum_id", "grade"}
    assert body["display_name"] == "Guest" and body["curriculum_id"] == "bhutan"
    today = client.get("/students/me/today", headers=auth_header(body["token"]))
    assert today.status_code == 200 and today.json()["student_id"] == body["student_id"]

    db.expire_all()
    student = db.scalars(select(StudentRow)).one()
    owner = db.get(UserRow, student.parent_id)
    assert owner is not None and owner.role == "guest"
    assert owner.email.endswith(".invalid")  # not a real address, so nothing to contact or leak
    assert student.pin_hash is None and student.family_code is None
    assert student.context_key and student.context_key["book_id"] == "bhutan_class9"
    assert student.grade == 9
    assert student.timezone  # resolved by the registry order
    assert db.scalars(select(ConsentRow)).all() == []


def test_two_guests_get_different_ids_and_owners(client: TestClient, db: Session) -> None:
    first, second = _start(client).json(), _start(client).json()
    assert first["student_id"] != second["student_id"]
    assert len({u.id for u in db.scalars(select(UserRow)).all()}) == 2


@pytest.mark.parametrize(
    "over",
    [
        {"curriculum_id": "nowhere"},
        {"grade": 99},
        {"grade": 0},
        {"home_language": "xx"},
        {"subject": "alchemy"},
    ],
)
def test_guest_start_rejects_unknown_context(client: TestClient, over: dict) -> None:
    assert _start(client, **over).status_code in {400, 422}


@pytest.mark.parametrize("field", ["display_name", "email", "phone", "school", "surname"])
def test_guest_start_refuses_any_personal_field(client: TestClient, field: str) -> None:
    assert _start(client, **{field: "something"}).status_code == 422


def test_guest_start_is_rate_limited_per_ip(client: TestClient) -> None:
    settings.guest_start_limit_ip = 2
    assert _start(client).status_code == 200
    assert _start(client).status_code == 200
    assert _start(client).status_code == 429
