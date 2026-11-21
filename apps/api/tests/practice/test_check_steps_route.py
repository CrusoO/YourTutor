"""POST /practice/check-steps: gates, abuse, privacy (no storage, no expression in logs)."""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.auth.consent as consent_mod
from app.auth.security import now_utc
from app.config import settings
from app.db.models import Base, ConsentRow
from app.practice.router import step_window
from tests.conftest import MemoryOtpSender, auth_header, signup

OK_BODY: dict[str, Any] = {
    "schema": "step-check/1",
    "question": "x^2 - 7x + 10 = 0",
    "lines": ["(x-2)(x-5)=0", "x=-2 or x=-5"],
}


@pytest.fixture(autouse=True)
def _open(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "scope_math_check_enabled", True)
    monkeypatch.setattr(settings, "step_check_enabled", True)
    real = consent_mod.available_scopes
    monkeypatch.setattr(
        consent_mod, "available_scopes", lambda s, sid: real(s, sid) | {"math_check"}
    )
    step_window.reset()
    yield
    step_window.reset()


@dataclass
class World:
    parent_token: str
    student_token: str
    consent_share_id: uuid.UUID
    student_share_id: str


@pytest.fixture
def world(client: TestClient, sender: MemoryOtpSender) -> World:
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
    return client.post("/practice/check-steps", content=data, headers=headers)


def code(res: Any) -> str:
    return str(res.json()["detail"]["code"])


def test_checks_lines_and_gives_a_verdict(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    res = post(client, world, OK_BODY)
    assert res.status_code == 200, res.text
    out = res.json()
    assert [line["state"] for line in out["lines"]] == ["ok", "wrong_step"]
    assert out["lines"][1]["hint_key"] == "MC.QUAD.FACTOR_SIGN_READ"
    assert out["verdict"] == "wrong" and out["label"] == "checked_by_code"
    assert out["supported"] is True


def test_right_path_is_correct(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    body = {**OK_BODY, "lines": ["(x-2)(x-5)=0", "x = 2 or x = 5"]}
    out = post(client, world, body).json()
    assert [line["state"] for line in out["lines"]] == ["ok", "ok"] and out["verdict"] == "correct"


def test_unreadable_line_is_reported_without_penalty(
    client: TestClient, world: World, db: Session
) -> None:
    grant(db, world)
    out = post(client, world, {**OK_BODY, "lines": ["3 +", "x=2 or x=5"]}).json()
    assert [line["state"] for line in out["lines"]] == ["unreadable", "skipped"]
    assert out["verdict"] == "correct"


def test_flag_default_is_off() -> None:
    assert type(settings).model_fields["step_check_enabled"].default is False


def test_flag_off_is_404_with_a_code(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    grant(db, world)
    monkeypatch.setattr(settings, "step_check_enabled", False)
    res = post(client, world, OK_BODY)
    assert res.status_code == 404 and code(res) == "step_check_disabled"


def test_no_scope_is_refused(client: TestClient, world: World) -> None:
    res = post(client, world, OK_BODY)
    assert res.status_code == 403 and code(res) == "math_check_consent_required"


def test_revoked_consent_is_refused(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    assert post(client, world, OK_BODY).status_code == 200
    row = db.scalars(select(ConsentRow).where(ConsentRow.id == world.consent_share_id)).one()
    row.revoked_at = now_utc()
    db.commit()
    assert code(post(client, world, OK_BODY)) == "math_check_consent_required"


def test_needs_a_token_and_a_student(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    assert client.post("/practice/check-steps", json=OK_BODY).status_code == 401
    parent = client.post(
        "/practice/check-steps", json=OK_BODY, headers=auth_header(world.parent_token)
    )
    assert parent.status_code == 403


def test_per_student_rate_limit(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    step_window.per_hour = 3
    try:
        for _ in range(3):
            assert post(client, world, OK_BODY).status_code == 200
        res = post(client, world, OK_BODY)
    finally:
        step_window.per_hour = 30
    assert res.status_code == 429 and code(res) == "step_check_rate_limited"


def test_ip_rate_limit_group_matches_the_doubt_route() -> None:
    from app.ratelimit import load_limits

    assert load_limits().for_path("/practice/check-steps") == ("/practice", 20)


BAD_BODIES: dict[str, Any] = {
    "sentence_line": {**OK_BODY, "lines": ["my name is Asha"]},
    "script": {**OK_BODY, "lines": ["<script>alert(1)</script>"]},
    "sql": {**OK_BODY, "lines": ["1; DROP TABLE users"]},
    "extra_key": {**OK_BODY, "note": "my name is Asha"},
    "no_lines": {**OK_BODY, "lines": []},
    "thirteen_lines": {**OK_BODY, "lines": ["x=1"] * 13},
    "long_line": {**OK_BODY, "lines": ["1" * 161]},
    "question_not_equation": {**OK_BODY, "question": "x^2 - 7x + 10"},
    "question_text": {**OK_BODY, "question": "solve x = hello"},
    "wrong_schema": {**OK_BODY, "schema": "step-check/2"},
    "int_line": {**OK_BODY, "lines": [3]},
    "null_line": {**OK_BODY, "lines": [None]},
    "string_body": "x = 1",
    "list_body": [1, 2, 3],
}


@pytest.mark.parametrize("name", sorted(BAD_BODIES))
def test_abuse_is_refused_without_echo(
    client: TestClient, world: World, db: Session, name: str
) -> None:
    grant(db, world)
    body = BAD_BODIES[name]
    res = post(client, world, body)
    assert res.status_code == 422 and code(res) == "step_check_invalid", (name, res.text)
    for piece in ("DROP TABLE", "script", "Asha", "hello"):
        if piece in json.dumps(body):
            assert piece not in res.text


def test_oversize_body_is_refused(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)
    res = post(client, world, {**OK_BODY, "lines": ["1"] * 5000})
    assert res.status_code == 413 and code(res) == "step_check_too_large"


def test_phone_like_number_is_refused_by_the_pii_screen(
    client: TestClient, world: World, db: Session
) -> None:
    grant(db, world)
    res = post(client, world, {**OK_BODY, "lines": ["x = 9876543210"]})
    assert res.status_code == 422 and code(res) == "step_check_pii"


def test_logs_hold_a_hash_and_an_outcome_and_no_expression(
    client: TestClient, world: World, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    grant(db, world)
    caplog.set_level(logging.DEBUG)
    body = {**OK_BODY, "question": "x^2 - 4217x + 613 = 0", "lines": ["x = 8191", "x^2 = 6133"]}
    assert post(client, world, body).status_code == 200
    post(client, world, {**body, "lines": ["hello there"]})
    logged = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app.practice"))
    assert "outcome=" in logged and "outcome=rejected" in logged
    visible = re.sub(r"h=[0-9a-f]+", "h=<digest>", logged)
    for secret in ("4217", "613", "8191", "6133", "hello"):
        assert secret not in visible


def test_nothing_is_stored(client: TestClient, world: World, db: Session) -> None:
    grant(db, world)

    def snapshot() -> dict[str, list[str]]:
        db.rollback()
        return {
            t.name: sorted(str(r) for r in db.execute(select(t)).all())
            for t in Base.metadata.sorted_tables
        }

    before = snapshot()
    assert post(client, world, OK_BODY).status_code == 200
    post(client, world, BAD_BODIES["sql"])
    assert snapshot() == before


def test_no_model_is_called() -> None:
    import app.practice.router as route

    names = " ".join(vars(route))
    assert "gateway" not in names and "llm" not in names.lower()
