"""The only way to write or read the method/error profile.

Privacy by construction: a write takes an id string (or enum) that passes `validate_id` and an
integer increment. There is no free-text path: anything outside the id charset raises ValueError
before the database or the key is touched. Nothing in the tutor calls this module yet.

Writes need the flag (`learner_profile_enabled`), a configured key and the `learning_profile`
consent scope; otherwise `record_event` writes nothing and returns False. Reads for export are the
student's own right and need neither the flag nor the scope.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from datetime import date
from enum import StrEnum
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.consent import has_scope
from app.config import settings
from app.db.models import LearnerMethodCountRow
from app.learner.profile.counts import (
    SCHEMA_V,
    Counts,
    add_event,
    decayed,
    from_payload,
    to_payload,
    week_index,
)
from app.learner.profile.crypto import (
    KeyRing,
    ProfileCryptoError,
    build_aad,
    parse_key_ring,
    seal,
    unseal,
)

SCOPE = "learning_profile"
RETENTION_WEEKS = 26  # about 180 days; the shortest period that still does the job
MAX_INCREMENT = 10
PSEUDONYM_HEX = 16
MIN_SALT_CHARS = 16
_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.]{0,63}")  # ASCII, no spaces: an id, never a sentence


class DiagnosisClass(StrEnum):
    SLIP = "slip"
    INCOMPLETE_PROCEDURE = "incomplete_procedure"
    PREREQUISITE_GAP = "prerequisite_gap"


def validate_id(value: str) -> str:
    """Return `value` if it is a well-formed id; raise ValueError (never echoing it) if not."""
    text = str(value)
    if not _ID_RE.fullmatch(text):
        raise ValueError("not a valid method, error or skill id")
    return text


def key_ring() -> KeyRing:
    return parse_key_ring(settings.profile_enc_keys)


def _load(row: LearnerMethodCountRow, ring: KeyRing) -> Counts:
    aad = build_aad(row.student_id, row.skill_id, row.schema_v)
    return from_payload(json.loads(unseal(ring, row.key_id, row.payload, aad)))


def _kind_and_key(method_id: str | None, error_id: str | DiagnosisClass | None) -> tuple[str, str]:
    if (method_id is None) == (error_id is None):
        raise ValueError("give exactly one of method_id and error_id")
    if method_id is not None:
        return "method", validate_id(method_id)
    return "error", validate_id(str(error_id))


def record_event(
    db: Session,
    student_id: uuid.UUID,
    skill_id: str,
    *,
    method_id: str | None = None,
    error_id: str | DiagnosisClass | None = None,
    increment: int = 1,
    today: date | None = None,
    ring: KeyRing | None = None,
) -> bool:
    """Add `increment` to one method or one error id. True when a row was written.

    Exactly one of `method_id` and `error_id` is given. Flushes, never commits.
    """
    if isinstance(increment, bool) or not isinstance(increment, int):
        raise ValueError("increment must be an integer")
    if not 1 <= increment <= MAX_INCREMENT:
        raise ValueError("increment out of range")
    skill = validate_id(skill_id)
    kind, key = _kind_and_key(method_id, error_id)
    if not settings.learner_profile_enabled or not has_scope(db, student_id, SCOPE):
        return False
    keys = ring if ring is not None else key_ring()
    if keys.empty:
        return False
    week = week_index(today or date.today())
    row = db.get(LearnerMethodCountRow, (student_id, skill))
    current = _load(row, keys) if row is not None else Counts(week=week)
    merged = add_event(current, kind=kind, key=key, increment=increment, week=week)
    plaintext = json.dumps(to_payload(merged), sort_keys=True).encode()
    key_id, blob = seal(keys, plaintext, build_aad(student_id, skill, SCHEMA_V))
    if row is None:
        row = LearnerMethodCountRow(student_id=student_id, skill_id=skill)
        db.add(row)
    row.key_id, row.payload, row.schema_v, row.updated_week = key_id, blob, SCHEMA_V, week
    db.flush()
    return True


def read_counts(
    db: Session,
    student_id: uuid.UUID,
    skill_id: str,
    *,
    today: date | None = None,
    ring: KeyRing | None = None,
) -> Counts | None:
    """The decayed counts for one skill as of this week, or None (no row, flag off, no scope)."""
    skill = validate_id(skill_id)
    if not settings.learner_profile_enabled or not has_scope(db, student_id, SCOPE):
        return None
    row = db.get(LearnerMethodCountRow, (student_id, skill))
    if row is None:
        return None
    keys = ring if ring is not None else key_ring()
    return decayed(_load(row, keys), week_index(today or date.today()))


def export_rows(
    db: Session, student_id: uuid.UUID, *, today: date | None = None, ring: KeyRing | None = None
) -> list[dict[str, Any]]:
    """The student's own counts in plain language: skill id, ids and rounded counts. No payload."""
    keys = ring if ring is not None else key_ring()
    week = week_index(today or date.today())
    out: list[dict[str, Any]] = []
    rows = db.scalars(
        select(LearnerMethodCountRow)
        .where(LearnerMethodCountRow.student_id == student_id)
        .order_by(LearnerMethodCountRow.skill_id)
    )
    for row in rows:
        entry: dict[str, Any] = {"skill_id": row.skill_id, "updated_week": row.updated_week}
        try:
            counts = decayed(_load(row, keys), week)
        except (ProfileCryptoError, ValueError, KeyError):
            entry["readable"] = False  # a retired key or damaged row: say so, never fail the export
        else:
            entry["readable"] = True
            entry["methods"] = {k: round(v, 1) for k, v in counts.methods.items()}
            entry["errors"] = {k: round(v, 1) for k, v in counts.errors.items()}
        out.append(entry)
    return out


def delete_student_rows(db: Session, student_id: uuid.UUID) -> int:
    """Delete every profile row of this student (on revoke and on account purge)."""
    result = db.execute(
        delete(LearnerMethodCountRow).where(LearnerMethodCountRow.student_id == student_id)
    )
    return int(getattr(result, "rowcount", 0) or 0)


def delete_older_than(db: Session, today: date, *, dry_run: bool = False, batch: int = 500) -> int:
    """Delete rows whose `updated_week` is more than RETENTION_WEEKS old, in batches."""
    where = LearnerMethodCountRow.updated_week < week_index(today) - RETENTION_WEEKS
    if dry_run:
        return db.scalar(select(func.count()).select_from(LearnerMethodCountRow).where(where)) or 0
    total = 0
    while True:
        keys = db.execute(
            select(LearnerMethodCountRow.student_id, LearnerMethodCountRow.skill_id)
            .where(where)
            .limit(batch)
        ).all()
        if not keys:
            return total
        for student_id, skill_id in keys:
            db.execute(
                delete(LearnerMethodCountRow).where(
                    LearnerMethodCountRow.student_id == student_id,
                    LearnerMethodCountRow.skill_id == skill_id,
                )
            )
        db.commit()
        total += len(keys)


def pseudonym(student_id: uuid.UUID, salt: str) -> str:
    """HMAC-SHA256(salt, student id) truncated to 16 hex: the id an analyst sees."""
    if len(salt) < MIN_SALT_CHARS:
        raise ValueError("the pseudonym salt is missing or too short")
    digest = hmac.new(salt.encode(), str(student_id).encode(), hashlib.sha256).hexdigest()
    return digest[:PSEUDONYM_HEX]
