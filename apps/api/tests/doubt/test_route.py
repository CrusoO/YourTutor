"""POST /doubt/solve: gates (flag, consent, role), abuse, privacy (no storage, no text in logs)."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.auth.consent as consent_mod
from app.auth.security import now_utc
from app.config import settings
from app.db.models import Base, ConsentRow
from app.doubt.limits import student_window
from tests.conftest import MemoryOtpSender, auth_header, signup

OK_BODY: dict[str, Any] = {
    "schema": "doubt-expr/1",
    "kind": "poly_eq",
    "lhs": ["3", "2"],
    "rhs": ["7"],
}


@pytest.fixture(autouse=True)
def _open(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "scope_math_check_enabled", True)
    real = consent_mod.available_scopes
    monkeypatch.setattr(
        consent_mod, "available_scopes", lambda s, sid: real(s, sid) | {"math_check"}
    )
    student_window.reset()
    yield
    student_window.reset()


@dataclass
class World:
    parent_token: str
    student_token: str
    consent_share_id: uuid.UUID
    student_share_id: str


@pytest.fixture
def world(client: TestClient, sender: MemoryOtpSender) -> World:
    """One guardian, one student with a tutoring consent and a student token (a light version of
    the shared world fixture: the doubt route needs nothing else)."""
    parent = signup(client, sender, "parent@example.com")
    made = client.post(
        "/students",
        json={"display_name": "Kid", "grade": 9, "board": "bhutan"},
        headers=auth_header(parent),
    )
    sid = made.json()["id"]
    consent = client.post(
        f"/students/{sid}/consent",
        json={"version": "v1", "scopes": ["tutoring"]},
        headers=auth_header(parent),
    )
    assert consent.status_code == 200, consent.text
    client.post(f"/students/{sid}/pin", json={"pin": "1234"}, headers=auth_header(parent))
    pin = client.post(f"/students/{sid}/pin/verify", json={"pin": "1234"})
    assert pin.status_code == 200, pin.text
    return World(parent, pin.json()["access_token"], uuid.UUID(consent.json()["id"]), sid)


def grant(db: Session, world: World, on: bool = True) -> None:
    row = db.scalars(select(ConsentRow).where(ConsentRow.id == world.consent_share_id)).one()
    scopes = [s for s in row.scopes if s != "math_check"]
    row.scopes = [*scopes, "math_check"] if on else scopes
    db.commit()


def post(client: TestClient, world: World, body: object, raw: bytes | None = None) -> Any:
    headers = {**auth_header(world.student_token), "Content-Type": "application/json"}
    data = raw if raw is not None else json.dumps(body).encode()
    return client.post("/doubt/solve", content=data, headers=headers)


def code(res: Any) -> str:
    return str(res.json()["detail"]["code"])


def test_solves_and_labels_a_verified_result(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    res = post(client, world, OK_BODY)
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["verified"] and out["label"] == "checked_by_code"
    assert out["answer"] == {"kind": "values", "values": ["2"]}
    assert [s["rule"] for s in out["steps"]][-1] == "substitute_check"


def test_flag_off_is_404_with_a_code_even_with_consent(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    grant(db, world)
    monkeypatch.setattr(settings, "scope_math_check_enabled", False)
    res = post(client, world, OK_BODY)
    assert res.status_code == 404 and code(res) == "doubt_server_disabled"


def test_flag_default_is_off() -> None:
    assert type(settings).model_fields["scope_math_check_enabled"].default is False


def test_no_scope_is_refused(client: TestClient, world: World) -> None:
    res = post(client, world, OK_BODY)
    assert res.status_code == 403 and code(res) == "math_check_consent_required"


def test_revoked_consent_is_refused(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    assert post(client, world, OK_BODY).status_code == 200
    row = db.scalars(select(ConsentRow).where(ConsentRow.id == world.consent_share_id)).one()
    row.revoked_at = now_utc()
    db.commit()
    res = post(client, world, OK_BODY)
    assert res.status_code == 403 and code(res) == "math_check_consent_required"


def test_scope_not_offered_by_the_profile_is_refused(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    grant(db, world)
    monkeypatch.setattr(consent_mod, "available_scopes", lambda s, sid: {"tutoring"})
    res = post(client, world, OK_BODY)
    assert res.status_code == 403 and code(res) == "math_check_consent_required"


def test_needs_a_token_and_a_student(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    assert client.post("/doubt/solve", json=OK_BODY).status_code == 401
    parent = client.post("/doubt/solve", json=OK_BODY, headers=auth_header(world.parent_token))
    assert parent.status_code == 403


def test_per_student_rate_limit(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    student_window.per_hour = 3
    try:
        for _ in range(3):
            assert post(client, world, OK_BODY).status_code == 200
        res = post(client, world, OK_BODY)
    finally:
        student_window.per_hour = 30
    assert res.status_code == 429 and code(res) == "doubt_rate_limited"


def test_ip_rate_limit_group_exists() -> None:
    from app.ratelimit import load_limits

    assert load_limits().for_path("/doubt/solve") == ("/doubt", 20)


BAD_BODIES: dict[str, Any] = {
    "free_text_kind": {**OK_BODY, "kind": "free_text"},
    "arith_has_no_schema_kind": {"schema": "doubt-expr/1", "kind": "arith", "expr": "2+2"},
    "extra_key": {**OK_BODY, "note": "my name is Asha"},
    "sentence_as_number": {**OK_BODY, "lhs": ["solve this for me", "2"]},
    "non_math": {**OK_BODY, "lhs": ["hello", "world"]},
    "ten_digits": {**OK_BODY, "rhs": ["9876543210"]},
    "unicode_digits": {**OK_BODY, "rhs": ["٣"]},
    "fullwidth_digits": {**OK_BODY, "rhs": ["３"]},
    "unicode_minus": {**OK_BODY, "rhs": ["−3"]},
    "trailing_newline": {**OK_BODY, "rhs": ["3\n"]},
    "plus_sign": {**OK_BODY, "rhs": ["+3"]},
    "space": {**OK_BODY, "rhs": [" 3"]},
    "zero_width": {**OK_BODY, "rhs": ["3​"]},
    "sql": {**OK_BODY, "rhs": ["1; DROP TABLE users"]},
    "script": {**OK_BODY, "rhs": ["<script>alert(1)</script>"]},
    "template": {**OK_BODY, "rhs": ["{{7*7}}"]},
    "float": {**OK_BODY, "rhs": [2.5]},
    "int": {**OK_BODY, "rhs": [3]},
    "bool": {**OK_BODY, "rhs": [True]},
    "null_entry": {**OK_BODY, "rhs": [None]},
    "zero_denominator": {**OK_BODY, "rhs": ["1/0"]},
    "decimal": {**OK_BODY, "rhs": ["0.5"]},
    "exponent": {**OK_BODY, "rhs": ["1e9"]},
    "too_many_coeffs": {**OK_BODY, "lhs": ["1"] * 6},
    "empty_side": {**OK_BODY, "lhs": []},
    "wrong_schema": {**OK_BODY, "schema": "doubt-expr/2"},
    "mixed_shapes": {
        **OK_BODY,
        "system": {"coeffs": [["1", "1"], ["1", "-1"]], "consts": ["1", "1"]},
    },
    "missing_rhs": {"schema": "doubt-expr/1", "kind": "poly_eq", "lhs": ["1", "1"]},
    "string_body": "2x + 3 = 7",
    "list_body": [1, 2, 3],
}


@pytest.mark.parametrize("name", sorted(BAD_BODIES))
def test_abuse_is_refused_without_echo(
    client: TestClient, world: World, db: Session, name: str
) -> None:
    grant(db, world)
    body = BAD_BODIES[name]
    res = post(client, world, body)
    assert res.status_code == 422 and code(res) == "doubt_invalid", (name, res.text)
    for piece in ("DROP TABLE", "script", "Asha", "solve this", "9876543210", "hello"):
        if piece in json.dumps(body):
            assert piece not in res.text


def test_oversize_body_is_refused(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    res = post(client, world, {**OK_BODY, "lhs": ["1"] * 5000})
    assert res.status_code == 413 and code(res) == "doubt_too_large"


def test_invalid_json_is_refused(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    res = post(client, world, None, raw=b"{not json \xff\xfe")
    assert res.status_code == 422 and code(res) == "doubt_invalid"


def test_phone_like_number_is_refused_by_the_pii_screen(
    client: TestClient, world: World, db: Session
) -> None:
    grant(db, world)
    res = post(client, world, {**OK_BODY, "rhs": ["987654321"]})
    assert res.status_code == 422 and code(res) == "doubt_pii"


def test_unverifiable_problem_gets_an_honest_answer(
    client: TestClient, world: World, db: Session
) -> None:
    grant(db, world)
    res = post(client, world, {**OK_BODY, "lhs": ["-2", "0", "1"], "rhs": ["0"]})
    out = res.json()
    assert res.status_code == 200 and out["verified"] is False
    assert out["label"] == "not_verified" and out["answer"] is None and out["steps"] == []


def test_logs_hold_a_hash_and_an_outcome_and_no_numbers(
    client: TestClient, world: World, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    grant(db, world)
    caplog.set_level(logging.DEBUG)
    body = {**OK_BODY, "lhs": ["4217", "613"], "rhs": ["8191"]}
    assert post(client, world, body).status_code == 200
    post(client, world, {**body, "kind": "free_text"})
    doubt_lines = "\n".join(
        r.getMessage() for r in caplog.records if r.name.startswith("app.doubt")
    )
    assert "outcome=verified" in doubt_lines
    for secret in ("4217", "613", "8191", "poly_eq"):
        assert secret not in doubt_lines


def test_nothing_is_stored(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)

    def snapshot() -> dict[str, list[str]]:
        db.rollback()
        return {
            t.name: sorted(str(r) for r in db.execute(select(t)).all())
            for t in Base.metadata.sorted_tables
        }

    before = snapshot()
    assert post(client, world, {**OK_BODY, "rhs": ["4242"]}).status_code == 200
    post(client, world, BAD_BODIES["sql"])
    assert snapshot() == before


def test_no_model_is_called(client: TestClient, world: World, db: Session) -> None:
    import app.doubt.router as route

    names = " ".join(vars(route))
    assert "gateway" not in names and "llm" not in names.lower()
    grant(db, world)
    assert post(client, world, OK_BODY).status_code == 200
