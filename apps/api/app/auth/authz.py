from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.actor import Actor
from app.auth.consent import active_scopes, has_scope
from app.config import settings
from app.db.models import ClassMembershipRow, ClassRow, StudentRow

FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def require(condition: bool) -> None:
    if not condition:
        raise FORBIDDEN


def student_or_404(session: Session, student_id: uuid.UUID) -> StudentRow:
    row = session.get(StudentRow, student_id)
    if row is None:
        raise HTTPException(status_code=404, detail="student not found")
    return row


def owns_child(actor: Actor, student: StudentRow) -> bool:
    return actor.is_parent and actor.user_id == student.parent_id


def teacher_can_see(session: Session, actor: Actor, student_id: uuid.UUID) -> bool:
    if not actor.is_teacher or actor.user_id is None:
        return False
    in_class = session.scalar(
        select(ClassMembershipRow)
        .join(ClassRow, ClassRow.id == ClassMembershipRow.class_id)
        .where(
            ClassMembershipRow.student_id == student_id,
            ClassRow.teacher_id == actor.user_id,
        )
    )
    return bool(in_class) and has_scope(session, student_id, "teacher_share")


def can_see_progress(session: Session, actor: Actor, student: StudentRow) -> bool:
    if actor.is_admin:
        return True
    if actor.is_student:
        return actor.student_id == student.id
    if owns_child(actor, student):
        return True
    if teacher_can_see(session, actor, student.id):
        return True
    return False


def can_manage_student(actor: Actor, student: StudentRow) -> bool:
    return actor.is_admin or owns_child(actor, student)


def can_start_session(actor: Actor, student: StudentRow) -> bool:
    if actor.is_admin:
        return True
    return actor.is_student and actor.student_id == student.id


def can_export_family(actor: Actor, parent_id: uuid.UUID) -> bool:
    return actor.is_admin or (actor.is_parent and actor.user_id == parent_id)


def can_teacher_query(actor: Actor) -> bool:
    return actor.is_admin or actor.is_teacher


def llm_phrasing_allowed(actor: Actor, scopes: set[str]) -> bool:
    if actor.is_comparison:
        return False
    if actor.is_student or actor.is_admin:
        return "ai_processing" in scopes
    return False


def can_load_draft(actor: Actor | None) -> bool:
    if actor is not None and actor.is_comparison:
        return False
    return settings.allow_draft_content


def teacher_visible_student_ids(session: Session, teacher_id: uuid.UUID) -> list[uuid.UUID]:
    rows = session.execute(
        select(ClassMembershipRow.student_id)
        .join(ClassRow, ClassRow.id == ClassMembershipRow.class_id)
        .where(ClassRow.teacher_id == teacher_id)
    ).all()
    visible: list[uuid.UUID] = []
    for (student_id,) in rows:
        if "teacher_share" in active_scopes(session, student_id):
            visible.append(student_id)
    return visible
