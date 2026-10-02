from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.actor import Actor
from app.auth.authz import (
    can_export_family,
    can_manage_student,
    can_see_progress,
    can_start_session,
    can_teacher_query,
    require,
    student_or_404,
    teacher_visible_student_ids,
)
from app.auth.consent import active_consent, has_scope
from app.auth.scopes import CONSENT_SCOPES, DEFAULT_TIMEZONE
from app.auth.security import (
    as_utc,
    codes_match,
    expires_after,
    hash_code,
    hash_pin,
    new_token,
    now_utc,
    otp_code,
    verify_pin,
)
from app.auth.sender import OtpSender
from app.config import settings
from app.db.models import (
    AuthSessionRow,
    CheckpointTokenRow,
    ClassMembershipRow,
    ClassRow,
    ConsentRow,
    EventRow,
    OtpChallengeRow,
    RateEventRow,
    ReviewQueueRow,
    SessionRow,
    StudentRow,
    UserRow,
)

TOO_MANY = HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limited")
LOCKED = HTTPException(status_code=status.HTTP_423_LOCKED, detail="pin locked")


def _count_rate(session: Session, bucket: str) -> int:
    cutoff = expires_after(-settings.rate_window_seconds)
    rows = session.scalars(select(RateEventRow).where(RateEventRow.bucket == bucket)).all()
    return sum(1 for row in rows if as_utc(row.created_at) >= cutoff)


def _hit_rate(session: Session, bucket: str) -> None:
    session.add(RateEventRow(id=uuid.uuid4(), bucket=bucket, created_at=now_utc()))


def request_otp(
    session: Session,
    sender: OtpSender,
    *,
    email: str,
    ip: str,
    actor: Actor | None,
) -> None:
    if actor is not None and actor.role in {"student", "comparison"}:
        raise HTTPException(status_code=403, detail="forbidden")
    email = email.strip().lower()
    if actor is not None and actor.email and actor.email != email:
        raise HTTPException(status_code=403, detail="forbidden")
    if _count_rate(session, f"otp_request:email:{email}") >= settings.otp_request_limit_email:
        raise TOO_MANY
    if _count_rate(session, f"otp_request:ip:{ip}") >= settings.otp_request_limit_ip:
        raise TOO_MANY
    existing = session.scalar(select(UserRow).where(UserRow.email == email))
    if existing is None and actor is not None and actor.role in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="forbidden")
    _hit_rate(session, f"otp_request:email:{email}")
    _hit_rate(session, f"otp_request:ip:{ip}")
    code = otp_code()
    session.add(
        OtpChallengeRow(
            id=uuid.uuid4(),
            email=email,
            code_hash=hash_code(code),
            ip=ip,
            created_at=now_utc(),
            expires_at=expires_after(settings.otp_ttl_seconds),
        )
    )
    sender.send(email, code)


def verify_otp(
    session: Session,
    *,
    email: str,
    code: str,
    ip: str,
    actor: Actor | None,
) -> str:
    if actor is not None and actor.role in {"student", "comparison"}:
        raise HTTPException(status_code=403, detail="forbidden")
    email = email.strip().lower()
    if actor is not None and actor.email and actor.email != email:
        raise HTTPException(status_code=403, detail="forbidden")
    if _count_rate(session, f"otp_verify:email:{email}") >= settings.otp_verify_limit_email:
        raise TOO_MANY
    _hit_rate(session, f"otp_verify:email:{email}")
    challenge = session.scalar(
        select(OtpChallengeRow)
        .where(OtpChallengeRow.email == email, OtpChallengeRow.consumed_at.is_(None))
        .order_by(OtpChallengeRow.created_at.desc())
    )
    if challenge is None or as_utc(challenge.expires_at) < now_utc():
        raise HTTPException(status_code=401, detail="invalid otp")
    if challenge.consumed_at is not None or challenge.attempts >= 5:
        raise HTTPException(status_code=401, detail="invalid otp")
    if not codes_match(challenge.code_hash, hash_code(code)):
        challenge.attempts += 1
        if challenge.attempts >= 5:
            challenge.consumed_at = now_utc()
        raise HTTPException(status_code=401, detail="invalid otp")
    challenge.consumed_at = now_utc()
    user = session.scalar(select(UserRow).where(UserRow.email == email))
    if user is None:
        user = UserRow(
            id=uuid.uuid4(),
            role="parent",
            email=email,
            locale="en",
            created_at=now_utc(),
        )
        session.add(user)
        session.flush()
    return issue_auth_token(session, role=user.role, user_id=user.id)


