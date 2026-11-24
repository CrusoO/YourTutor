"""Admin-issued reviewer sign-in codes: one-time, no email, checked by the normal verify path."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import as_utc, now_utc
from app.auth.sender import EmailUnavailable, get_otp_sender
from app.config import settings
from app.db.models import OtpChallengeRow, ReviewerCodeIssueRow, UserRow
from app.main import app
from tests.conftest import World, auth_header, seed_user

LIST = "/staff/review/items"


@pytest.fixture
def desk() -> None:
    settings.reviewer_desk_enabled = True


def _issue(client: TestClient, token: str, reviewer_id: Any) -> Any:
    return client.post(
        f"/staff/review/reviewers/{reviewer_id}/sign-in-code", headers=auth_header(token)
    )


def _reviewer(db: Session, email: str = "rev@example.com") -> UserRow:
    return seed_user(db, "reviewer", email)


def _sign_in(client: TestClient, email: str, code: str) -> Any:
    return client.post("/auth/verify-otp", json={"email": email, "code": code})


def _challenge(db: Session, email: str) -> OtpChallengeRow:
    db.expire_all()
    return db.scalars(select(OtpChallengeRow).where(OtpChallengeRow.email == email)).one()


def test_a_code_signs_the_reviewer_in_exactly_once(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    rev = _reviewer(db)
    made = _issue(client, world.admin_token, rev.id)
    assert made.status_code == 200, made.text
    code = made.json()["code"]
    assert len(code) == 6 and made.json()["expires_at"]
    first = _sign_in(client, rev.email, code)
    assert first.status_code == 200
    token = first.json()["access_token"]
    assert client.get(LIST, headers=auth_header(token)).status_code == 200
    assert _sign_in(client, rev.email, code).status_code == 401


def test_the_code_fails_after_it_expires(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    rev = _reviewer(db)
    code = _issue(client, world.admin_token, rev.id).json()["code"]
    row = _challenge(db, rev.email)
    life = as_utc(row.expires_at) - as_utc(row.created_at)
    assert abs(life.total_seconds() - settings.reviewer_signin_code_ttl_seconds) < 5
    row.expires_at = now_utc() - timedelta(seconds=1)
    db.commit()
    assert _sign_in(client, rev.email, code).status_code == 401


def test_a_wrong_code_fails_and_counts_toward_the_attempt_limit(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    rev = _reviewer(db)
    code = _issue(client, world.admin_token, rev.id).json()["code"]
    wrong = "000000" if code != "000000" else "111111"
    assert _sign_in(client, rev.email, wrong).status_code == 401
    assert _challenge(db, rev.email).attempts == 1
    for _ in range(settings.otp_challenge_max_attempts - 1):
        _sign_in(client, rev.email, wrong)
    assert _challenge(db, rev.email).consumed_at is not None  # the code died with its tries


def test_a_code_for_one_reviewer_does_not_sign_in_another(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    a, b = _reviewer(db, "a@example.com"), _reviewer(db, "b@example.com")
    code = _issue(client, world.admin_token, a.id).json()["code"]
    assert _sign_in(client, b.email, code).status_code == 401
    assert _sign_in(client, a.email, code).status_code == 200


def test_a_new_code_replaces_the_previous_unused_one(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    rev = _reviewer(db)
    first = _issue(client, world.admin_token, rev.id).json()["code"]
    second = _issue(client, world.admin_token, rev.id).json()["code"]
    if first != second:
        assert _sign_in(client, rev.email, first).status_code == 401
    assert _sign_in(client, rev.email, second).status_code == 200


def test_a_suspended_reviewer_is_refused_and_cannot_use_an_issued_code(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    rev = _reviewer(db)
    code = _issue(client, world.admin_token, rev.id).json()["code"]
    head = auth_header(world.admin_token)
    assert client.post(f"/staff/review/reviewers/{rev.id}/suspend", headers=head).status_code == 200
    # the sign-in itself still answers (as for an emailed code), but the session it gives is dead
    signed = _sign_in(client, rev.email, code)
    assert signed.status_code == 200
    for path in (LIST, "/auth/me"):
        assert (
            client.get(path, headers=auth_header(signed.json()["access_token"])).status_code == 403
        )
    assert _issue(client, world.admin_token, rev.id).status_code == 409


def test_only_reviewer_accounts_get_a_code(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    for role in ("teacher", "admin", "parent"):
        other = seed_user(db, role, f"{role}-x@example.com")
        assert _issue(client, world.admin_token, other.id).status_code == 404
    assert _issue(client, world.admin_token, uuid.uuid4()).status_code == 404


def test_at_most_five_codes_per_reviewer_per_hour(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    rev = _reviewer(db)
    for _ in range(5):
        assert _issue(client, world.admin_token, rev.id).status_code == 200
    assert _issue(client, world.admin_token, rev.id).status_code == 429
    other = _reviewer(db, "rev-two@example.com")
    assert _issue(client, world.admin_token, other.id).status_code == 200  # per reviewer


def test_only_an_admin_may_issue_a_code(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    rev = _reviewer(db)
    path = f"/staff/review/reviewers/{rev.id}/sign-in-code"
    assert client.post(path).status_code == 401
    assert client.post(path, headers=auth_header(world.teacher_token)).status_code == 403
    assert client.post(path, headers=auth_header(world.parent_token)).status_code == 403
    other = _reviewer(db, "r2@example.com")
    code = _issue(client, world.admin_token, other.id).json()["code"]
    token = _sign_in(client, other.email, code).json()["access_token"]
    assert client.post(path, headers=auth_header(token)).status_code == 403


def test_with_the_desk_off_the_route_is_404(client: TestClient, world: World, db: Session) -> None:
    rev = _reviewer(db)
    assert settings.reviewer_desk_enabled is False
    assert _issue(client, world.admin_token, rev.id).status_code == 404
    assert db.scalars(select(ReviewerCodeIssueRow)).all() == []


def test_the_code_appears_only_in_the_response(
    client: TestClient,
    world: World,
    db: Session,
    desk: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    rev = _reviewer(db)
    with caplog.at_level(logging.DEBUG):
        code = _issue(client, world.admin_token, rev.id).json()["code"]
        _sign_in(client, rev.email, code)
    assert code not in caplog.text
    db.expire_all()
    audit = db.scalars(select(ReviewerCodeIssueRow)).one()
    assert audit.reviewer_id == rev.id
    admin = db.scalar(select(UserRow).where(UserRow.role == "admin"))
    assert admin is not None and audit.issued_by == admin.id
    values = [str(getattr(audit, c.key)) for c in ReviewerCodeIssueRow.__table__.columns]
    assert all(code not in v for v in values)
    challenge = _challenge(db, rev.email)
    assert code not in challenge.code_hash
    listing = client.get("/staff/review/reviewers", headers=auth_header(world.admin_token))
    assert code not in listing.text


def test_a_failed_email_send_does_not_hide_an_issued_code(
    client: TestClient, world: World, db: Session, desk: None
) -> None:
    class Down:
        def send(self, destination: str, code: str) -> None:
            raise EmailUnavailable("no smtp")

    rev = _reviewer(db)
    code = _issue(client, world.admin_token, rev.id).json()["code"]
    app.dependency_overrides[get_otp_sender] = lambda: Down()
    asked = client.post("/auth/request-otp", json={"email": rev.email})
    assert asked.status_code == 503
    assert _sign_in(client, rev.email, code).status_code == 200


def test_the_bootstrap_command_makes_the_first_admin_with_a_working_code(
    client: TestClient, engine: Any, db: Session, monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    from sqlalchemy.orm import sessionmaker

    from app.auth import bootstrap

    monkeypatch.setattr(bootstrap, "session_factory", lambda: sessionmaker(bind=engine))
    assert bootstrap.main(["admin-code", "Boss@Example.org"]) == 0
    code = capsys.readouterr().out.strip()[-6:]
    signed = _sign_in(client, "boss@example.org", code)
    assert signed.status_code == 200
    me = client.get("/auth/me", headers=auth_header(signed.json()["access_token"]))
    assert me.json()["role"] == "admin"
    seed_user(db, "teacher", "t-op@example.com")
    assert (
        bootstrap.main(["admin-code", "t-op@example.com"]) == 1
    )  # never turns another role into admin
