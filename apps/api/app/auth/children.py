"""A child's limited-mode profile and the guardian's approval of it.

Limited mode is guest mode with a guardian on the way. The child gives a nickname (not a real
name), the class level and board, and a contact for the guardian. Until the guardian approves,
the child's learner row is an ordinary guest row (hidden `guest` owner, "Guest" as its name, the
`tutoring` scope only): no saved progress, no personalised difficulty, no school details. The one
row holding anything personal is the approval row: the nickname, and the contact only so the link
can be sent. It is deleted when the guardian approves or declines or it expires.

The guardian gets a link with a signed-in-free, single-use, expiring token. The token is random,
only its hash is stored, it travels after the "#" of the link (never sent to a web server's log)
and in a POST body. Approving needs no account made beforehand: holding the link is the proof of
control of the contact it was sent to, the same proof as a sign-in code. Approval creates the
guardian's account if the contact is new, moves the child to it, records the guardian agreement
(every scope, including teacher_share, on one screen) and unlocks the profile.

No tracking, behavioural monitoring or advertising targeting of children happens here or
anywhere in the product; nothing in this module records anything but the above.
"""

from __future__ import annotations

import re
import uuid
from typing import Any
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import agreements
from app.auth.actor import Actor
from app.auth.age import record_age
from app.auth.authz import require
from app.auth.consent import is_guest
from app.auth.contact import classify_contact, contact_bucket, synthetic_email
from app.auth.guest import GUEST_NAME, GuestStartIn, create_guest_student
from app.auth.notify import NotifyUnavailable, get_notifier
from app.auth.security import as_utc, expires_after, hash_code, new_token, now_utc
from app.auth.service import (
    TOO_MANY,
    _count_rate,
    _family_code_for_parent,
    _hit_rate,
    issue_auth_token,
    purge_students,
)
from app.config import settings
from app.db.models import GuardianApprovalRow, StudentRow, UserRow
from app.registries.student_setup import apply_student_context, resolve_curriculum_id

NOT_VALID = "approval_not_valid"  # one answer for unknown, used, expired or malformed
_DIGITS = re.compile(r"\d")


class ChildStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # no surname, school, phone of the child, ...

    nickname: str = Field(min_length=1, max_length=30)
    curriculum_id: str
    grade: int = Field(ge=1, le=12)
    subject: str = "math"
    home_language: str = "en"
    device_timezone: str | None = Field(default=None, max_length=64)
    guardian_contact: str = Field(min_length=3, max_length=120)  # an email or a phone number
    acknowledged: list[str]  # the child's notice, ticked (checked, never stored)


class ApproveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=10, max_length=200)
    version: str
    accepted: list[str]
    grade: int | None = Field(default=None, ge=1, le=12)  # the guardian may correct the class
    curriculum_id: str | None = None  # ... and the board


class TokenIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=10, max_length=200)


def _require_enabled() -> None:
    if not settings.child_profiles_enabled:
        raise HTTPException(status_code=404, detail="child_profiles_disabled")


def _link(token: str) -> str:
    parts = urlsplit(settings.public_web_url)
    origin = f"{parts.scheme}://{parts.netloc}" if parts.netloc else settings.public_web_url
    return f"{origin}/approve#{token}"


def _clean_nickname(raw: str) -> str:
    """A nickname, not an identifier: refuse anything shaped like an email or a phone number."""
    name = " ".join(raw.split())
    if not name or "@" in name or len(_DIGITS.findall(name)) >= 5 or "http" in name.lower():
        raise HTTPException(status_code=400, detail="nickname_invalid")
    return name


def _send_link(row: GuardianApprovalRow, token: str) -> None:
    text = (
        "A child has asked YourTutor to set up a learning profile with you as their guardian. "
        "Nothing is kept about them until you decide. Open this link to read what is asked and "
        f"to say yes or no: {_link(token)} . If you do not know this child, ignore this message."
    )
    try:
        get_notifier().send(row.contact_kind, row.contact, "YourTutor: a guardian is needed", text)
    except NotifyUnavailable:
        raise HTTPException(
            status_code=503,
            detail={"code": "notice_unavailable", "message": "could not reach the guardian"},
        ) from None


