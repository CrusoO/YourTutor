"""A child's limited-mode profile, the guardian's approval, and a child login made by a guardian."""

from __future__ import annotations

import re
import uuid
from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import agreements, children
from app.auth.consent import active_scopes, is_guest
from app.auth.notify import DefaultNotifier, MemoryNotifier, NotifyUnavailable, set_notifier
from app.auth.security import now_utc
from app.auth.sender import MemoryOtpSender
from app.classes import service as class_service
from app.config import settings
from app.db.models import (
    AuthSessionRow,
    GuardianApprovalRow,
    StudentRow,
    UserRow,
)
from app.retention import run_job
from tests.conftest import auth_header, signup

GUARDIAN_ALL = [i.id for i in agreements.CATALOG["guardian"]]
GUARDIAN_REQUIRED = [i.id for i in agreements.CATALOG["guardian"] if i.required]
CHILD_ACK = [i.id for i in agreements.CATALOG["child"]]
PHONE = "+15550001234"


@pytest.fixture(autouse=True)
def _on() -> Generator[MemoryNotifier, None, None]:
    settings.child_profiles_enabled = True  # restored by the conftest fixture
    settings.adult_learners_assumed = False
    settings.public_web_url = "https://app.example/guardian"
    box = MemoryNotifier()
    set_notifier(box)
    yield box
    set_notifier(DefaultNotifier())


def _start(client: TestClient, contact: str = "mum@example.com", **over: object):
    body: dict[str, object] = {
        "nickname": "Tiger",
        "curriculum_id": "bhutan",
        "grade": 9,
        "guardian_contact": contact,
        "acknowledged": CHILD_ACK,
    }
    body.update(over)
    return client.post("/children/start", json=body)


def _token(box: MemoryNotifier, contact: str) -> str:
    match = re.search(r"/approve#([\w-]+)", box.last(contact))
    assert match, box.last(contact)
    return match.group(1)


def _approve(client: TestClient, token: str, items: list[str] | None = None, **over: object):
    body: dict[str, object] = {
        "token": token,
        "version": agreements.VERSION,
        "accepted": items if items is not None else GUARDIAN_ALL,
    }
    body.update(over)
    return client.post("/approvals/approve", json=body)


def test_it_is_off_until_switched_on(client: TestClient) -> None:
    settings.child_profiles_enabled = False
    assert _start(client).status_code == 404
    assert client.post("/approvals/lookup", json={"token": "x" * 20}).status_code == 404


def test_a_pending_profile_is_guest_mode_and_stores_nothing_personal(
    client: TestClient, db: Session, _on: MemoryNotifier
) -> None:
    res = _start(client)
    assert res.status_code == 200, res.text
    body = res.json()
    sid = uuid.UUID(body["student_id"])
    assert body["state"] == "pending" and body["display_name"] == "Guest"
    assert is_guest(db, sid)
    assert active_scopes(db, sid) == {"tutoring"}
    student = db.get(StudentRow, sid)
    assert student is not None and student.display_name == "Guest"
    assert student.is_adult is None and student.birth_year is None and student.username is None
    assert student.site_id is None and student.onboarding is None
    # the nickname is on the approval row only, never on a learner or user row
    users = db.scalars(select(UserRow)).all()
    assert all("Tiger" not in (u.email or "") for u in users)
    assert db.scalar(select(GuardianApprovalRow.nickname)) == "Tiger"
    # the guardian was told, with a link whose token is after the "#"
    assert "mum@example.com" in _on.sent
    assert "https://app.example/approve#" in _on.last("mum@example.com")
    # the child can ask what is going on, and the student token cannot reach a guardian screen
    status = client.get("/children/me/status", headers=auth_header(body["token"]))
    assert status.json()["state"] == "pending"
    assert client.get("/parents/me/export", headers=auth_header(body["token"])).status_code == 403
    # a pending child cannot join a class (guest rule)
    assert (
        client.post(
            "/classes/join", json={"code": "abcd-2345"}, headers=auth_header(body["token"])
        ).status_code
        == 409
    )


def test_the_start_form_refuses_what_it_must(client: TestClient, db: Session) -> None:
    assert _start(client, acknowledged=["ack_limited_mode"]).status_code == 400
    assert _start(client, contact="not a contact").status_code == 400
    assert _start(client, nickname="a@b.com").status_code == 400
    assert _start(client, nickname="98765 43210").status_code == 400
    assert _start(client, surname="Sharma").status_code == 422  # no extra personal fields
    assert _start(client, school="DPS").status_code == 422
    assert db.scalars(select(StudentRow)).all() == []  # nothing was created by any of that


