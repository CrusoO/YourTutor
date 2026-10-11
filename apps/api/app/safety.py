"""Child safety actions: PII stripping, and the distress pause and flag (ARCHITECTURE section 25).

When a student's own words signal distress (in Ask or in an explain-back), tutoring pauses and the
adults are told: the open session ends, a flag appears on the guardian's page (and an alert for the
teacher when the family shared), and no new session starts until the guardian acknowledges the flag
or a day has passed. The tutor itself only shows the authored gentle message; it never counsels.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ask.config import load_safety
from app.ask.guard import EMAIL, PHONE, URL, screen
from app.auth.consent import has_scope
from app.auth.security import as_utc, now_utc
from app.db.models import SafetyFlagRow, SessionRow, StudentRow, TeacherAlertRow

PAUSE = timedelta(hours=24)


def strip_pii(text: str) -> str:
    """Emails, phone numbers and links replaced before the text is stored or sent anywhere."""
    return URL.sub("[removed]", EMAIL.sub("[removed]", PHONE.sub("[removed]", text)))


def is_distress(text: str, language: str) -> bool:
    return screen(text, load_safety(language)).kind == "distress"


def raise_distress(
    db: Session, student: StudentRow, source: str, now: datetime | None = None
) -> SafetyFlagRow:
    moment = now or now_utc()
    flag = SafetyFlagRow(
        id=uuid.uuid4(),
        student_id=student.id,
        kind="distress",
        source=source,
        created_at=moment,
    )
    db.add(flag)
    for row in db.scalars(
        select(SessionRow).where(SessionRow.student_id == student.id, SessionRow.ended_at.is_(None))
    ):
        row.ended_at = moment
        row.ended_reason = "paused_distress"
        row.resumable = False
    if has_scope(db, student.id, "teacher_share"):
        db.add(
            TeacherAlertRow(
                id=uuid.uuid4(),
                student_id=student.id,
                skill_id="",
                type="distress",
                created_at=moment,
            )
        )
    db.flush()
    return flag


def open_flags(db: Session, student_id: uuid.UUID) -> list[SafetyFlagRow]:
    return list(
        db.scalars(
            select(SafetyFlagRow)
            .where(SafetyFlagRow.student_id == student_id, SafetyFlagRow.acknowledged_at.is_(None))
            .order_by(SafetyFlagRow.created_at)
        )
    )


def is_paused(db: Session, student_id: uuid.UUID, now: datetime | None = None) -> bool:
    moment = now or now_utc()
    return any(moment - as_utc(f.created_at) < PAUSE for f in open_flags(db, student_id))


def acknowledge(db: Session, student_id: uuid.UUID, flag_id: uuid.UUID) -> bool:
    flag = db.get(SafetyFlagRow, flag_id)
    if flag is None or flag.student_id != student_id or flag.acknowledged_at is not None:
        return False
    flag.acknowledged_at = now_utc()
    for alert in db.scalars(
        select(TeacherAlertRow).where(
            TeacherAlertRow.student_id == student_id,
            TeacherAlertRow.type == "distress",
            TeacherAlertRow.resolved_at.is_(None),
        )
    ):
        alert.resolved_at = flag.acknowledged_at
    return True