def issue_auth_token(
    session: Session,
    *,
    role: str,
    user_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    checkpoint_id: str | None = None,
    checkpoint_form: str | None = None,
) -> str:
    token = new_token()
    session.add(
        AuthSessionRow(
            id=uuid.uuid4(),
            token_hash=hash_code(token),
            role=role,
            user_id=user_id,
            student_id=student_id,
            checkpoint_id=checkpoint_id,
            checkpoint_form=checkpoint_form,
            expires_at=expires_after(settings.session_ttl_seconds),
            created_at=now_utc(),
        )
    )
    return token


def resolve_token(session: Session, token: str) -> Actor:
    row = session.scalar(
        select(AuthSessionRow).where(AuthSessionRow.token_hash == hash_code(token))
    )
    if row is None or as_utc(row.expires_at) < now_utc():
        raise HTTPException(status_code=401, detail="invalid session")
    email = None
    if row.user_id:
        user = session.get(UserRow, row.user_id)
        email = user.email if user else None
    return Actor(
        role=row.role,
        user_id=row.user_id,
        student_id=row.student_id,
        email=email,
        checkpoint_id=row.checkpoint_id,
        checkpoint_form=row.checkpoint_form,
    )


def create_student(
    session: Session,
    actor: Actor,
    *,
    display_name: str,
    grade: int,
    board: str,
    home_language: str,
    exam_language: str,
    parent_id: uuid.UUID | None = None,
    current_chapter_id: str | None = None,
) -> StudentRow:
    if actor.role in {"student", "teacher", "comparison"}:
        raise HTTPException(status_code=403, detail="forbidden")
    owner = actor.user_id if actor.is_parent else parent_id
    if actor.is_parent:
        require(parent_id is None or parent_id == actor.user_id)
        owner = actor.user_id
    if actor.is_admin:
        if owner is None:
            raise HTTPException(status_code=400, detail="parent_id required")
    if owner is None:
        raise HTTPException(status_code=403, detail="forbidden")
    parent = session.get(UserRow, owner)
    if parent is None or parent.role != "parent":
        raise HTTPException(status_code=400, detail="parent not found")
    if board not in DEFAULT_TIMEZONE:
        raise HTTPException(status_code=400, detail="invalid board")
    student = StudentRow(
        id=uuid.uuid4(),
        parent_id=owner,
        display_name=display_name,
        grade=grade,
        board=board,
        home_language=home_language,
        exam_language=exam_language,
        current_chapter_id=current_chapter_id,
        timezone=DEFAULT_TIMEZONE[board],
        pin_failed_attempts=0,
        created_at=now_utc(),
    )
    session.add(student)
    session.flush()
    return student


def grant_consent(
    session: Session,
    actor: Actor,
    student_id: uuid.UUID,
    *,
    version: str,
    scopes: list[str],
) -> ConsentRow:
    student = student_or_404(session, student_id)
    require(can_manage_student(actor, student))
    unknown = set(scopes) - CONSENT_SCOPES
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown scopes: {sorted(unknown)}")
    existing = active_consent(session, student_id)
    if existing:
        existing.revoked_at = now_utc()
    row = ConsentRow(
        id=uuid.uuid4(),
        student_id=student_id,
        parent_id=student.parent_id,
        version=version,
        scopes=list(scopes),
        granted_at=now_utc(),
    )
    session.add(row)
    session.flush()
    return row


