from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import service
from app.auth.deps import ActorDep, DbSession, OptionalActorDep, OtpDep, client_ip

router = APIRouter()


class EmailIn(BaseModel):
    email: str


class VerifyOtpIn(BaseModel):
    email: str
    code: str


class StudentIn(BaseModel):
    display_name: str
    grade: int
    board: str
    home_language: str = "en"
    exam_language: str = "en"
    parent_id: uuid.UUID | None = None
    current_chapter_id: str | None = None


class ConsentIn(BaseModel):
    version: str
    scopes: list[str]
    paper_ref: str | None = None


class FamilyLoginIn(BaseModel):
    family_code: str
    pin: str = Field(min_length=4, max_length=6)


class PinIn(BaseModel):
    pin: str = Field(min_length=4, max_length=6)


class SessionIn(BaseModel):
    student_id: uuid.UUID
    type: str
    chapter_id: str | None = None


class EventIn(BaseModel):
    client_event_id: uuid.UUID
    event_type: str
    item_id: str | None = None
    payload: dict[str, Any] = {}


class ClassIn(BaseModel):
    name: str
    board: str


class MemberIn(BaseModel):
    student_id: uuid.UUID


class TokenIn(BaseModel):
    participant_id: uuid.UUID
    form: str | None = None
    consent_id: uuid.UUID | None = None


class StudyIn(BaseModel):
    site_id: str
    group: str
    consent_id: uuid.UUID
    student_id: uuid.UUID | None = None
    household_id: str | None = None


class CheckpointAnswersIn(BaseModel):
    answers: list[dict[str, Any]]
    occasion: str = "pretest"


class RedeemIn(BaseModel):
    token: str


def _token_body(token: str) -> dict[str, str]:
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/request-otp")
def request_otp(
    body: EmailIn,
    request: Request,
    db: DbSession,
    sender: OtpDep,
    actor: OptionalActorDep,
) -> dict[str, str]:
    service.request_otp(db, sender, email=body.email, ip=client_ip(request), actor=actor)
    return {"status": "sent"}


@router.post("/auth/verify-otp")
def verify_otp(
    body: VerifyOtpIn,
    request: Request,
    db: DbSession,
    actor: OptionalActorDep,
) -> dict[str, str]:
    token = service.verify_otp(
        db, email=body.email, code=body.code, ip=client_ip(request), actor=actor
    )
    return _token_body(token)


@router.post("/students")
def create_student(body: StudentIn, db: DbSession, actor: ActorDep) -> dict[str, str]:
    student = service.create_student(
        db,
        actor,
        display_name=body.display_name,
        grade=body.grade,
        board=body.board,
        home_language=body.home_language,
        exam_language=body.exam_language,
        parent_id=body.parent_id,
        current_chapter_id=body.current_chapter_id,
    )
    return {"id": str(student.id), "family_code": student.family_code or ""}


