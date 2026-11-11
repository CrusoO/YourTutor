"""Contact details a person can sign in or be reached with: an email or a phone number.

A phone number is kept in international form (E.164: "+" and 8 to 15 digits). A number typed
without "+" gets PHONE_DEFAULT_CALLING_CODE in front, if the deployment set one; otherwise it is
refused so a number is never guessed to belong to a country.
"""

from __future__ import annotations

import re

from app.auth.security import hash_code
from app.config import settings

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_CHALLENGE_PREFIX = "tel:"  # OtpChallengeRow.email holds "tel:+..." for a phone challenge
SYNTHETIC_DOMAIN = "phone.invalid"  # .invalid never resolves; a phone-only account's made-up email


def normalise_phone(raw: str) -> str | None:
    """The E.164 form of a typed number, or None when it cannot be one."""
    text = re.sub(r"[\s().-]", "", raw or "")
    if not text:
        return None
    if text.startswith("00"):
        text = "+" + text[2:]
    if not text.startswith("+"):
        code = re.sub(r"\D", "", settings.phone_default_calling_code)
        if not code:
            return None
        text = "+" + code + text.lstrip("0")
    return text if _E164.match(text) else None


def normalise_email(raw: str) -> str | None:
    text = (raw or "").strip().lower()
    return text if _EMAIL.match(text) else None


def classify_contact(raw: str) -> tuple[str, str] | None:
    """("email", address) or ("phone", e164) for something a guardian could be reached on."""
    email = normalise_email(raw)
    if email:
        return "email", email
    phone = normalise_phone(raw)
    if phone:
        return "phone", phone
    return None


def challenge_key(phone: str) -> str:
    return PHONE_CHALLENGE_PREFIX + phone


def contact_bucket(contact: str) -> str:
    """A rate-limit key for a contact that does not itself hold the contact."""
    return hash_code(contact)[:16]


def synthetic_email(user_key: str) -> str:
    return f"p-{user_key}@{SYNTHETIC_DOMAIN}"


def is_synthetic(email: str) -> bool:
    return email.endswith("@" + SYNTHETIC_DOMAIN)