def revoke_consent(session: Session, actor: Actor, student_id: uuid.UUID) -> None:
    student = student_or_404(session, student_id)
    require(can_manage_student(actor, student))
    row = active_consent(session, student_id)
    if row:
        row.revoked_at = now_utc()


def set_pin(session: Session, actor: Actor, student_id: uuid.UUID, pin: str) -> None:
    student = student_or_404(session, student_id)
    require(can_manage_student(actor, student))
    if not pin.isdigit() or not (4 <= len(pin) <= 6):
        raise HTTPException(status_code=400, detail="pin must be 4-6 digits")
    student.pin_hash = hash_pin(pin)
    student.pin_failed_attempts = 0
    student.pin_locked_until = None


def verify_student_pin(session: Session, student_id: uuid.UUID, pin: str) -> str:
    student = student_or_404(session, student_id)
    if student.pin_hash is None:
        raise HTTPException(status_code=400, detail="pin not set")
    if student.pin_locked_until and as_utc(student.pin_locked_until) > now_utc():
        raise LOCKED
    if not verify_pin(pin, student.pin_hash):
        student.pin_failed_attempts += 1
        if student.pin_failed_attempts >= settings.pin_max_attempts:
            student.pin_locked_until = expires_after(settings.pin_lockout_seconds)
        raise HTTPException(status_code=401, detail="invalid pin")
    student.pin_failed_attempts = 0
    student.pin_locked_until = None
    return issue_auth_token(session, role="student", student_id=student.id)


def get_student(session: Session, actor: Actor, student_id: uuid.UUID) -> StudentRow:
    student = student_or_404(session, student_id)
    require(can_see_progress(session, actor, student) or can_manage_student(actor, student))
    return student


def student_progress(session: Session, actor: Actor, student_id: uuid.UUID) -> dict[str, Any]:
    student = student_or_404(session, student_id)
    require(can_see_progress(session, actor, student))
    consent = active_consent(session, student.id)
    return {
        "student_id": str(student.id),
        "display_name": student.display_name,
        "current_chapter_id": student.current_chapter_id,
        "scopes": sorted(consent.scopes) if consent else [],
    }


