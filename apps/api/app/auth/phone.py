"""Phone sign-in: a phone number and a one-time code, the primary route for guardians and teachers.

It reuses the email route's rules (rate limits per number and per address, a code that dies after
a few wrong tries, one answer for every kind of failure) and its challenge table: a phone
challenge is stored under the key "tel:+...". A phone-only account gets a made-up `.invalid`
email so every user row still has one. A signed-in person can attach a phone to their account by
verifying it (the same two calls with their token); a number already on another account is
refused.

Nothing is sent from here: the sender is chosen by `get_sms_otp_sender` (app/auth/sender.py)
and the provider behind it by SMS_PROVIDER (app/auth/sms.py).
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.actor import Actor
from app.auth.contact import challenge_key, contact_bucket, normalise_phone, synthetic_email
from app.auth.security import expires_after, hash_code, now_utc, otp_code
from app.auth.sender import OtpSender
from app.auth.service import (
    TOO_MANY,
    _count_rate,
    _hit_rate,
    consume_challenge,
    issue_auth_token,
)
from app.config import settings
from app.db.models import OtpChallengeRow, UserRow


def _checked_phone(raw: str, actor: Actor | None) -> str:
    if not settings.phone_signin_enabled:
        raise HTTPException(
            status_code=400,
            detail={"code": "phone_signin_disabled", "message": "phone sign-in is off"},
        )
    if actor is not None and actor.role in {"student", "comparison"}:
        raise HTTPException(status_code=403, detail="forbidden")
    phone = normalise_phone(raw)
    if phone is None:
        raise HTTPException(
            status_code=400, detail={"code": "phone_invalid", "message": "phone number invalid"}
        )
    return phone


def request_phone_otp(
    session: Session, sender: OtpSender, *, phone: str, ip: str, actor: Actor | None
) -> None:
    number = _checked_phone(phone, actor)
    bucket = f"otp_request:phone:{contact_bucket(number)}"
    if _count_rate(session, bucket) >= settings.otp_request_limit_email:
        raise TOO_MANY
    if _count_rate(session, f"otp_request:ip:{ip}") >= settings.otp_request_limit_ip:
        raise TOO_MANY
    _hit_rate(session, bucket)
    _hit_rate(session, f"otp_request:ip:{ip}")
    code = otp_code()
    session.add(
        OtpChallengeRow(
            id=uuid.uuid4(),
            email=challenge_key(number),
            code_hash=hash_code(code),
            ip=ip,
            created_at=now_utc(),
            expires_at=expires_after(settings.otp_ttl_seconds),
        )
    )
    sender.send(number, code)


def verify_phone_otp(
    session: Session, *, phone: str, code: str, ip: str, actor: Actor | None
) -> str:
    number = _checked_phone(phone, actor)
    consume_challenge(session, challenge_key(number), code, ip)
    owner = session.scalar(select(UserRow).where(UserRow.phone == number))
    if actor is not None and actor.user_id is not None:
        me = session.get(UserRow, actor.user_id)
        if me is None:
            raise HTTPException(status_code=403, detail="forbidden")
        if owner is not None and owner.id != me.id:
            raise HTTPException(status_code=409, detail="phone_in_use")
        me.phone = number
        user = me
    elif owner is not None:
        user = owner
    else:
        user_id = uuid.uuid4()
        user = UserRow(
            id=user_id,
            role="parent",
            email=synthetic_email(user_id.hex),
            phone=number,
            locale="en",
            created_at=now_utc(),
        )
        session.add(user)
        session.flush()
    return issue_auth_token(session, role=user.role, user_id=user.id)
