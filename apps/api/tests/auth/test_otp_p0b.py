"""P0-B: no OTP in logs, typed 503 when email is down, per-IP verify limits."""

from __future__ import annotations

import logging
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.security import now_utc
from app.auth.sender import (
    EmailOtpSender,
    EmailUnavailable,
    MemoryOtpSender,
    get_otp_sender,
)
from app.config import settings
from app.db.models import RateEventRow
from app.main import app


def test_otp_never_logged_and_unavailable_when_smtp_unset(caplog) -> None:
    settings.smtp_host = ""
    logging.getLogger("yourtutor.otp").propagate = True
    with caplog.at_level(logging.DEBUG, logger="yourtutor.otp"):
        with pytest.raises(EmailUnavailable):
            EmailOtpSender().send("dev@example.com", "654321")
        MemoryOtpSender().send("dev@example.com", "654321")
    assert "654321" not in caplog.text


def test_smtp_failure_becomes_email_unavailable(monkeypatch, caplog) -> None:
    settings.smtp_host = "smtp.invalid"

    def boom(*_a, **_k):  # noqa: ANN202
        raise OSError("connection refused for 654321")

    monkeypatch.setattr("app.auth.sender.smtplib.SMTP", boom)
    logging.getLogger("yourtutor.otp").propagate = True
    with caplog.at_level(logging.DEBUG, logger="yourtutor.otp"):
        with pytest.raises(EmailUnavailable):
            EmailOtpSender().send("dev@example.com", "654321")
    assert "654321" not in caplog.text
    settings.smtp_host = ""


def test_request_otp_answers_503_email_unavailable(client: TestClient) -> None:
    settings.smtp_host = ""
    app.dependency_overrides[get_otp_sender] = EmailOtpSender
    response = client.post("/auth/request-otp", json={"email": "nomail@example.com"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "email_unavailable"


def test_wrong_codes_from_attacker_ips_do_not_block_the_victims_fresh_code(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    email = "victim@example.com"
    client.post("/auth/request-otp", json={"email": email})
    for n in range(6):
        with pytest.raises(HTTPException):
            service.verify_otp(db, email=email, code="000000", ip=f"203.0.113.{n}", actor=None)
    client.post("/auth/request-otp", json={"email": email})  # fresh code
    ok = client.post("/auth/verify-otp", json={"email": email, "code": sender.inbox[email]})
    assert ok.status_code == 200


def test_one_ip_gets_an_exponential_delay(db: Session) -> None:
    ip = "198.51.100.9"
    for _ in range(settings.otp_verify_free_failures_ip + 3):  # 3 over the free ones: wait 8 s
        db.add(
            RateEventRow(id=uuid.uuid4(), bucket=f"otp_verify_fail:ip:{ip}", created_at=now_utc())
        )
    db.commit()
    with pytest.raises(HTTPException) as delayed:
        service.verify_otp(db, email="x@example.com", code="1", ip=ip, actor=None)
    assert delayed.value.status_code == 429
    # another IP is not affected
    with pytest.raises(HTTPException) as other:
        service.verify_otp(db, email="x@example.com", code="1", ip="198.51.100.10", actor=None)
    assert other.value.status_code == 401


def test_first_failure_with_no_free_tries_does_not_crash(db: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "otp_verify_free_failures_ip", 0)
    with pytest.raises(HTTPException) as first:
        service.verify_otp(db, email="y@example.com", code="1", ip="198.51.100.11", actor=None)
    assert first.value.status_code == 401
