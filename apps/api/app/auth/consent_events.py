"""Append-only consent audit: one hash-chained row per change, per student.

Rows hold ids, scope, action, the sha256 of the wording shown, the verification method and who
acted. No IP address and no free text. The chain maths is pure and lives in consent_state.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.consent_state import GENESIS, row_hash
from app.auth.security import as_utc, now_utc
from app.db.models import ConsentEventRow

ACTIONS = frozenset(
    {
        "granted",
        "withdrawn",
        "expired",
        "reasked",
        "verified",
        "verify_failed",
        "deleted_data",
        "flag_off_forced",
    }
)
ACTOR_KINDS = frozenset({"guardian", "system", "admin"})


def event_fields(row: ConsentEventRow) -> dict[str, str | None]:
    """The row as plain strings, the form the pure chain functions hash."""
    return {
        "id": str(row.id),
        "at": as_utc(row.at).isoformat() if row.at else None,
        "student_id": str(row.student_id) if row.student_id else None,
        "guardian_user_id": str(row.guardian_user_id) if row.guardian_user_id else None,
        "scope": row.scope,
        "action": row.action,
        "text_sha256": row.text_sha256,
        "method": row.method,
        "actor_kind": row.actor_kind,
        "prev_hash": row.prev_hash,
        "row_hash": row.row_hash,
    }


def chain(session: Session, student_id: uuid.UUID) -> list[ConsentEventRow]:
    """A student's events in chain order (follows prev_hash links from GENESIS)."""
    rows = list(
        session.scalars(select(ConsentEventRow).where(ConsentEventRow.student_id == student_id))
    )
    by_prev: dict[str, list[ConsentEventRow]] = {}
    for row in rows:
        by_prev.setdefault(row.prev_hash, []).append(row)
    ordered: list[ConsentEventRow] = []
    prev = GENESIS
    while by_prev.get(prev):
        row = by_prev[prev].pop(0)
        ordered.append(row)
        prev = row.row_hash
    # rows the walk could not reach (a forked or edited chain) go last so verify_chain fails
    ordered.extend(r for r in rows if r not in ordered)
    return ordered


def append_event(
    session: Session,
    *,
    student_id: uuid.UUID,
    guardian_user_id: uuid.UUID | None,
    scope: str,
    action: str,
    actor_kind: str,
    text_sha256: str | None = None,
    method: str | None = None,
) -> ConsentEventRow:
    """Add one audit row, chained to the student's latest. The only writer of consent_events."""
    if action not in ACTIONS or actor_kind not in ACTOR_KINDS:
        raise ValueError("unknown consent action or actor kind")
    # pending rows from this same flush cycle must count, so write them out first
    session.flush()
    existing = chain(session, student_id)
    prev = existing[-1].row_hash if existing else GENESIS
    row = ConsentEventRow(
        id=uuid.uuid4(),
        at=now_utc(),
        student_id=student_id,
        guardian_user_id=guardian_user_id,
        scope=scope,
        action=action,
        text_sha256=text_sha256,
        method=method,
        actor_kind=actor_kind,
        prev_hash=prev,
    )
    row.row_hash = row_hash(prev, event_fields_without_hash(row))
    session.add(row)
    session.flush()
    return row


def event_fields_without_hash(row: ConsentEventRow) -> dict[str, str | None]:
    fields = event_fields(row)
    fields.pop("row_hash", None)
    return fields


def rows_for_verification(rows: Sequence[ConsentEventRow]) -> list[dict[str, str | None]]:
    return [event_fields(r) for r in rows]
