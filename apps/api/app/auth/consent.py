from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConsentRow


def active_consent(session: Session, student_id: uuid.UUID) -> ConsentRow | None:
    return session.scalar(
        select(ConsentRow)
        .where(ConsentRow.student_id == student_id, ConsentRow.revoked_at.is_(None))
        .order_by(ConsentRow.granted_at.desc())
    )


def has_scope(session: Session, student_id: uuid.UUID, scope: str) -> bool:
    row = active_consent(session, student_id)
    return bool(row and scope in (row.scopes or []))


def active_scopes(session: Session, student_id: uuid.UUID) -> set[str]:
    row = active_consent(session, student_id)
    return set(row.scopes or []) if row else set()
