"""Phone sign-in: a one-time code by SMS, through a provider that sends nothing in tests."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.contact import classify_contact, is_synthetic, normalise_phone
from app.auth.sender import MemoryOtpSender, SmsOtpSender
from app.auth.sms import (
    ConsoleSmsProvider,
    FakeSmsProvider,
    SmsUnavailable,
    get_sms_provider,
    set_sms_provider,
)
from app.config import Settings, production_config_errors, settings
from app.db.models import OtpChallengeRow, UserRow
from tests.conftest import auth_header, signup

PHONE = "+15550001234"


@pytest.fixture(autouse=True)
def _phone_on() -> None:
    settings.phone_signin_enabled = True  # restored by the conftest fixture


def _request(client: TestClient, phone: str, token: str | None = None):
    return client.post(
        "/auth/request-otp", json={"phone": phone}, headers=auth_header(token) if token else {}
    )


def _verify(client: TestClient, phone: str, code: str, token: str | None = None):
    return client.post(
        "/auth/verify-otp",
        json={"phone": phone, "code": code},
        headers=auth_header(token) if token else {},
    )


def test_numbers_are_kept_in_international_form() -> None:
    assert normalise_phone("+1 (555) 000-1234") == PHONE
    assert normalise_phone("0015550001234") == PHONE
    assert normalise_phone("5550001234") is None  # no country code to assume
    assert normalise_phone("+12") is None
    assert normalise_phone("not a number") is None
    settings.phone_default_calling_code = "+1"
    assert normalise_phone("0555 000 1234") == "+15550001234"
    assert classify_contact("A@Example.com") == ("email", "a@example.com")
    assert classify_contact("+15550001234") == ("phone", PHONE)
    assert classify_contact("nonsense") is None


def test_it_is_off_until_switched_on(client: TestClient) -> None:
    settings.phone_signin_enabled = False
    res = _request(client, PHONE)
    assert res.status_code == 400 and res.json()["detail"]["code"] == "phone_signin_disabled"
    assert client.get("/auth/options").json() == {"phone_signin": False, "child_profiles": False}
    settings.phone_signin_enabled = True
    assert client.get("/auth/options").json()["phone_signin"] is True


def test_a_new_number_becomes_a_guardian_account_with_no_real_email(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    assert _request(client, PHONE).status_code == 200
    verified = _verify(client, PHONE, sender.inbox[PHONE])
    assert verified.status_code == 200, verified.text
    token = verified.json()["access_token"]
    me = client.get("/auth/me", headers=auth_header(token)).json()
    assert me["role"] == "parent" and is_synthetic(me["email"])
    user = db.scalar(select(UserRow).where(UserRow.phone == PHONE))
    assert user is not None
    # the same number signs into the same account
    _request(client, PHONE)
    again = _verify(client, PHONE, sender.inbox[PHONE]).json()["access_token"]
    assert client.get("/auth/me", headers=auth_header(again)).json()["user_id"] == str(user.id)
    # the export does not present the made-up address as the person's
    export = client.get("/parents/me/export", headers=auth_header(again)).json()
    assert export["user"]["email"] is None and export["user"]["phone"] == PHONE


def test_a_wrong_or_reused_code_and_a_bad_number_are_refused(
    client: TestClient, sender: MemoryOtpSender
) -> None:
    assert _request(client, "12").status_code == 400
    _request(client, PHONE)
    code = sender.inbox[PHONE]
    wrong = "000000" if code != "000000" else "111111"
    assert _verify(client, PHONE, wrong).status_code == 401
    assert _verify(client, PHONE, code).status_code == 200
    assert _verify(client, PHONE, code).status_code == 401  # used up


def test_a_code_for_one_channel_does_not_open_another(
    client: TestClient, sender: MemoryOtpSender
) -> None:
    _request(client, PHONE)
    code = sender.inbox[PHONE]
    res = client.post("/auth/verify-otp", json={"email": "x@example.com", "code": code})
    assert res.status_code == 401


def test_requests_are_rate_limited_per_number(client: TestClient) -> None:
    results = [
        _request(client, PHONE).status_code for _ in range(settings.otp_request_limit_email + 1)
    ]
    assert results[:-1] == [200] * settings.otp_request_limit_email
    assert results[-1] == 429


def test_a_signed_in_person_can_add_a_phone_and_cannot_take_anothers(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    mine = signup(client, sender, "me@example.com")
    other = signup(client, sender, "other@example.com")
    _request(client, PHONE, mine)
    assert _verify(client, PHONE, sender.inbox[PHONE], mine).status_code == 200
    me = db.scalar(select(UserRow).where(UserRow.email == "me@example.com"))
    assert me is not None and me.phone == PHONE
    # another account cannot attach the same number
    _request(client, PHONE, other)
    taken = _verify(client, PHONE, sender.inbox[PHONE], other)
    assert taken.status_code == 409
    # and a learner's token cannot use the route at all
    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    assert _request(client, "+15550009999", guest["token"]).status_code == 403


def test_deleting_the_account_removes_the_number_and_its_codes(
    client: TestClient, sender: MemoryOtpSender, db: Session
) -> None:
    _request(client, PHONE)
    token = _verify(client, PHONE, sender.inbox[PHONE]).json()["access_token"]
    _request(client, PHONE, token)  # a second challenge row for the same number
    assert db.scalars(select(OtpChallengeRow).where(OtpChallengeRow.email == "tel:" + PHONE)).all()
    assert client.delete("/parents/me", headers=auth_header(token)).status_code == 200
    db.expire_all()
    assert db.scalar(select(UserRow).where(UserRow.phone == PHONE)) is None
    assert not db.scalars(
        select(OtpChallengeRow).where(OtpChallengeRow.email == "tel:" + PHONE)
    ).all()


# ---- the provider interface ---------------------------------------------------------------------


def test_the_sms_sender_uses_the_provider_and_the_code_stays_out_of_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeSmsProvider()
    set_sms_provider(fake)
    try:
        SmsOtpSender().send(PHONE, "123456")
    finally:
        set_sms_provider(None)
    assert fake.last_to(PHONE) and "123456" in (fake.last_to(PHONE) or "")
    caplog.set_level("DEBUG")
    with pytest.raises(SmsUnavailable):
        ConsoleSmsProvider().send_sms(PHONE, "code 987654")
    assert "987654" not in caplog.text and PHONE not in caplog.text


def test_the_setting_picks_the_provider_and_vendor_is_a_stub() -> None:
    settings.sms_provider = "console"
    assert isinstance(get_sms_provider(), ConsoleSmsProvider)
    settings.sms_provider = "fake"
    assert isinstance(get_sms_provider(), FakeSmsProvider)
    settings.sms_provider = "vendor"
    with pytest.raises(SmsUnavailable):
        get_sms_provider().send_sms(PHONE, "x")


def test_an_unsent_code_is_a_503_not_a_silent_success(client: TestClient) -> None:
    from app.auth.sender import get_sms_otp_sender
    from app.main import app

    class Dead:
        def send(self, destination: str, code: str) -> None:
            raise SmsUnavailable("no vendor")

    app.dependency_overrides[get_sms_otp_sender] = lambda: Dead()
    res = _request(client, PHONE)
    assert res.status_code == 503 and res.json()["detail"]["code"] == "sms_unavailable"


def test_production_refuses_phone_sign_in_that_cannot_send() -> None:
    base: dict[str, Any] = {
        "app_env": "production",
        "token_pepper": "x" * 40,
        "smtp_host": "mail.example",
        "postgres_password": "not-the-default",
        "phone_signin_enabled": True,
        "sms_provider": "console",
    }
    errors = production_config_errors(Settings(**base))
    assert any("SMS_PROVIDER" in e for e in errors)
    ok = production_config_errors(Settings(**{**base, "sms_provider": "vendor"}))
    assert not any("SMS_PROVIDER" in e for e in ok)
    child = production_config_errors(
        Settings(**{**base, "child_profiles_enabled": True, "sms_provider": "vendor"})
    )
    assert any("PUBLIC_WEB_URL" in e for e in child)
