"""Class join codes through the API (in-memory SQLite): pending until the guardian says yes."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.sender import MemoryOtpSender
from app.classes import service as class_service
from app.config import settings
from app.db.models import ClassMembershipRow, ClassRow, ConsentRow
from app.ratelimit import limiter
from tests.conftest import auth_header, seed_user, signup

SHARE = ["tutoring", "teacher_share"]


@pytest.fixture(autouse=True)
def _minors() -> None:
    settings.adult_learners_assumed = False  # restored by the conftest fixture
    limiter.reset()
    class_service.account_limiter.reset()


class Kit:
    def __init__(self, client: TestClient, sender: MemoryOtpSender, db: Session) -> None:
        self.client, self.sender, self.db = client, sender, db
        self.teacher = self.staff("teacher", "teacher@example.com")
        self.class_id = self.make_class(self.teacher)

    def staff(self, role: str, email: str) -> str:
        seed_user(self.db, role, email)
        return signup(self.client, self.sender, email)

    def make_class(self, token: str, name: str = "10A") -> str:
        res = self.client.post(
            "/classes", json={"name": name, "board": "bhutan"}, headers=auth_header(token)
        )
        assert res.status_code == 200, res.text
        return str(res.json()["id"])

    def family(self, email: str, name: str = "Riya") -> tuple[str, str, str]:
        """(guardian token, student id, student token)."""
        guardian = signup(self.client, self.sender, email)
        made = self.client.post(
            "/students",
            json={"display_name": name, "grade": 9, "board": "bhutan"},
            headers=auth_header(guardian),
        )
        assert made.status_code == 200, made.text
        sid = made.json()["id"]
        self.client.post(
            f"/students/{sid}/pin", json={"pin": "1234"}, headers=auth_header(guardian)
        )
        pin = self.client.post(f"/students/{sid}/pin/verify", json={"pin": "1234"})
        return guardian, sid, pin.json()["access_token"]

    def code(self, token: str | None = None, class_id: str | None = None, **body: object) -> str:
        res = self.client.post(
            f"/classes/{class_id or self.class_id}/join-code",
            json=body,
            headers=auth_header(token or self.teacher),
        )
        assert res.status_code == 200, res.text
        return str(res.json()["code"])

    def join(self, student_token: str, code: str, label: str | None = None):
        body: dict[str, object] = {"code": code}
        if label is not None:
            body["label"] = label
        return self.client.post("/classes/join", json=body, headers=auth_header(student_token))

    def view(self, token: str | None = None) -> dict:
        res = self.client.get(
            f"/teacher/classes/{self.class_id}/heatmap", headers=auth_header(token or self.teacher)
        )
        assert res.status_code == 200, res.text
        return res.json()

    def status(self, sid: str, class_id: str | None = None) -> str | None:
        self.db.expire_all()
        row = self.db.get(
            ClassMembershipRow, (uuid.UUID(class_id or self.class_id), uuid.UUID(sid))
        )
        return row.status if row else None


@pytest.fixture
def kit(client: TestClient, sender: MemoryOtpSender, db: Session) -> Kit:
    return Kit(client, sender, db)


def test_the_teacher_sees_a_code_once_and_the_database_holds_only_a_hash(kit: Kit) -> None:
    code = kit.code(expires_in_days=30)
    assert len(code) == 9 and code[4] == "-"
    row = kit.db.get(ClassRow, uuid.UUID(kit.class_id))
    assert row is not None and row.join_code_hash
    assert code.replace("-", "") not in row.join_code_hash
    status = kit.client.get(f"/classes/{kit.class_id}/join-code", headers=auth_header(kit.teacher))
    assert status.json()["enabled"] is True and "code" not in status.json()


def test_a_minor_joins_as_pending_and_nothing_is_shared(kit: Kit) -> None:
    code = kit.code()
    _, sid, token = kit.family("g1@example.com")
    res = kit.join(token, code, label="Ri")
    assert res.status_code == 200 and res.json()["status"] == "pending"
    assert res.json()["class_name"] == "10A"
    assert kit.status(sid) == "pending"
    assert kit.view()["students"] == []  # not listed
    mine = kit.client.get("/students/me/classes", headers=auth_header(token)).json()
    assert mine["classes"][0]["status"] == "pending"
    requests = kit.client.get(
        f"/classes/{kit.class_id}/join-requests", headers=auth_header(kit.teacher)
    ).json()
    assert requests == {"requests": [{"label": "Ri"}], "count": 1}


def test_the_teacher_list_shows_no_identifiers_until_active(kit: Kit) -> None:
    code = kit.code()
    _, sid, token = kit.family("g1@example.com", name="Riya Sharma")
    kit.join(token, code, label="riya@example.com")  # a bad label falls back
    text = kit.client.get(
        f"/classes/{kit.class_id}/join-requests", headers=auth_header(kit.teacher)
    ).text
    assert "Student 1" in text
    for leaked in (sid, "Riya", "g1@example.com", "riya@example.com"):
        assert leaked not in text
    count = kit.client.get(f"/classes/{kit.class_id}/join-code", headers=auth_header(kit.teacher))
    assert count.json()["pending_count"] == 1


def test_guardian_accept_records_teacher_share_and_activates(kit: Kit) -> None:
    code = kit.code()
    guardian, sid, token = kit.family("g1@example.com")
    kit.client.post(
        f"/students/{sid}/consent",
        json={"version": "v1", "scopes": ["tutoring", "ai_processing"]},
        headers=auth_header(guardian),
    )
    kit.join(token, code)
    waiting = kit.client.get("/parents/me/class-requests", headers=auth_header(guardian)).json()
    assert waiting["requests"][0]["class_name"] == "10A"
    assert waiting["requests"][0]["teacher"] == "teacher@example.com"
    res = kit.client.post(
        f"/parents/me/class-requests/{kit.class_id}/{sid}/accept", headers=auth_header(guardian)
    )
    assert res.status_code == 200 and res.json()["status"] == "active"
    assert kit.status(sid) == "active"
    assert [s["display_name"] for s in kit.view()["students"]] == ["Riya"]
    consents = kit.db.scalars(select(ConsentRow).where(ConsentRow.revoked_at.is_(None))).all()
    assert len(consents) == 1
    assert set(consents[0].scopes) == {"tutoring", "ai_processing", "teacher_share"}
    assert kit.client.get("/parents/me/class-requests", headers=auth_header(guardian)).json() == {
        "requests": []
    }


def test_guardian_decline_removes_the_pending_membership(kit: Kit) -> None:
    code = kit.code()
    guardian, sid, token = kit.family("g1@example.com")
    kit.join(token, code)
    res = kit.client.post(
        f"/parents/me/class-requests/{kit.class_id}/{sid}/decline", headers=auth_header(guardian)
    )
    assert res.status_code == 200
    assert kit.status(sid) is None
    assert kit.db.scalars(select(ConsentRow)).all() == []  # consent never touched


def test_another_guardian_cannot_decide_for_my_child(kit: Kit) -> None:
    code = kit.code()
    _, sid, token = kit.family("g1@example.com")
    other, _, _ = kit.family("g2@example.com", name="Other")
    kit.join(token, code)
    for verb in ("accept", "decline"):
        res = kit.client.post(
            f"/parents/me/class-requests/{kit.class_id}/{sid}/{verb}", headers=auth_header(other)
        )
        assert res.status_code == 403
    assert kit.status(sid) == "pending"


def test_an_adult_is_active_at_once_but_still_needs_teacher_share_to_be_seen(kit: Kit) -> None:
    settings.adult_learners_assumed = True
    code = kit.code()
    guardian, sid, token = kit.family("g1@example.com")
    assert kit.join(token, code).json()["status"] == "active"
    assert kit.view()["students"] == []  # no teacher_share yet
    kit.client.post(
        f"/students/{sid}/consent",
        json={"version": "v1", "scopes": SHARE},
        headers=auth_header(guardian),
    )
    assert len(kit.view()["students"]) == 1


def test_unknown_disabled_expired_and_malformed_codes_answer_the_same(kit: Kit) -> None:
    live = kit.code()
    other_class = kit.make_class(kit.teacher, "10B")
    expired = kit.code(class_id=other_class, expires_in_days=1)
    row = kit.db.get(ClassRow, uuid.UUID(other_class))
    assert row is not None and row.join_code_expires_at is not None
    row.join_code_expires_at = row.join_code_expires_at - timedelta(days=2)
    kit.db.commit()
    kit.client.delete(f"/classes/{kit.class_id}/join-code", headers=auth_header(kit.teacher))
    _, _, token = kit.family("g1@example.com")
    answers = {
        (r.status_code, r.text)
        for r in (
            kit.join(token, "ZZZZ-ZZZZ"),
            kit.join(token, live),  # disabled now
            kit.join(token, expired),
            kit.join(token, "nope"),
            kit.join(token, ""),
        )
    }
    assert len(answers) == 1
    assert next(iter(answers))[0] == 404


def test_a_code_enrols_only_into_its_own_class(kit: Kit) -> None:
    other_teacher = kit.staff("teacher", "t2@example.com")
    other_class = kit.make_class(other_teacher, "Other")
    mine = kit.code()
    _, sid, token = kit.family("g1@example.com")
    assert kit.join(token, mine).json()["class_id"] == kit.class_id
    assert kit.status(sid, other_class) is None
    denied = kit.client.post(
        f"/classes/{kit.class_id}/join-code", json={}, headers=auth_header(other_teacher)
    )
    assert denied.status_code == 403
    for method, path in (
        ("get", f"/classes/{kit.class_id}/join-requests"),
        ("delete", f"/classes/{kit.class_id}/join-code"),
        ("delete", f"/classes/{kit.class_id}/members/{sid}"),
    ):
        res = getattr(kit.client, method)(path, headers=auth_header(other_teacher))
        assert res.status_code == 403


def test_rotating_gives_a_new_code_and_keeps_members(kit: Kit) -> None:
    first = kit.code()
    guardian, sid, token = kit.family("g1@example.com")
    kit.join(token, first)
    kit.client.post(
        f"/parents/me/class-requests/{kit.class_id}/{sid}/accept", headers=auth_header(guardian)
    )
    second = kit.code()
    assert second != first
    assert kit.status(sid) == "active"
    _, _, late = kit.family("g2@example.com", name="Late")
    assert kit.join(late, first).status_code == 404  # old code is dead
    assert kit.join(late, second).status_code == 200


def test_a_student_can_leave_and_a_teacher_can_remove(kit: Kit) -> None:
    code = kit.code()
    _, sid, token = kit.family("g1@example.com")
    _, sid2, token2 = kit.family("g2@example.com", name="Two")
    kit.join(token, code)
    kit.join(token2, code)
    left = kit.client.delete(f"/students/me/classes/{kit.class_id}", headers=auth_header(token))
    assert left.status_code == 200 and kit.status(sid) is None
    again = kit.client.delete(f"/students/me/classes/{kit.class_id}", headers=auth_header(token))
    assert again.status_code == 404
    removed = kit.client.delete(
        f"/classes/{kit.class_id}/members/{sid2}", headers=auth_header(kit.teacher)
    )
    assert removed.status_code == 200 and kit.status(sid2) is None


def test_joining_twice_is_harmless_and_never_upgrades_a_pending_join(kit: Kit) -> None:
    code = kit.code()
    _, _, token = kit.family("g1@example.com")
    kit.join(token, code, label="First")
    settings.adult_learners_assumed = True
    again = kit.join(token, code, label="Second")
    assert again.json()["status"] == "pending"
    listed = kit.client.get(
        f"/classes/{kit.class_id}/join-requests", headers=auth_header(kit.teacher)
    ).json()
    assert listed["requests"] == [{"label": "First"}]


def test_parents_and_teachers_cannot_join_and_a_token_is_needed(kit: Kit) -> None:
    code = kit.code()
    guardian, _, _ = kit.family("g1@example.com")
    assert kit.join(guardian, code).status_code == 403
    assert kit.join(kit.teacher, code).status_code == 403
    assert kit.client.post("/classes/join", json={"code": code}).status_code == 401


def test_join_attempts_are_limited_per_account(kit: Kit) -> None:
    settings.rate_limit_enabled = True
    _, _, token = kit.family("g1@example.com")
    seen = []
    for _ in range(10):
        limiter.reset()  # isolate the per-account limit from the per-address one
        seen.append(kit.join(token, "ZZZZ-ZZZZ").status_code)
    assert set(seen) == {404}
    limiter.reset()
    assert kit.join(token, "ZZZZ-ZZZZ").status_code == 429


def test_join_attempts_are_limited_per_address(kit: Kit) -> None:
    _, _, one = kit.family("g1@example.com")
    _, _, two = kit.family("g2@example.com", name="Two")
    settings.rate_limit_enabled = True
    limiter.reset()
    results = [kit.join(one if i % 2 else two, "ZZZZ-ZZZZ").status_code for i in range(11)]
    assert results[:10] == [404] * 10 and results[10] == 429


def test_a_bad_expiry_is_refused(kit: Kit) -> None:
    for days in (0, 366, -1):
        res = kit.client.post(
            f"/classes/{kit.class_id}/join-code",
            json={"expires_in_days": days},
            headers=auth_header(kit.teacher),
        )
        assert res.status_code == 422


def test_deleting_the_family_removes_the_membership(kit: Kit) -> None:
    code = kit.code()
    guardian, _, token = kit.family("g1@example.com")
    kit.join(token, code, label="Ri")
    assert kit.client.delete("/parents/me", headers=auth_header(guardian)).status_code == 200
    kit.db.expire_all()
    assert kit.db.scalars(select(ClassMembershipRow)).all() == []