def start_child(db: Session, body: ChildStartIn, ip: str) -> dict[str, Any]:
    _require_enabled()
    error = agreements.items_error("child", body.acknowledged)
    if error:
        raise HTTPException(status_code=400, detail=error)
    contact = classify_contact(body.guardian_contact)
    if contact is None:
        raise HTTPException(status_code=400, detail="guardian_contact_invalid")
    kind, value = contact
    nickname = _clean_nickname(body.nickname)
    if _count_rate(db, f"child_start:ip:{ip}") >= settings.guest_start_limit_ip:
        raise TOO_MANY
    contact_bucket_name = f"approval_send:contact:{contact_bucket(value)}"
    if _count_rate(db, contact_bucket_name) >= settings.approval_send_limit_contact:
        raise TOO_MANY
    student = create_guest_student(
        db,
        GuestStartIn(
            curriculum_id=body.curriculum_id,
            grade=body.grade,
            subject=body.subject,
            home_language=body.home_language,
            device_timezone=body.device_timezone,
        ),
    )
    token = new_token()
    row = GuardianApprovalRow(
        id=uuid.uuid4(),
        student_id=student.id,
        token_hash=hash_code(token),
        nickname=nickname,
        contact=value,
        contact_kind=kind,
        created_at=now_utc(),
        expires_at=expires_after(settings.approval_ttl_seconds),
    )
    db.add(row)
    db.flush()
    try:
        _send_link(row, token)
    except HTTPException:
        # Nothing reached the guardian, so nothing is kept about the child (the address's try
        # still counts, so a dead contact cannot be used to hammer the sender).
        db.rollback()
        _hit_rate(db, f"child_start:ip:{ip}")
        db.commit()
        raise
    _hit_rate(db, f"child_start:ip:{ip}")
    _hit_rate(db, contact_bucket_name)
    student_token = issue_auth_token(db, role="student", student_id=student.id)
    db.commit()
    return {
        "student_id": str(student.id),
        "token": student_token,
        "state": "pending",
        "display_name": GUEST_NAME,
        "contact_kind": kind,
    }


def child_status(db: Session, actor: Actor) -> dict[str, Any]:
    require(actor.is_student and actor.student_id is not None)
    assert actor.student_id is not None
    row = db.scalar(
        select(GuardianApprovalRow).where(GuardianApprovalRow.student_id == actor.student_id)
    )
    if row is not None:
        return {
            "state": "expired" if as_utc(row.expires_at) < now_utc() else "pending",
            "contact_kind": row.contact_kind,
            "expires_at": as_utc(row.expires_at).isoformat(),
        }
    student = db.get(StudentRow, actor.student_id)
    if student is None or is_guest(db, actor.student_id):
        return {"state": "none"}
    return {"state": "approved", "display_name": student.display_name}


