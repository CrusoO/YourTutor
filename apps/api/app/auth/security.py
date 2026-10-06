from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from app.config import settings

_now_override: datetime | None = None


def now_utc() -> datetime:
    return _now_override if _now_override is not None else datetime.now(UTC)


def get_now_override() -> datetime | None:
    return _now_override


def set_now_override(value: datetime | None) -> None:
    """Pin `now_utc()`; only `app.dev.clock.frozen` calls this (dev tooling, never in requests)."""
    global _now_override
    _now_override = value


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def hash_pin(pin: str, *, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode(),
        (settings.token_pepper + salt).encode(),
        settings.pin_hash_iterations,
    )
    return f"{salt}${digest.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    salt, _, _digest = stored.partition("$")
    if not salt or not _digest:
        return False
    return hmac.compare_digest(hash_pin(pin, salt=salt), stored)


def hash_code(value: str) -> str:
    return hashlib.sha256(f"{settings.token_pepper}:{value}".encode()).hexdigest()


def codes_match(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def expires_after(seconds: int) -> datetime:
    return now_utc() + timedelta(seconds=seconds)