def test_the_guardian_approves_with_no_account_and_the_profile_unlocks(
    client: TestClient, db: Session, _on: MemoryNotifier
) -> None:
    started = _start(client).json()
    sid = uuid.UUID(started["student_id"])
    token = _token(_on, "mum@example.com")
    seen = client.post("/approvals/lookup", json={"token": token})
    assert seen.status_code == 200, seen.text
    assert seen.json()["nickname"] == "Tiger" and seen.json()["grade"] == 9
    assert "mum@example.com" not in seen.text  # the contact is not echoed back
    assert {i["id"] for i in seen.json()["agreement"]["items"]} == set(GUARDIAN_ALL)

    # required items missing, and a stale version, are refused and change nothing
    assert _approve(client, token, ["tutoring"]).status_code == 400
    assert _approve(client, token, version="old").status_code == 409
    assert is_guest(db, sid)

    done = _approve(client, token)
    assert done.status_code == 200, done.text
    out = done.json()
    db.expire_all()
    student = db.get(StudentRow, sid)
    assert student is not None
    assert student.display_name == "Tiger" and student.is_adult is False
    assert not is_guest(db, sid)
    assert active_scopes(db, sid) == set(GUARDIAN_ALL) - {"confirm_guardian", "progress_reports"}
    assert "teacher_share" in active_scopes(db, sid)
    # the approval row and the hidden guest owner are gone; the single use is spent
    assert db.scalars(select(GuardianApprovalRow)).all() == []
    assert not db.scalars(select(UserRow).where(UserRow.role == "guest")).all()
    assert client.post("/approvals/lookup", json={"token": token}).status_code == 404
    assert _approve(client, token).status_code == 404
    # the guardian is signed in as a new guardian account and sees the child
    me = client.get("/auth/me", headers=auth_header(out["access_token"])).json()
    assert me["role"] == "parent" and me["email"] == "mum@example.com" and me["agreements"] == []
    export = client.get("/parents/me/export", headers=auth_header(out["access_token"])).json()
    assert [s["display_name"] for s in export["students"]] == ["Tiger"]
    # the child's own session shows the unlocked state
    status = client.get("/children/me/status", headers=auth_header(started["token"]))
    assert status.json() == {"state": "approved", "display_name": "Tiger"}


def test_a_class_join_is_active_after_approval_because_teacher_share_was_ticked(
    client: TestClient, sender: MemoryOtpSender, db: Session, _on: MemoryNotifier
) -> None:
    from tests.conftest import seed_user

    seed_user(db, "teacher", "t@example.com")
    teacher = signup(client, sender, "t@example.com")
    class_id = client.post(
        "/classes", json={"name": "10A", "board": "bhutan"}, headers=auth_header(teacher)
    ).json()["id"]
    code = client.post(
        f"/classes/{class_id}/join-code", json={}, headers=auth_header(teacher)
    ).json()["code"]
    started = _start(client).json()
    _approve(client, _token(_on, "mum@example.com"))
    joined = client.post(
        "/classes/join", json={"code": code}, headers=auth_header(started["token"])
    )
    assert joined.status_code == 200, joined.text
    assert joined.json()["status"] == "active"


def test_the_guardian_can_correct_the_class_and_keep_choices_optional(
    client: TestClient, db: Session, _on: MemoryNotifier
) -> None:
    started = _start(client, curriculum_id="cbse", grade=10, subject="maths").json()
    sid = uuid.UUID(started["student_id"])
    token = _token(_on, "mum@example.com")
    seen = client.post("/approvals/lookup", json={"token": token}).json()
    assert (seen["grade"], seen["curriculum_id"]) == (10, "cbse")
    done = _approve(client, token, GUARDIAN_REQUIRED, grade=9, curriculum_id="bhutan")
    assert done.status_code == 200, done.text
    db.expire_all()
    student = db.get(StudentRow, sid)
    assert student is not None and (student.grade, student.curriculum_id) == (9, "bhutan")
    assert active_scopes(db, sid) == {"tutoring", "ai_processing"}  # unticked means not granted
    # a grade or board that does not exist is refused before anything changes
    again = _start(client, contact="dad@example.com").json()
    bad = _approve(client, _token(_on, "dad@example.com"), grade=12, curriculum_id="nowhere")
    assert bad.status_code == 400
    assert db.get(StudentRow, uuid.UUID(again["student_id"])) is not None


