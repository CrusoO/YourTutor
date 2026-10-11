from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConsentRow, StudentRow, UserRow
from app.registries.loaders import load_all_curricula
from app.registries.startup import deployment_jurisdiction_profile

GUEST_ROLE = "guest"
GUEST_SCOPES = frozenset({"tutoring"})  # a guest stores no personal data; nothing else is implied


def active_consent(session: Session, student_id: uuid.UUID) -> ConsentRow | None:
    return session.scalar(
        select(ConsentRow)
        .where(ConsentRow.student_id == student_id, ConsentRow.revoked_at.is_(None))
        .order_by(ConsentRow.granted_at.desc())
    )


def is_guest(session: Session, student_id: uuid.UUID) -> bool:
    role = session.scalar(
        select(UserRow.role)
        .join(StudentRow, StudentRow.parent_id == UserRow.id)
        .where(StudentRow.id == student_id)
    )
    return role == GUEST_ROLE


def _profile_id_for(session: Session, student: StudentRow | None) -> str | None:
    """The jurisdiction profile of the student's curriculum (None: use the deployment's)."""
    if student is None or not student.curriculum_id:
        return None
    spec = load_all_curricula().get(student.curriculum_id)
    return spec.jurisdiction_profile if spec else None


def available_scopes(session: Session, student_id: uuid.UUID) -> set[str]:
    """Scopes a guardian may grant for this student: the profile's list, nothing else."""
    student = session.get(StudentRow, student_id)
    profile = deployment_jurisdiction_profile(_profile_id_for(session, student))
    return set(profile.consent_scopes)


def active_scopes(session: Session, student_id: uuid.UUID) -> set[str]:
    row = active_consent(session, student_id)
    if row is not None:
        return set(row.scopes or []) & available_scopes(session, student_id)
    return set(GUEST_SCOPES) if is_guest(session, student_id) else set()


def has_scope(session: Session, student_id: uuid.UUID, scope: str) -> bool:
    return scope in active_scopes(session, student_id)