def export_family(session: Session, actor: Actor, parent_id: uuid.UUID) -> dict[str, Any]:
    require(can_export_family(actor, parent_id))
    user = session.get(UserRow, parent_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    students = session.scalars(select(StudentRow).where(StudentRow.parent_id == parent_id)).all()
    consents = session.scalars(
        select(ConsentRow).where(ConsentRow.parent_id == parent_id)
    ).all()
    return {
        "user": {"id": str(user.id), "email": user.email, "role": user.role, "locale": user.locale},
        "students": [
            {
                "id": str(s.id),
                "display_name": s.display_name,
                "grade": s.grade,
                "board": s.board,
                "timezone": s.timezone,
            }
            for s in students
        ],
        "consents": [
            {
                "id": str(c.id),
                "student_id": str(c.student_id),
                "scopes": list(c.scopes or []),
                "version": c.version,
                "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
            }
            for c in consents
        ],
    }


def delete_family(session: Session, actor: Actor, parent_id: uuid.UUID) -> None:
    require(can_export_family(actor, parent_id))
    students = session.scalars(select(StudentRow).where(StudentRow.parent_id == parent_id)).all()
    ids = [s.id for s in students]
    if ids:
        session_ids = session.scalars(
            select(SessionRow.id).where(SessionRow.student_id.in_(ids))
        ).all()
        if session_ids:
            session.execute(delete(EventRow).where(EventRow.session_id.in_(session_ids)))
        session.execute(delete(SessionRow).where(SessionRow.student_id.in_(ids)))
        session.execute(delete(ReviewQueueRow).where(ReviewQueueRow.student_id.in_(ids)))
        session.execute(delete(ClassMembershipRow).where(ClassMembershipRow.student_id.in_(ids)))
        session.execute(delete(ConsentRow).where(ConsentRow.student_id.in_(ids)))
        session.execute(delete(AuthSessionRow).where(AuthSessionRow.student_id.in_(ids)))
        session.execute(delete(StudentRow).where(StudentRow.id.in_(ids)))
    session.execute(delete(AuthSessionRow).where(AuthSessionRow.user_id == parent_id))
    session.execute(delete(ConsentRow).where(ConsentRow.parent_id == parent_id))
    user = session.get(UserRow, parent_id)
    if user:
        session.delete(user)


def start_session(
    session: Session, actor: Actor, student_id: uuid.UUID, session_type: str
) -> SessionRow:
    student = student_or_404(session, student_id)
    require(can_start_session(actor, student))
    if not has_scope(session, student_id, "tutoring"):
        raise HTTPException(status_code=403, detail="tutoring consent required")
    if session_type not in {"practice", "diagnostic", "checkpoint"}:
        raise HTTPException(status_code=400, detail="invalid session type")
    existing = session.scalar(
        select(SessionRow).where(
            SessionRow.student_id == student_id,
            SessionRow.type == session_type,
            SessionRow.ended_at.is_(None),
        )
    )
    if existing:
        return existing
    idle = session.scalar(
        select(SessionRow).where(
            SessionRow.student_id == student_id,
            SessionRow.type == session_type,
            SessionRow.resumable.is_(True),
        )
    )
    if idle:
        idle.ended_at = None
        idle.ended_reason = None
        idle.resumable = False
        idle.last_active_at = now_utc()
        return idle
    row = SessionRow(
        id=uuid.uuid4(),
        student_id=student_id,
        started_at=now_utc(),
        type=session_type,
        last_active_at=now_utc(),
        plan={},
    )
    session.add(row)
    session.flush()
    return row


def post_session_event(
    session: Session,
    actor: Actor,
    session_id: uuid.UUID,
    *,
    client_event_id: uuid.UUID,
    event_type: str,
    item_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = session.get(SessionRow, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="session not found")
    student = student_or_404(session, row.student_id)
    require(can_start_session(actor, student) or actor.is_admin)
    if not has_scope(session, row.student_id, "tutoring"):
        row.ended_at = now_utc()
        row.ended_reason = "consent_revoked"
        row.resumable = False
        return {
            "session_id": str(row.id),
            "duplicate": False,
            "action": {"type": "end_session", "reason": "consent_revoked"},
            "progress": {"items_completed": 0, "active_ms": row.active_ms, "resumable": False},
            "llm_called": False,
        }
    prior = session.scalar(select(EventRow).where(EventRow.client_event_id == client_event_id))
    if prior:
        return {
            "session_id": str(row.id),
            "duplicate": True,
            "action": {"type": "show_item", "item_id": prior.item_id},
            "progress": {"items_completed": 0, "active_ms": row.active_ms, "resumable": True},
            "llm_called": row.llm_called,
        }
    session.add(
        EventRow(
            id=uuid.uuid4(),
            client_event_id=client_event_id,
            session_id=row.id,
            item_id=item_id,
            event_type=event_type,
            payload=payload,
            created_at=now_utc(),
            state_before=payload.get("state_before"),
            state_after=payload.get("state_after"),
            rule_id=payload.get("rule_id"),
        )
    )
    row.last_active_at = now_utc()
    return {
        "session_id": str(row.id),
        "duplicate": False,
        "action": {"type": "show_item", "item_id": item_id},
        "progress": {"items_completed": 0, "active_ms": row.active_ms, "resumable": True},
        "llm_called": False,
    }


def create_class(session: Session, actor: Actor, *, name: str, board: str) -> ClassRow:
    require(actor.is_teacher or actor.is_admin)
    teacher_id = actor.user_id
    if teacher_id is None:
        raise HTTPException(status_code=403, detail="forbidden")
    row = ClassRow(
        id=uuid.uuid4(),
        teacher_id=teacher_id,
        name=name,
        board=board,
        created_at=now_utc(),
    )
    session.add(row)
    session.flush()
    return row


def add_class_member(
    session: Session, actor: Actor, class_id: uuid.UUID, student_id: uuid.UUID
) -> None:
    klass = session.get(ClassRow, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="class not found")
    require(actor.is_admin or (actor.is_teacher and actor.user_id == klass.teacher_id))
    student_or_404(session, student_id)
    session.merge(ClassMembershipRow(class_id=class_id, student_id=student_id))


def teacher_class_view(
    session: Session, actor: Actor, class_id: uuid.UUID, kind: str
) -> dict[str, Any]:
    require(can_teacher_query(actor))
    klass = session.get(ClassRow, class_id)
    if klass is None:
        raise HTTPException(status_code=404, detail="class not found")
    if actor.is_teacher and actor.user_id != klass.teacher_id:
        raise HTTPException(status_code=403, detail="forbidden")
    member_ids = [
        mid
        for (mid,) in session.execute(
            select(ClassMembershipRow.student_id).where(ClassMembershipRow.class_id == class_id)
        ).all()
    ]
    if actor.is_admin:
        visible = set(member_ids)
    else:
        visible = {sid for sid in member_ids if has_scope(session, sid, "teacher_share")}
    members = session.scalars(select(StudentRow).where(StudentRow.id.in_(visible))).all()
    return {
        "kind": kind,
        "class_id": str(class_id),
        "students": [{"id": str(s.id), "display_name": s.display_name} for s in members],
    }


def review_queue(session: Session, actor: Actor) -> dict[str, Any]:
    require(can_teacher_query(actor))
    if actor.is_teacher and actor.user_id:
        visible = teacher_visible_student_ids(session, actor.user_id)
        items = session.scalars(
            select(ReviewQueueRow).where(ReviewQueueRow.student_id.in_(visible))
        ).all()
    else:
        items = session.scalars(select(ReviewQueueRow)).all()
    return {"items": [{"id": str(i.id), "student_id": str(i.student_id)} for i in items]}


def analytics_export(session: Session, actor: Actor) -> dict[str, Any]:
    require(actor.is_admin)
    students = session.scalars(select(StudentRow)).all()
    rows = []
    for student in students:
        if has_scope(session, student.id, "research_pseudonymised"):
            rows.append(
                {
                    "student_id": str(student.id),
                    "board": student.board,
                    "grade": student.grade,
                    "timezone": student.timezone,
                }
            )
    return {"students": rows}


def issue_checkpoint_token(
    session: Session,
    actor: Actor,
    *,
    checkpoint_id: str,
    form: str,
    consent_id: uuid.UUID | None,
) -> str:
    require(actor.is_admin)
    if form not in {"A", "B"}:
        raise HTTPException(status_code=400, detail="form must be A or B")
    if consent_id is None:
        raise HTTPException(status_code=400, detail="consent_ref required")
    consent = session.get(ConsentRow, consent_id)
    if consent is None or consent.revoked_at is not None:
        raise HTTPException(status_code=400, detail="consent required")
    token = new_token()
    session.add(
        CheckpointTokenRow(
            id=uuid.uuid4(),
            checkpoint_id=checkpoint_id,
            form=form,
            token_hash=hash_code(token),
            consent_id=consent_id,
            expires_at=expires_after(settings.session_ttl_seconds),
            issued_at=now_utc(),
        )
    )
    return token


def redeem_checkpoint_token(session: Session, raw: str) -> str:
    row = session.scalar(
        select(CheckpointTokenRow).where(CheckpointTokenRow.token_hash == hash_code(raw))
    )
    if row is None or as_utc(row.expires_at) < now_utc():
        raise HTTPException(status_code=401, detail="invalid token")
    return issue_auth_token(
        session,
        role="comparison",
        checkpoint_id=row.checkpoint_id,
        checkpoint_form=row.form,
    )


def load_checkpoint_form(actor: Actor, checkpoint_id: str, form: str) -> dict[str, str]:
    if actor.is_comparison:
        require(actor.checkpoint_id == checkpoint_id and actor.checkpoint_form == form)
        return {"checkpoint_id": checkpoint_id, "form": form}
    raise HTTPException(status_code=403, detail="forbidden")
