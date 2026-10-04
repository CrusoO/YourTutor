from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BookRow, CurriculumRow, LocaleRow, StudentRow
from app.registries.context import context_key_for_student
from app.registries.loaders import load_all_curricula, load_curriculum
from app.registries.timezone import resolve_student_timezone


def ensure_locale(session: Session, code: str) -> str:
    if session.get(LocaleRow, code) is None:
        raise HTTPException(status_code=400, detail=f"unknown locale: {code}")
    return code


def resolve_curriculum_id(raw: str) -> str:
    if raw in load_all_curricula():
        return raw
    raise HTTPException(status_code=400, detail="invalid curriculum")


def student_context_fields(
    session: Session,
    *,
    curriculum_id: str,
    grade: int,
    current_chapter_id: str | None,
    timezone_override: str | None = None,
    device_timezone: str | None = None,
) -> dict[str, object]:
    curriculum = session.get(CurriculumRow, curriculum_id)
    if curriculum is None:
        raise HTTPException(status_code=400, detail="unknown curriculum")
    book = session.scalar(
        select(BookRow).where(BookRow.curriculum_id == curriculum_id, BookRow.grade == grade)
    )
    if book is None:
        raise HTTPException(status_code=400, detail="no book for grade")
    spec = load_curriculum(curriculum_id)
    ctx = context_key_for_student(
        curriculum_id=curriculum_id,
        book_id=book.id,
        grade=grade,
        current_chapter_id=current_chapter_id,
        spec=spec,
    )
    timezone = resolve_student_timezone(
        student_override=timezone_override,
        curriculum_default=curriculum.default_timezone,
        device_timezone=device_timezone,
    )
    legacy_board = curriculum.legacy_board or curriculum_id
    return {
        "curriculum_id": curriculum_id,
        "book_id": book.id,
        "board": legacy_board,
        "current_chapter_id": ctx.chapter_id,
        "context_key": ctx.as_dict(),
        "timezone": timezone,
    }


def apply_student_context(
    student: StudentRow,
    session: Session,
    *,
    curriculum_id: str,
    grade: int,
    current_chapter_id: str | None,
    timezone_override: str | None = None,
) -> None:
    fields = student_context_fields(
        session,
        curriculum_id=curriculum_id,
        grade=grade,
        current_chapter_id=current_chapter_id,
        timezone_override=timezone_override or student.timezone,
    )
    student.curriculum_id = str(fields["curriculum_id"])
    student.book_id = str(fields["book_id"])
    student.board = str(fields["board"])
    student.current_chapter_id = str(fields["current_chapter_id"])
    student.context_key = fields["context_key"]  # type: ignore[assignment]
    student.timezone = str(fields["timezone"])
