"""Class join codes: a teacher opens a code, a student asks to join, a guardian decides.

Consent rule (minors; DPDP s.9 and the 2025 Rules, counsel to confirm): a join by code makes a
PENDING membership. It is active, so the student is listed and the teacher can see anything, only
once the guardian says yes (which records the existing `teacher_share` consent) or the learner is
recorded as an adult. Until then nothing is shared and the teacher sees only a label the student
chose. Visibility itself is still decided by `teacher_can_see` and `teacher_visible_student_ids`,
which count active memberships only and still need `teacher_share`.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth import service as auth_service
from app.auth.actor import Actor
from app.auth.authz import owns_child, require, student_or_404
from app.auth.consent import active_consent, available_scopes, has_scope, is_guest
from app.auth.security import now_utc
from app.classes import codes
from app.config import adults_assumed, settings
from app.db.models import ClassMembershipRow, ClassRow, StudentRow, UserRow
from app.ratelimit import Limiter, Limits

# Per account: 10 join attempts in 15 minutes, right or wrong. Per address the middleware applies
# the `/classes/join` group in config/limits.yaml.
account_limiter = Limiter(Limits(window=900, default=10, groups=(), exempt=()))

NOT_VALID = "code_not_valid"  # one answer for unknown, disabled, expired or malformed
CONSENT_VERSION = "class-code-v1"  # used only when a guardian has no consent on file yet


def learner_is_adult(session: Session, student: StudentRow) -> bool:
    """Whether this learner is recorded as an adult. For now the deployment-wide stand-in
    (`adults_assumed`: yes in development, no in production). The later age question replaces the
    body of this one function; nothing else in the class-code flow reads age."""
    return adults_assumed()


def _owned_class(session: Session, actor: Actor, class_id: uuid.UUID) -> ClassRow:
    klass = session.get(ClassRow, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="class not found")
    require(actor.is_admin or (actor.is_teacher and actor.user_id == klass.teacher_id))
    return klass


# ---- teacher ----------------------------------------------------------------------------------


def set_join_code(
    session: Session, actor: Actor, class_id: uuid.UUID, expires_in_days: int | None
) -> dict[str, Any]:
    """Create or rotate. The code is returned once; only its hash is kept. Members stay."""
    klass = _owned_class(session, actor, class_id)
    if expires_in_days is not None and not 1 <= expires_in_days <= codes.MAX_EXPIRY_DAYS:
        raise HTTPException(status_code=422, detail="expires_in_days must be 1 to 365")
    now = now_utc()
    for _ in range(8):
        code = codes.generate_code()
        digest = codes.code_hash(code)
        if session.scalar(select(ClassRow.id).where(ClassRow.join_code_hash == digest)) is None:
            break
    else:  # pragma: no cover - 40 bits: a collision streak means something is wrong
        raise HTTPException(status_code=503, detail="try again")
    klass.join_code_hash = digest
    klass.join_code_updated_at = now
    klass.join_code_expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None
    session.flush()
    expires = klass.join_code_expires_at
    return {
        "code": codes.display_code(code),
        "expires_at": expires.isoformat() if expires else None,
        "shown_once": True,
    }


def disable_join_code(session: Session, actor: Actor, class_id: uuid.UUID) -> None:
    klass = _owned_class(session, actor, class_id)
    klass.join_code_hash = None
    klass.join_code_expires_at = None
    klass.join_code_updated_at = now_utc()


def _pending_count(session: Session, class_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(ClassMembershipRow)
            .where(
                ClassMembershipRow.class_id == class_id,
                ClassMembershipRow.status == codes.PENDING,
            )
        )
        or 0
    )


def join_code_status(session: Session, actor: Actor, class_id: uuid.UUID) -> dict[str, Any]:
    klass = _owned_class(session, actor, class_id)
    now = now_utc()
    expires = klass.join_code_expires_at
    return {
        "enabled": codes.code_usable(klass.join_code_hash, expires, now),
        "expired": klass.join_code_hash is not None and codes.is_expired(expires, now),
        "expires_at": expires.isoformat() if expires else None,
        "pending_count": _pending_count(session, class_id),
    }


def join_requests(session: Session, actor: Actor, class_id: uuid.UUID) -> dict[str, Any]:
    """Waiting requests: the label the student chose (else 'Student N'), nothing else."""
    _owned_class(session, actor, class_id)
    rows = session.execute(
        select(ClassMembershipRow.student_id, ClassMembershipRow.label)
        .where(
            ClassMembershipRow.class_id == class_id,
            ClassMembershipRow.status == codes.PENDING,
        )
        .order_by(ClassMembershipRow.requested_at, ClassMembershipRow.student_id)
    ).all()
    labels = codes.request_labels([(str(sid), label) for sid, label in rows])
    # No student id either: the teacher cannot act on a request, only the guardian can.
    return {"requests": [{"label": labels[str(sid)]} for sid, _ in rows], "count": len(rows)}


def remove_member(
    session: Session, actor: Actor, class_id: uuid.UUID, student_id: uuid.UUID
) -> None:
    """A teacher removes a student (active or waiting). Nothing else about the student changes."""
    _owned_class(session, actor, class_id)
    done = session.execute(
        delete(ClassMembershipRow).where(
            ClassMembershipRow.class_id == class_id, ClassMembershipRow.student_id == student_id
        )
    )
    if not done.rowcount:  # type: ignore[attr-defined]
        raise HTTPException(status_code=404, detail="not a member")


# ---- student ----------------------------------------------------------------------------------


def join_class(
    session: Session, actor: Actor, raw_code: str, raw_label: str | None
) -> dict[str, Any]:
    require(actor.is_student and actor.student_id is not None)
    assert actor.student_id is not None
    student = student_or_404(session, actor.student_id)
    if is_guest(session, student.id):
        raise HTTPException(status_code=409, detail="guest_cannot_join")
    if settings.rate_limit_enabled:
        wait = account_limiter.check(str(student.id), "classes/join")
        if wait is not None:
            raise HTTPException(
                status_code=429, detail="too many requests", headers={"Retry-After": str(wait)}
            )
    code = codes.normalise_code(raw_code)
    klass = (
        session.scalar(select(ClassRow).where(ClassRow.join_code_hash == codes.code_hash(code)))
        if code
        else None
    )
    now = now_utc()
    if klass is None or not codes.code_usable(
        klass.join_code_hash, klass.join_code_expires_at, now
    ):
        raise HTTPException(status_code=404, detail=NOT_VALID)
    row = session.get(ClassMembershipRow, (klass.id, student.id))
    if row is None:
        row = ClassMembershipRow(
            class_id=klass.id,
            student_id=student.id,
            status=codes.join_status(adult=learner_is_adult(session, student)),
            label=codes.clean_label(raw_label),
            requested_at=now,
        )
        session.add(row)
        session.flush()
    return {"class_id": str(klass.id), "class_name": klass.name, "status": row.status}


def my_classes(session: Session, actor: Actor) -> dict[str, Any]:
    require(actor.is_student and actor.student_id is not None)
    rows = session.execute(
        select(ClassRow.id, ClassRow.name, ClassMembershipRow.status)
        .join(ClassMembershipRow, ClassMembershipRow.class_id == ClassRow.id)
        .where(ClassMembershipRow.student_id == actor.student_id)
        .order_by(ClassRow.name, ClassRow.id)
    ).all()
    return {"classes": [{"class_id": str(i), "name": n, "status": s} for i, n, s in rows]}


def leave_class(session: Session, actor: Actor, class_id: uuid.UUID) -> None:
    require(actor.is_student and actor.student_id is not None)
    done = session.execute(
        delete(ClassMembershipRow).where(
            ClassMembershipRow.class_id == class_id,
            ClassMembershipRow.student_id == actor.student_id,
        )
    )
    if not done.rowcount:  # type: ignore[attr-defined]
        raise HTTPException(status_code=404, detail="not a member")


# ---- guardian ---------------------------------------------------------------------------------


def guardian_requests(session: Session, actor: Actor) -> dict[str, Any]:
    require(actor.is_parent and actor.user_id is not None)
    rows = session.execute(
        select(StudentRow, ClassRow, UserRow, ClassMembershipRow)
        .join(ClassMembershipRow, ClassMembershipRow.student_id == StudentRow.id)
        .join(ClassRow, ClassRow.id == ClassMembershipRow.class_id)
        .join(UserRow, UserRow.id == ClassRow.teacher_id)
        .where(StudentRow.parent_id == actor.user_id, ClassMembershipRow.status == codes.PENDING)
        .order_by(ClassMembershipRow.requested_at, ClassRow.id)
    ).all()
    return {
        "requests": [
            {
                "student_id": str(s.id),
                "student_name": s.display_name,
                "class_id": str(k.id),
                "class_name": k.name,
                "teacher": t.email,  # the guardian is deciding whom to share with
                "requested_at": m.requested_at.isoformat() if m.requested_at else None,
            }
            for s, k, t, m in rows
        ]
    }


def _pending_for_guardian(
    session: Session, actor: Actor, class_id: uuid.UUID, student_id: uuid.UUID
) -> ClassMembershipRow:
    student = student_or_404(session, student_id)
    require(owns_child(actor, student))
    row = session.get(ClassMembershipRow, (class_id, student_id))
    if row is None or row.status != codes.PENDING:
        raise HTTPException(status_code=404, detail="request not found")
    return row


def accept_request(
    session: Session, actor: Actor, class_id: uuid.UUID, student_id: uuid.UUID
) -> dict[str, str]:
    """Yes: record `teacher_share` through the normal consent path (keeping the other scopes the
    guardian already gave), then activate this one membership."""
    row = _pending_for_guardian(session, actor, class_id, student_id)
    if not has_scope(session, student_id, "teacher_share"):
        available = available_scopes(session, student_id)
        if "teacher_share" not in available:
            raise HTTPException(status_code=409, detail="teacher_share_unavailable")
        existing = active_consent(session, student_id)
        scopes = set(existing.scopes or []) if existing else ({"tutoring"} & available)
        auth_service.grant_consent(
            session,
            actor,
            student_id,
            version=existing.version if existing else CONSENT_VERSION,
            scopes=sorted(scopes | {"teacher_share"}),
            paper_ref=existing.paper_ref if existing else None,
        )
    row.status = codes.ACTIVE
    return {"status": codes.ACTIVE}


def decline_request(
    session: Session, actor: Actor, class_id: uuid.UUID, student_id: uuid.UUID
) -> dict[str, str]:
    """No: the waiting membership is removed; consent is not touched."""
    row = _pending_for_guardian(session, actor, class_id, student_id)
    session.delete(row)
    return {"status": "declined"}
