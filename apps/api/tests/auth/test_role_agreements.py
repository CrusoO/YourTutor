"""Role agreements, the age question and adult learners (in-memory SQLite)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import agreements
from app.auth.age import resolve_is_adult
from app.auth.consent import active_consent, active_scopes
from app.auth.sender import MemoryOtpSender
from app.classes import service as class_service
from app.config import settings
from app.db.models import AgreementRow, ConsentRow, StudentRow
from tests.conftest import auth_header, seed_user, signup

GUARDIAN_ALL = [i.id for i in agreements.CATALOG["guardian"]]
GUARDIAN_REQUIRED = [i.id for i in agreements.CATALOG["guardian"] if i.required]
ADULT_ALL = [i.id for i in agreements.CATALOG["adult"]]
TEACHER_ALL = [i.id for i in agreements.CATALOG["teacher"]]


@pytest.fixture(autouse=True)
def _minors() -> None:
    settings.adult_learners_assumed = False  # restored by the conftest fixture
    class_service.account_limiter.reset()


def _accept(
    client: TestClient, token: str, role: str, items: list[str], version: str | None = None
):
    return client.post(
        f"/agreements/{role}",
        json={"version": version or agreements.VERSION, "items": items},
        headers=auth_header(token),
    )


def _child(client: TestClient, token: str, name: str = "Riya") -> str:
    made = client.post(
        "/students",
        json={"display_name": name, "grade": 9, "board": "bhutan"},
        headers=auth_header(token),
    )
    assert made.status_code == 200, made.text
    return str(made.json()["id"])


# ---- pure rules -------------------------------------------------------------------------------


def test_required_items_are_the_service_and_the_rest_are_choices() -> None:
    for role in ("guardian", "adult"):
        required = {i.id for i in agreements.CATALOG[role] if i.required}
        optional = {i.id for i in agreements.CATALOG[role] if not i.required}
        assert {"tutoring", "ai_processing"} <= required
        # teacher sharing, reports, research and the rest are never forced
        assert {"teacher_share", "progress_reports", "research_pseudonymised"} <= optional
    assert all(i.required for i in agreements.CATALOG["teacher"])
    assert len(agreements.CATALOG["teacher"]) == 3


def test_items_error_names_what_is_wrong() -> None:
    assert agreements.items_error("guardian", GUARDIAN_ALL) is None
    assert agreements.items_error("guardian", GUARDIAN_REQUIRED) is None
    assert "required" in (agreements.items_error("guardian", ["tutoring"]) or "")
    assert "unknown" in (agreements.items_error("guardian", [*GUARDIAN_ALL, "ads"]) or "")
    assert agreements.items_error("nobody", []) == "unknown role"
    assert agreements.scopes_of("guardian", GUARDIAN_REQUIRED) == ["tutoring", "ai_processing"]


@pytest.mark.parametrize(
    ("birth_year", "declared", "adult"),
    [
        (2000, None, True),
        (2009, None, False),
        (2008, None, False),  # 18 by year: not an adult unless the birthday is declared
        (2008, True, True),
        (None, True, True),
        (None, False, False),
    ],
)
def test_age_answer(birth_year: int | None, declared: bool | None, adult: bool) -> None:
    assert resolve_is_adult(birth_year, declared, date(2026, 11, 11)) is adult


def test_age_answer_must_be_usable() -> None:
    with pytest.raises(ValueError):
        resolve_is_adult(None, None, date(2026, 11, 11))
    with pytest.raises(ValueError):
        resolve_is_adult(2090, None, date(2026, 11, 11))
    with pytest.raises(ValueError):
        resolve_is_adult(1800, None, date(2026, 11, 11))


# ---- the catalog and a guardian ----------------------------------------------------------------


def test_catalog_is_public_and_marks_required_items(client: TestClient) -> None:
    body = client.get("/agreements/guardian").json()
    assert body["version"] == agreements.VERSION
    by_id = {i["id"]: i for i in body["items"]}
    assert by_id["tutoring"]["required"] is True
    assert by_id["teacher_share"]["required"] is False
    assert client.get("/agreements/stranger").status_code == 404


def test_a_guardian_must_tick_the_required_items_and_each_is_separate(
    client: TestClient, sender: MemoryOtpSender
) -> None:
    token = signup(client, sender, "g@example.com")
    assert client.get("/auth/me", headers=auth_header(token)).json()["agreements"] == [
        "guardian",
        "adult",
    ]
    assert _accept(client, token, "guardian", ["tutoring"]).status_code == 400
    assert _accept(client, token, "guardian", [*GUARDIAN_ALL, "ads"]).status_code == 400
    assert _accept(client, token, "guardian", GUARDIAN_ALL, "old-version").status_code == 409
    # an old or missing token and the wrong role are refused
    assert _accept(client, token, "teacher", TEACHER_ALL).status_code == 403
    done = _accept(client, token, "guardian", GUARDIAN_REQUIRED)
    assert done.status_code == 200, done.text
    assert done.json()["needed"] == []
    assert client.get("/auth/me", headers=auth_header(token)).json()["agreements"] == []


def test_one_screen_grants_every_scope_of_every_child_including_teacher_share(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    token = signup(client, sender, "g@example.com")
    first = _child(client, token, "Ava")
    assert _accept(client, token, "guardian", GUARDIAN_ALL).status_code == 200
    db.expire_all()
    consent = active_consent(db, uuid.UUID(first))
    assert consent is not None
    scopes = set(consent.scopes)
    assert scopes == {
        "tutoring",
        "ai_processing",
        "teacher_share",
        "free_text",
        "uploads",
        "research_pseudonymised",
    }
    # the next child needs no second tick: the same items become that child's consent
    second = _child(client, token, "Ben")
    db.expire_all()
    assert "teacher_share" in active_scopes(db, uuid.UUID(second))


def test_a_class_join_is_active_at_once_under_the_guardians_agreement(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    seed_user(db, "teacher", "t@example.com")
    teacher = signup(client, sender, "t@example.com")
    made = client.post(
        "/classes", json={"name": "10A", "board": "bhutan"}, headers=auth_header(teacher)
    )
    class_id = made.json()["id"]
    code = client.post(
        f"/classes/{class_id}/join-code", json={}, headers=auth_header(teacher)
    ).json()["code"]
    guardian = signup(client, sender, "g@example.com")
    assert _accept(client, guardian, "guardian", GUARDIAN_ALL).status_code == 200
    sid = _child(client, guardian)
    client.post(f"/students/{sid}/pin", json={"pin": "1234"}, headers=auth_header(guardian))
    student = client.post(f"/students/{sid}/pin/verify", json={"pin": "1234"}).json()[
        "access_token"
    ]
    joined = client.post("/classes/join", json={"code": code}, headers=auth_header(student))
    assert joined.status_code == 200, joined.text
    assert joined.json()["status"] == "active" and joined.json()["shared"] is True


def test_withdrawing_an_optional_item_takes_effect_at_once(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    token = signup(client, sender, "g@example.com")
    sid = uuid.UUID(_child(client, token))
    _accept(client, token, "guardian", GUARDIAN_ALL)
    res = client.post(
        "/agreements/guardian/withdraw",
        json={"item": "teacher_share"},
        headers=auth_header(token),
    )
    assert res.status_code == 200, res.text
    db.expire_all()
    scopes = active_scopes(db, sid)
    assert "teacher_share" not in scopes and "tutoring" in scopes
    # still complete: nothing more is asked at the next sign-in
    assert res.json()["needed"] == []
    # the history is kept: the first row is closed, not deleted
    rows = db.scalars(select(AgreementRow).where(AgreementRow.role == "guardian")).all()
    assert len(rows) == 2 and sum(1 for r in rows if r.revoked_at is None) == 1
    # withdrawing what was never agreed
    again = client.post(
        "/agreements/guardian/withdraw",
        json={"item": "teacher_share"},
        headers=auth_header(token),
    )
    assert again.status_code == 404


def test_withdrawing_a_required_item_closes_the_childs_consent(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    token = signup(client, sender, "g@example.com")
    sid = uuid.UUID(_child(client, token))
    _accept(client, token, "guardian", GUARDIAN_ALL)
    res = client.post(
        "/agreements/guardian/withdraw", json={"item": "ai_processing"}, headers=auth_header(token)
    )
    assert res.status_code == 200
    db.expire_all()
    assert active_consent(db, sid) is None
    assert res.json()["needed"] == ["guardian", "adult"]  # asked again on the next sign-in
    assert db.scalars(select(ConsentRow).where(ConsentRow.student_id == sid)).all()  # history kept


# ---- teachers ----------------------------------------------------------------------------------


def test_the_teacher_terms_are_three_required_promises(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    seed_user(db, "teacher", "t@example.com")
    token = signup(client, sender, "t@example.com")
    assert client.get("/auth/me", headers=auth_header(token)).json()["agreements"] == ["teacher"]
    assert _accept(client, token, "teacher", TEACHER_ALL[:2]).status_code == 400
    assert _accept(client, token, "guardian", GUARDIAN_ALL).status_code == 403
    assert _accept(client, token, "teacher", TEACHER_ALL).status_code == 200
    assert client.get("/auth/me", headers=auth_header(token)).json()["agreements"] == []


def test_with_the_switch_on_a_teacher_without_the_terms_is_refused(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    seed_user(db, "teacher", "t@example.com")
    token = signup(client, sender, "t@example.com")
    body = {"name": "10A", "board": "bhutan"}
    assert client.post("/classes", json=body, headers=auth_header(token)).status_code == 200
    settings.role_agreements_required = True
    refused = client.post("/classes", json=body, headers=auth_header(token))
    assert refused.status_code == 403 and refused.json()["detail"] == "agreement_required"
    assert client.get("/teacher/classes", headers=auth_header(token)).status_code == 200
    _accept(client, token, "teacher", TEACHER_ALL)
    assert client.post("/classes", json=body, headers=auth_header(token)).status_code == 200


# ---- adult learners and the one place age is read ----------------------------------------------


def _adult_body(**over: object) -> dict[str, object]:
    body: dict[str, object] = {
        "version": agreements.VERSION,
        "accepted": ADULT_ALL,
        "declared_adult": True,
        "grade": 9,
        "board": "bhutan",
    }
    body.update(over)
    return body


def test_an_adult_agrees_for_themself_and_is_recorded_as_an_adult(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    token = signup(client, sender, "a@example.com")
    res = client.post("/adult/start", json=_adult_body(), headers=auth_header(token))
    assert res.status_code == 200, res.text
    sid = uuid.UUID(res.json()["student_id"])
    student = db.get(StudentRow, sid)
    assert student is not None and student.is_adult is True and student.birth_year is None
    assert class_service.learner_is_adult(db, student) is True  # even with adults_assumed False
    assert "teacher_share" in active_scopes(db, sid)  # the adult's own ticks
    assert client.get("/auth/me", headers=auth_header(token)).json()["agreements"] == []
    # the learner session works, and a returning adult can get one again
    assert (
        client.get("/students/me/today", headers=auth_header(res.json()["token"])).status_code
        == 200
    )
    again = client.post("/adult/session", headers=auth_header(token))
    assert again.status_code == 200 and again.json()["student_id"] == str(sid)
    assert (
        client.post("/adult/start", json=_adult_body(), headers=auth_header(token)).status_code
        == 409
    )


def test_an_adults_unticked_options_are_not_granted(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    token = signup(client, sender, "a@example.com")
    items = [i for i in ADULT_ALL if i not in {"teacher_share", "uploads"}]
    res = client.post("/adult/start", json=_adult_body(accepted=items), headers=auth_header(token))
    scopes = active_scopes(db, uuid.UUID(res.json()["student_id"]))
    assert "teacher_share" not in scopes and "uploads" not in scopes and "tutoring" in scopes


def test_a_child_is_not_let_in_as_an_adult(client: TestClient, sender: MemoryOtpSender) -> None:
    token = signup(client, sender, "a@example.com")
    young = date.today().year - 14
    refused = client.post(
        "/adult/start",
        json=_adult_body(birth_year=young, declared_adult=None),
        headers=auth_header(token),
    )
    assert refused.status_code == 403 and refused.json()["detail"] == "not_adult"
    declared_no = client.post(
        "/adult/start", json=_adult_body(declared_adult=False), headers=auth_header(token)
    )
    assert declared_no.status_code == 403
    missing = client.post(
        "/adult/start", json=_adult_body(declared_adult=None), headers=auth_header(token)
    )
    assert missing.status_code == 400
    unticked = client.post(
        "/adult/start", json=_adult_body(accepted=["tutoring"]), headers=auth_header(token)
    )
    assert unticked.status_code == 400
    assert client.post("/adult/start", json=_adult_body()).status_code == 401


def test_the_birth_year_is_the_only_age_detail_kept(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    token = signup(client, sender, "a@example.com")
    res = client.post(
        "/adult/start",
        json=_adult_body(birth_year=date.today().year - 30, declared_adult=None),
        headers=auth_header(token),
    )
    assert res.status_code == 200, res.text
    student = db.get(StudentRow, uuid.UUID(res.json()["student_id"]))
    assert student is not None and student.birth_year == date.today().year - 30
    assert student.is_adult is True
    # no other age-shaped column exists on the learner row
    names = {c.key for c in StudentRow.__table__.columns}
    assert {n for n in names if "birth" in n or "dob" in n or n.startswith("age")} == {"birth_year"}


def test_a_learner_never_asked_falls_back_to_the_deployment_stand_in(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    token = signup(client, sender, "g@example.com")
    student = db.get(StudentRow, uuid.UUID(_child(client, token)))
    assert student is not None and student.is_adult is None
    settings.adult_learners_assumed = False
    assert class_service.learner_is_adult(db, student) is False
    settings.adult_learners_assumed = True
    assert class_service.learner_is_adult(db, student) is True
    student.is_adult = False  # an answer always beats the stand-in
    assert class_service.learner_is_adult(db, student) is False
