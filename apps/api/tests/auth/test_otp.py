from __future__ import annotations

import inspect
import logging
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.security import codes_match, hash_code
from app.auth.sender import EmailOtpSender, MemoryOtpSender
from app.config import settings
from app.db.models import OtpChallengeRow, RateEventRow
from tests.conftest import auth_header, signup


def test_otp_console_when_smtp_unset(caplog) -> None:
    settings.smtp_host = ""
    logging.getLogger("yourtutor.otp").propagate = True
    with caplog.at_level(logging.INFO, logger="yourtutor.otp"):
        EmailOtpSender().send("dev@example.com", "654321")
    assert "OTP for dev@example.com: 654321" in caplog.text


def test_request_and_verify_otp(client: TestClient, sender: MemoryOtpSender) -> None:
    token = signup(client, sender, "newparent@example.com")
    assert token


def test_otp_request_rate_limit(client: TestClient, sender: MemoryOtpSender) -> None:
    email = "limited@example.com"
    for _ in range(settings.otp_request_limit_email):
        assert client.post("/auth/request-otp", json={"email": email}).status_code == 200
    blocked = client.post("/auth/request-otp", json={"email": email})
    assert blocked.status_code == 429


def test_otp_verify_rate_limit(client: TestClient, sender: MemoryOtpSender) -> None:
    email = "verify-limit@example.com"
    client.post("/auth/request-otp", json={"email": email})
    for _ in range(settings.otp_verify_limit_email):
        client.post("/auth/verify-otp", json={"email": email, "code": "000000"})
    blocked = client.post("/auth/verify-otp", json={"email": email, "code": "000000"})
    assert blocked.status_code == 429


def test_student_cannot_request_otp(client: TestClient, world) -> None:
    response = client.post(
        "/auth/request-otp",
        json={"email": "student-try@example.com"},
        headers=auth_header(world.student_token),
    )
    assert response.status_code == 403


def test_otp_stored_hashed_not_plaintext(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    email = "hashed@example.com"
    client.post("/auth/request-otp", json={"email": email})
    code = sender.inbox[email]
    db.expire_all()
    row = db.scalar(
        select(OtpChallengeRow).where(OtpChallengeRow.email == email)
    )
    assert row is not None
    assert row.code_hash == hash_code(code)
    assert code not in row.code_hash
    assert row.code_hash != code


def test_otp_expires_after_ten_minutes(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    assert settings.otp_ttl_seconds == 600
    email = "expired@example.com"
    client.post("/auth/request-otp", json={"email": email})
    code = sender.inbox[email]
    db.expire_all()
    row = db.scalar(select(OtpChallengeRow).where(OtpChallengeRow.email == email))
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    response = client.post("/auth/verify-otp", json={"email": email, "code": code})
    assert response.status_code == 401


def test_otp_is_single_use(client: TestClient, sender: MemoryOtpSender) -> None:
    email = "once@example.com"
    client.post("/auth/request-otp", json={"email": email})
    code = sender.inbox[email]
    first = client.post("/auth/verify-otp", json={"email": email, "code": code})
    assert first.status_code == 200
    second = client.post("/auth/verify-otp", json={"email": email, "code": code})
    assert second.status_code == 401


def test_otp_compared_in_constant_time() -> None:
    digest = hash_code("123456")
    assert codes_match(digest, hash_code("123456"))
    assert not codes_match(digest, hash_code("000000"))
    assert "compare_digest" in inspect.getsource(codes_match)


def test_otp_invalidated_after_five_wrong_attempts(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    email = "fivewrong@example.com"
    client.post("/auth/request-otp", json={"email": email})
    code = sender.inbox[email]
    for _ in range(5):
        bad = client.post("/auth/verify-otp", json={"email": email, "code": "000000"})
        assert bad.status_code == 401
    db.expire_all()
    row = db.scalar(select(OtpChallengeRow).where(OtpChallengeRow.email == email))
    assert row is not None
    assert row.attempts == 5
    assert row.consumed_at is not None
    db.execute(delete(RateEventRow))
    db.commit()
    still = client.post("/auth/verify-otp", json={"email": email, "code": code})
    assert still.status_code == 401


def test_comparison_cannot_request_otp(client: TestClient, world) -> None:
    response = client.post(
        "/auth/request-otp",
        json={"email": "cmp@example.com"},
        headers=auth_header(world.comparison_token),
    )
    assert response.status_code == 403