def resend(db: Session, actor: Actor) -> dict[str, str]:
    """The child asks for the link to be sent again (a new token; the old one stops working)."""
    _require_enabled()
    require(actor.is_student and actor.student_id is not None)
    row = db.scalar(
        select(GuardianApprovalRow).where(GuardianApprovalRow.student_id == actor.student_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="nothing_pending")
    bucket = f"approval_send:contact:{contact_bucket(row.contact)}"
    if _count_rate(db, bucket) >= settings.approval_send_limit_contact:
        raise TOO_MANY
    token = new_token()
    row.token_hash = hash_code(token)
    row.expires_at = expires_after(settings.approval_ttl_seconds)
    _send_link(row, token)
    _hit_rate(db, bucket)
    return {"status": "sent"}


def _valid_row(db: Session, token: str) -> GuardianApprovalRow:
    row = db.scalar(
        select(GuardianApprovalRow).where(GuardianApprovalRow.token_hash == hash_code(token))
    )
    if row is None or as_utc(row.expires_at) < now_utc():
        raise HTTPException(status_code=404, detail=NOT_VALID)
    return row


def lookup(db: Session, token: str) -> dict[str, Any]:
    """What the guardian's screen shows: the nickname and the class and board the child gave
    (the guardian may correct them) and the guardian agreement's items. Not the contact."""
    _require_enabled()
    row = _valid_row(db, token)
    student = db.get(StudentRow, row.student_id)
    assert student is not None
    return {
        "nickname": row.nickname,
        "grade": student.grade,
        "curriculum_id": student.curriculum_id,
        "expires_at": as_utc(row.expires_at).isoformat(),
        "agreement": agreements.catalog("guardian"),
    }


def _guardian_user(db: Session, kind: str, contact: str) -> UserRow:
    column = UserRow.email if kind == "email" else UserRow.phone
    user = db.scalar(select(UserRow).where(column == contact))
    if user is not None:
        if user.role != "parent":
            # a teacher or admin address cannot be taken over by a child's typed contact
            raise HTTPException(status_code=409, detail="contact_not_a_guardian")
        return user
    user_id = uuid.uuid4()
    user = UserRow(
        id=user_id,
        role="parent",
        email=contact if kind == "email" else synthetic_email(user_id.hex),
        phone=contact if kind == "phone" else None,
        locale="en",
        created_at=now_utc(),
    )
    db.add(user)
    db.flush()
    return user


def approve(db: Session, body: ApproveIn) -> dict[str, Any]:
    _require_enabled()
    row = _valid_row(db, body.token)
    error = agreements.items_error("guardian", body.accepted)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if body.version != agreements.VERSION:
        raise HTTPException(status_code=409, detail="agreement_version_changed")
    student = db.get(StudentRow, row.student_id)
    assert student is not None
    guest_owner = db.get(UserRow, student.parent_id)
    guardian = _guardian_user(db, row.contact_kind, row.contact)
    # The guardian may set or correct the class and the board before anything is kept.
    if body.grade is not None or body.curriculum_id is not None:
        apply_student_context(
            student,
            db,
            curriculum_id=resolve_curriculum_id(body.curriculum_id or student.curriculum_id),
            grade=body.grade or student.grade,
            current_chapter_id=None,
        )
        student.grade = body.grade or student.grade
    nickname = row.nickname
    student.parent_id = guardian.id
    student.display_name = nickname
    student.family_code = _family_code_for_parent(db, guardian.id)
    record_age(student, None, False)  # a child by definition: not an adult
    db.delete(row)
    db.flush()
    actor = Actor(role="parent", user_id=guardian.id, email=guardian.email)
    if agreements.active_agreement(db, guardian.id, "guardian") is None:
        agreements.store(db, guardian.id, "guardian", body.accepted)
    # This child's consent is exactly what was ticked here; other children keep theirs.
    agreements.apply_to_learner(db, actor, student, "guardian", body.accepted)
    if guest_owner is not None and guest_owner.role == "guest":
        db.delete(guest_owner)
    access = issue_auth_token(db, role="parent", user_id=guardian.id)
    db.commit()
    return {
        "status": "approved",
        "student_id": str(student.id),
        "display_name": nickname,
        "family_code": student.family_code,
        "access_token": access,
        "token_type": "bearer",
    }


def decline(db: Session, token: str) -> dict[str, str]:
    """No: the child's pending profile and the approval row are deleted, nothing is kept."""
    _require_enabled()
    row = _valid_row(db, token)
    student = db.get(StudentRow, row.student_id)
    assert student is not None
    owner = db.get(UserRow, student.parent_id)
    db.execute(delete(GuardianApprovalRow).where(GuardianApprovalRow.id == row.id))
    purge_students(db, [student.id])
    if owner is not None and owner.role == "guest":
        db.delete(owner)
    db.commit()
    return {"status": "declined"}


def purge_expired(db: Session, now: Any = None, dry_run: bool = False) -> int:
    """Retention: pending profiles whose link expired are deleted with the hidden guest owner.
    Returns how many. (Called by `python -m app.retention approvals`.)"""
    moment = now or now_utc()
    rows = db.execute(
        select(GuardianApprovalRow.id, GuardianApprovalRow.student_id).where(
            GuardianApprovalRow.expires_at < moment
        )
    ).all()
    if dry_run:
        return len(rows)
    for approval_id, student_id in rows:
        student = db.get(StudentRow, student_id)
        owner = db.get(UserRow, student.parent_id) if student else None
        db.execute(delete(GuardianApprovalRow).where(GuardianApprovalRow.id == approval_id))
        purge_students(db, [student_id])
        if owner is not None and owner.role == "guest":
            db.delete(owner)
        db.commit()
    return len(rows)