def test_a_second_child_does_not_change_the_first_childs_choices(
    client: TestClient, db: Session, _on: MemoryNotifier
) -> None:
    a = _start(client).json()
    _approve(client, _token(_on, "mum@example.com"), GUARDIAN_ALL)
    b = _start(client, nickname="Lion").json()
    _approve(client, _token(_on, "mum@example.com"), GUARDIAN_REQUIRED)
    db.expire_all()
    assert "teacher_share" in active_scopes(db, uuid.UUID(a["student_id"]))
    assert "teacher_share" not in active_scopes(db, uuid.UUID(b["student_id"]))
    guardians = db.scalars(select(UserRow).where(UserRow.role == "parent")).all()
    assert len(guardians) == 1  # the same contact is the same guardian account


def test_a_phone_contact_makes_a_phone_account(
    client: TestClient, db: Session, _on: MemoryNotifier
) -> None:
    assert _start(client, contact="+1 555 000 1234").status_code == 200
    out = _approve(client, _token(_on, PHONE)).json()
    user = db.scalar(select(UserRow).where(UserRow.phone == PHONE))
    assert user is not None and user.email.endswith("@phone.invalid")
    me = client.get("/auth/me", headers=auth_header(out["access_token"])).json()
    assert me["user_id"] == str(user.id)


def test_a_staff_address_cannot_be_taken_over_by_a_typed_contact(
    client: TestClient, db: Session, _on: MemoryNotifier
) -> None:
    from tests.conftest import seed_user

    seed_user(db, "teacher", "teacher@example.com")
    _start(client, contact="teacher@example.com")
    res = _approve(client, _token(_on, "teacher@example.com"))
    assert res.status_code == 409


def test_the_guardian_can_say_no_and_nothing_is_kept(
    client: TestClient, db: Session, _on: MemoryNotifier
) -> None:
    started = _start(client).json()
    sid = uuid.UUID(started["student_id"])
    token = _token(_on, "mum@example.com")
    assert client.post("/approvals/decline", json={"token": token}).json() == {"status": "declined"}
    db.expire_all()
    assert db.get(StudentRow, sid) is None
    assert db.scalars(select(GuardianApprovalRow)).all() == []
    assert not db.scalars(select(UserRow)).all()
    assert not db.scalars(select(AuthSessionRow).where(AuthSessionRow.student_id == sid)).all()
    assert client.post("/approvals/decline", json={"token": token}).status_code == 404


def test_the_link_expires_and_the_clean_up_removes_the_profile(
    client: TestClient, db: Session, _on: MemoryNotifier
) -> None:
    started = _start(client).json()
    sid = uuid.UUID(started["student_id"])
    token = _token(_on, "mum@example.com")
    row = db.scalar(select(GuardianApprovalRow))
    assert row is not None
    row.expires_at = now_utc() - timedelta(minutes=1)
    db.commit()
    assert client.post("/approvals/lookup", json={"token": token}).status_code == 404
    assert _approve(client, token).status_code == 404
    assert (
        client.get("/children/me/status", headers=auth_header(started["token"])).json()["state"]
        == "expired"
    )
    assert (
        run_job(db, "approvals", dry_run=True)
        == "approvals: would delete 1 expired child profile(s)"
    )
    assert db.get(StudentRow, sid) is not None
    assert run_job(db, "approvals") == "approvals: deleted 1 expired child profile(s)"
    db.expire_all()
    assert db.get(StudentRow, sid) is None
    assert not db.scalars(select(UserRow)).all()
    assert run_job(db, "approvals") == "approvals: deleted 0 expired child profile(s)"  # idempotent


def test_a_new_link_replaces_the_old_one(client: TestClient, _on: MemoryNotifier) -> None:
    started = _start(client).json()
    old = _token(_on, "mum@example.com")
    again = client.post("/children/me/resend", headers=auth_header(started["token"]))
    assert again.status_code == 200, again.text
    new = _token(_on, "mum@example.com")
    assert new != old
    assert client.post("/approvals/lookup", json={"token": old}).status_code == 404
    assert client.post("/approvals/lookup", json={"token": new}).status_code == 200


def test_links_to_one_contact_are_limited_so_a_child_cannot_pester_a_guardian(
    client: TestClient,
) -> None:
    limit = settings.approval_send_limit_contact
    codes = [_start(client).status_code for _ in range(limit + 1)]
    assert codes[:limit] == [200] * limit and codes[-1] == 429
    assert _start(client, contact="someone-else@example.com").status_code == 200


def test_if_the_link_cannot_be_sent_nothing_is_kept(client: TestClient, db: Session) -> None:
    class Down:
        def send(self, kind: str, contact: str, subject: str, text: str) -> None:
            raise NotifyUnavailable("down")

    set_notifier(Down())
    res = _start(client)
    assert res.status_code == 503 and res.json()["detail"]["code"] == "notice_unavailable"
    assert db.scalars(select(StudentRow)).all() == []
    assert db.scalars(select(UserRow)).all() == []
    assert db.scalars(select(GuardianApprovalRow)).all() == []