@router.get("/students/{student_id}")
def get_student(student_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    student = service.get_student(db, actor, student_id)
    return {
        "id": str(student.id),
        "display_name": student.display_name,
        "board": student.board,
        "timezone": student.timezone,
    }


@router.post("/students/{student_id}/consent")
def grant_consent(
    student_id: uuid.UUID, body: ConsentIn, db: DbSession, actor: ActorDep
) -> dict[str, Any]:
    row = service.grant_consent(
        db, actor, student_id, version=body.version, scopes=body.scopes, paper_ref=body.paper_ref
    )
    return {"id": str(row.id), "scopes": list(row.scopes), "paper_ref": row.paper_ref}


@router.post("/students/{student_id}/consent/revoke")
def revoke_consent(student_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, str]:
    service.revoke_consent(db, actor, student_id)
    return {"status": "revoked"}


@router.post("/students/{student_id}/pin")
def set_pin(student_id: uuid.UUID, body: PinIn, db: DbSession, actor: ActorDep) -> dict[str, str]:
    service.set_pin(db, actor, student_id, body.pin)
    return {"status": "ok"}


@router.post("/students/{student_id}/pin/verify")
def verify_pin(student_id: uuid.UUID, body: PinIn, db: DbSession) -> dict[str, str]:
    token = service.verify_student_pin(db, student_id, body.pin)
    return _token_body(token)


@router.post("/auth/student-login")
def student_login(body: FamilyLoginIn, db: DbSession) -> dict[str, str]:
    token = service.verify_family_pin(db, body.family_code, body.pin)
    return _token_body(token)


@router.get("/students/me/today")
def today(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.student_today(db, actor)


@router.get("/students/{student_id}/chapters")
def student_chapters(student_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.student_chapters(db, actor, student_id)


@router.get("/students/{student_id}/chapters/{chapter_id}/skills")
def student_chapter_skills(
    student_id: uuid.UUID, chapter_id: str, db: DbSession, actor: ActorDep
) -> dict[str, Any]:
    return service.student_chapter_skills(db, actor, student_id, chapter_id)


@router.post("/students/{student_id}/chapters/{chapter_id}/skills/{skill_id}/skip-ahead")
def skip_ahead(
    student_id: uuid.UUID, chapter_id: str, skill_id: str, db: DbSession, actor: ActorDep
) -> dict[str, Any]:
    from app.player.runtime import session_view

    row = service.start_test_out(db, actor, student_id, chapter_id, skill_id)
    return session_view(db, actor, row)


@router.get("/students/{student_id}/progress")
def progress(student_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.student_progress(db, actor, student_id)


@router.get("/parents/me/export")
def export_me(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    if actor.user_id is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="forbidden")
    return service.export_family(db, actor, actor.user_id)


@router.delete("/parents/me")
def delete_me(db: DbSession, actor: ActorDep) -> dict[str, str]:
    if actor.user_id is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="forbidden")
    service.delete_family(db, actor, actor.user_id)
    return {"status": "deleted"}


@router.get("/parents/{parent_id}/export")
def export_parent(parent_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.export_family(db, actor, parent_id)


@router.delete("/parents/{parent_id}")
def delete_parent(parent_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, str]:
    service.delete_family(db, actor, parent_id)
    return {"status": "deleted"}


@router.post("/sessions")
def start_session(body: SessionIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    from app.player.runtime import session_view

    row = service.start_session(db, actor, body.student_id, body.type, body.chapter_id)
    view = session_view(db, actor, row)
    return view


@router.get("/sessions/{session_id}")
def get_session(session_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    from app.db.models import SessionRow
    from app.player.runtime import session_view

    row = db.get(SessionRow, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session_view(db, actor, row)


@router.post("/sessions/{session_id}/events")
def post_event(
    session_id: uuid.UUID, body: EventIn, db: DbSession, actor: ActorDep
) -> dict[str, Any]:
    return service.post_session_event(
        db,
        actor,
        session_id,
        client_event_id=body.client_event_id,
        event_type=body.event_type,
        item_id=body.item_id,
        payload=body.payload,
    )


@router.post("/classes")
def create_class(body: ClassIn, db: DbSession, actor: ActorDep) -> dict[str, str]:
    row = service.create_class(db, actor, name=body.name, board=body.board)
    return {"id": str(row.id)}


@router.post("/classes/{class_id}/members")
def add_member(
    class_id: uuid.UUID, body: MemberIn, db: DbSession, actor: ActorDep
) -> dict[str, str]:
    service.add_class_member(db, actor, class_id, body.student_id)
    return {"status": "ok"}


@router.get("/teacher/classes/{class_id}/heatmap")
def heatmap(class_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.teacher_class_view(db, actor, class_id, "heatmap")


@router.get("/teacher/classes/{class_id}/stuck")
def stuck(class_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.teacher_class_view(db, actor, class_id, "stuck")


@router.get("/teacher/review-queue")
def review_queue(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.review_queue(db, actor)
