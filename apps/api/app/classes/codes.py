"""Pure rules for class join codes and join requests (no database, no clock of its own).

A code is 8 characters from a 32-letter alphabet without 0, O, 1 or I (40 bits). It is stored only
as a keyed hash, so it is shown once at creation and never read back; rotating gives a new one.
The code is a lookup key behind per-address and per-account rate limits, not a password.
"""

from __future__ import annotations

import re
import secrets
from datetime import datetime

from app.ask.guard import EMAIL, PHONE, URL
from app.auth.security import as_utc, hash_code

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0, O, 1, I
CODE_LENGTH = 8
GROUP = 4
LABEL_MAX = 24
DEFAULT_LABEL = "Student"
MAX_EXPIRY_DAYS = 365

PENDING = "pending"
ACTIVE = "active"

_SEPARATORS = re.compile(r"[\s\-_.]+")
_LONG_DIGITS = re.compile(r"\d{4,}")


def generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def display_code(code: str) -> str:
    """ABCD-EFGH: easier to read aloud and copy from a board."""
    return f"{code[:GROUP]}-{code[GROUP:]}"


def normalise_code(raw: str) -> str | None:
    """The canonical code for what a student typed, or None when it cannot be a code."""
    cleaned = _SEPARATORS.sub("", raw or "").upper()
    if len(cleaned) != CODE_LENGTH or any(c not in ALPHABET for c in cleaned):
        return None
    return cleaned


def code_hash(code: str) -> str:
    return hash_code(f"class-join:{code}")


def is_expired(expires_at: datetime | None, now: datetime) -> bool:
    return expires_at is not None and as_utc(expires_at) <= now


def code_usable(code_hash_value: str | None, expires_at: datetime | None, now: datetime) -> bool:
    """Disabled (no hash) and expired codes are not usable; answered like an unknown code."""
    return code_hash_value is not None and not is_expired(expires_at, now)


def join_status(*, adult: bool) -> str:
    """A join is active at once only for a learner recorded as an adult; a minor waits for the
    guardian. The one place the later age question plugs in (see app/classes/service.py)."""
    return ACTIVE if adult else PENDING


def clean_label(raw: str | None) -> str | None:
    """A display label the student chose, or None to fall back to 'Student N'.

    Rejects anything that looks like contact details or a long number, and anything too long:
    the point is a nickname the teacher can recognise, never an identifier.
    """
    if raw is None:
        return None
    text = " ".join(raw.split())
    if not text or len(text) > LABEL_MAX:
        return None
    if EMAIL.search(text) or PHONE.search(text) or URL.search(text) or _LONG_DIGITS.search(text):
        return None
    if "@" in text:
        return None
    return text


def request_labels(rows: list[tuple[str, str | None]]) -> dict[str, str]:
    """Label per student id for the teacher's list: the chosen label, else 'Student N' in the
    order requested. Identifiers, email and the real display name never appear here."""
    out: dict[str, str] = {}
    number = 0
    for student_id, label in rows:
        if label:
            out[student_id] = label
        else:
            number += 1
            out[student_id] = f"{DEFAULT_LABEL} {number}"
    return out