def test_a_wrong_token_gets_the_one_answer(client: TestClient) -> None:
    for call in ("lookup", "decline"):
        res = client.post(f"/approvals/{call}", json={"token": "n" * 30})
        assert res.status_code == 404 and res.json()["detail"] == children.NOT_VALID


def test_children_are_never_tracked_the_pending_row_has_only_what_the_notice_says() -> None:
    columns = {c.key for c in GuardianApprovalRow.__table__.columns}
    assert columns == {
        "id",
        "student_id",
        "token_hash",
        "nickname",
        "contact",
        "contact_kind",
        "created_at",
        "expires_at",
    }
    assert not {c.key for c in StudentRow.__table__.columns} & {
        "ip",
        "user_agent",
        "device_id",
        "advertising_id",
    }


# ---- a guardian makes a child login ------------------------------------------------------------


def test_a_guardian_gives_a_child_a_short_username_and_pin(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    token = signup(client, sender, "g@example.com")
    sid = client.post(
        "/students",
        json={"display_name": "Ava", "grade": 9, "board": "bhutan"},
        headers=auth_header(token),
    ).json()["id"]
    made = client.post(f"/students/{sid}/login-details", headers=auth_header(token))
    assert made.status_code == 200, made.text
    username, pin = made.json()["username"], made.json()["pin"]
    assert len(username) == 8 and re.fullmatch(r"\d{4}", pin)
    login = client.post("/auth/student-login", json={"username": username, "pin": pin})
    assert login.status_code == 200, login.text
    child = client.get("/students/me/today", headers=auth_header(login.json()["access_token"]))
    assert child.status_code == 200
    # the username is not case sensitive; a wrong pin or name is one plain refusal
    assert (
        client.post(
            "/auth/student-login", json={"username": username.upper(), "pin": pin}
        ).status_code
        == 200
    )
    wrong = "0000" if pin != "0000" else "1111"
    assert (
        client.post("/auth/student-login", json={"username": username, "pin": wrong}).status_code
        == 401
    )
    assert (
        client.post("/auth/student-login", json={"username": "nobody00", "pin": pin}).status_code
        == 401
    )
    # asking again keeps the name and replaces the pin
    again = client.post(f"/students/{sid}/login-details", headers=auth_header(token)).json()
    assert again["username"] == username
    # one of the two names is required
    assert client.post("/auth/student-login", json={"pin": pin}).status_code == 422
    # the family-code route still works as before
    fam = db.get(StudentRow, uuid.UUID(sid))
    assert fam is not None and fam.family_code


def test_the_pin_locks_after_too_many_wrong_tries(
    client: TestClient, sender: MemoryOtpSender
) -> None:
    token = signup(client, sender, "g@example.com")
    sid = client.post(
        "/students",
        json={"display_name": "Ava", "grade": 9, "board": "bhutan"},
        headers=auth_header(token),
    ).json()["id"]
    made = client.post(f"/students/{sid}/login-details", headers=auth_header(token)).json()
    wrong = "0000" if made["pin"] != "0000" else "1111"
    codes = [
        client.post(
            "/auth/student-login", json={"username": made["username"], "pin": wrong}
        ).status_code
        for _ in range(settings.pin_max_attempts + 1)
    ]
    assert codes[-1] == 423
    good = client.post(
        "/auth/student-login", json={"username": made["username"], "pin": made["pin"]}
    )
    assert good.status_code == 423


def test_only_the_childs_own_guardian_can_make_the_login(
    client: TestClient, sender: MemoryOtpSender
) -> None:
    mine = signup(client, sender, "g@example.com")
    other = signup(client, sender, "o@example.com")
    sid = client.post(
        "/students",
        json={"display_name": "Ava", "grade": 9, "board": "bhutan"},
        headers=auth_header(mine),
    ).json()["id"]
    assert (
        client.post(f"/students/{sid}/login-details", headers=auth_header(other)).status_code == 403
    )
    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    assert client.post(
        f"/students/{guest['student_id']}/login-details", headers=auth_header(mine)
    ).status_code in (403, 409)


def test_adults_assumed_is_not_what_decides_a_child_after_approval(
    client: TestClient, db: Session, _on: MemoryNotifier
) -> None:
    """In development adults are assumed; an approved child is recorded as a child regardless."""
    settings.adult_learners_assumed = True
    started = _start(client).json()
    _approve(client, _token(_on, "mum@example.com"))
    student = db.get(StudentRow, uuid.UUID(started["student_id"]))
    assert student is not None
    assert class_service.learner_is_adult(db, student) is False
