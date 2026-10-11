"""Context options and guest start (G5).

A guest is a student with no guardian and no personal data. To keep every student row tied to an
owner, a hidden user with role `guest` and an unusable address owns it; deleting that user deletes
the guest, and the G6 upgrade moves the student to a real guardian. No name, email, phone,
school or surname is accepted or stored.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.consent import GUEST_ROLE
from app.auth.service import TOO_MANY, _count_rate, _hit_rate, issue_auth_token, now_utc
from app.config import settings
from app.db.models import LocaleRow, StudentRow, UserRow
from app.registries.loaders import load_all_curricula
from app.registries.student_setup import (
    ensure_locale,
    resolve_curriculum_id,
    student_context_fields,
)

GUEST_NAME = "Guest"
GUEST_EMAIL_DOMAIN = "guest.invalid"  # .invalid never resolves: no mail can reach a guest


class GuestStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # any personal field is refused with a 422

    curriculum_id: str
    grade: int = Field(ge=1, le=12)
    subject: str = "math"
    home_language: str = "en"
    device_timezone: str | None = Field(default=None, max_length=64)


def context_options(db: Session) -> dict[str, Any]:
    """Curriculum -> grade -> subject -> book, and the languages a student can pick."""
    curricula: list[dict[str, Any]] = []
    for spec in load_all_curricula().values():
        grades: dict[int, dict[str, list[dict[str, Any]]]] = {}
        for book in spec.books:
            subjects = grades.setdefault(book.grade, {})
            subjects.setdefault(book.subject, []).append({"id": book.id, "medium": book.medium})
        curricula.append(
            {
                "id": spec.id,
                "grades": [
                    {
                        "grade": grade,
                        "subjects": [
                            {"id": subject, "books": books} for subject, books in subs.items()
                        ],
                    }
                    for grade, subs in sorted(grades.items())
                ],
            }
        )
    languages = db.scalars(select(LocaleRow).order_by(LocaleRow.code)).all()
    return {
        "curricula": curricula,
        "languages": [{"code": row.code, "name": row.name} for row in languages],
    }


def start_guest(db: Session, body: GuestStartIn, ip: str) -> dict[str, Any]:
    if _count_rate(db, f"guest_start:ip:{ip}") >= settings.guest_start_limit_ip:
        raise TOO_MANY
    curriculum_id = resolve_curriculum_id(body.curriculum_id)
    spec = load_all_curricula()[curriculum_id]
    book = next(
        (b for b in spec.books if b.grade == body.grade and b.subject == body.subject), None
    )
    if book is None:
        raise HTTPException(status_code=400, detail="no book for that grade and subject")
    language = ensure_locale(db, body.home_language)
    fields = student_context_fields(
        db,
        curriculum_id=curriculum_id,
        grade=body.grade,
        current_chapter_id=None,
        device_timezone=body.device_timezone,
    )
    _hit_rate(db, f"guest_start:ip:{ip}")
    owner = UserRow(
        id=uuid.uuid4(),
        role=GUEST_ROLE,
        email=f"guest-{uuid.uuid4().hex}@{GUEST_EMAIL_DOMAIN}",
        locale=language,
        created_at=now_utc(),
    )
    db.add(owner)
    db.flush()
    student = StudentRow(
        id=uuid.uuid4(),
        parent_id=owner.id,
        display_name=GUEST_NAME,
        grade=body.grade,
        board=str(fields["board"]),
        curriculum_id=curriculum_id,
        book_id=str(fields["book_id"]),
        context_key=fields["context_key"],
        home_language=language,
        exam_language=language,
        current_chapter_id=str(fields["current_chapter_id"]),
        timezone=str(fields["timezone"]),
        created_at=now_utc(),
    )
    db.add(student)
    db.flush()
    token = issue_auth_token(db, role="student", student_id=student.id)
    db.commit()
    return {
        "student_id": str(student.id),
        "token": token,
        "display_name": GUEST_NAME,
        "curriculum_id": curriculum_id,
        "grade": body.grade,
    }
