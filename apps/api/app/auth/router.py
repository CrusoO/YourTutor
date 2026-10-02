from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.auth import service
from app.auth.deps import ActorDep, DbSession, OptionalActorDep, OtpDep, client_ip
from app.checkpoint.study import COOKIE_NAME, REFERRER_POLICY
from app.config import settings

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


class PinIn(BaseModel):
    pin: str = Field(min_length=4, max_length=6)


class SessionIn(BaseModel):
    student_id: uuid.UUID
    type: str


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
    return {"id": str(student.id)}


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
    row = service.grant_consent(db, actor, student_id, version=body.version, scopes=body.scopes)
    return {"id": str(row.id), "scopes": list(row.scopes)}


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
    row = service.start_session(db, actor, body.student_id, body.type)
    return {"id": str(row.id), "type": row.type, "student_id": str(row.student_id)}


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


@router.get("/analytics/export")
def analytics(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.analytics_export(db, actor)


@router.post("/study/participants")
def enrol_participant(body: StudyIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    row = service.enrol_study_participant(
        db,
        actor,
        site_id=body.site_id,
        group=body.group,
        consent_id=body.consent_id,
        student_id=body.student_id,
        household_id=body.household_id,
    )
    return {
        "id": str(row.id),
        "group": row.group,
        "site_id": row.site_id,
        "household_id": row.household_id,
        "pretest_form": row.pretest_form,
        "posttest_form": row.posttest_form,
        "assignment_method": row.assignment_method,
        "assignment_seed": row.assignment_seed,
        "pseudonym": row.pseudonymous_code,
    }


@router.post("/checkpoints/{checkpoint_id}/tokens")
def issue_token(
    checkpoint_id: str, body: TokenIn, db: DbSession, actor: ActorDep
) -> dict[str, Any]:
    return service.issue_checkpoint_token(
        db,
        actor,
        checkpoint_id=checkpoint_id,
        participant_id=body.participant_id,
        form=body.form,
        consent_id=body.consent_id,
    )


@router.post("/checkpoints/redeem")
def redeem(body: RedeemIn, db: DbSession) -> dict[str, str]:
    return _token_body(service.redeem_checkpoint_token(db, body.token))


@router.get("/checkpoints/{checkpoint_id}/forms/{form}")
def load_form(
    checkpoint_id: str,
    form: str,
    request: Request,
    db: DbSession,
    actor: OptionalActorDep,
    token: str | None = Query(default=None),
) -> Any:
    if token:
        service.lookup_checkpoint_token(db, token)
        redirect = RedirectResponse(url=str(request.url.replace(query="")), status_code=302)
        redirect.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            max_age=settings.session_ttl_seconds,
            samesite="lax",
            path="/",
        )
        redirect.headers["Referrer-Policy"] = REFERRER_POLICY
        return redirect
    resolved = actor or service.actor_from_checkpoint_cookie(db, request.cookies.get(COOKIE_NAME))
    if resolved is None:
        raise HTTPException(status_code=401, detail="authentication required")
    payload = service.load_checkpoint_form(db, resolved, checkpoint_id, form)
    return JSONResponse(payload, headers={"Referrer-Policy": REFERRER_POLICY})


@router.post("/checkpoints/{checkpoint_id}/forms/{form}/submit")
def submit_form(
    checkpoint_id: str,
    form: str,
    body: CheckpointAnswersIn,
    request: Request,
    actor: OptionalActorDep,
    db: DbSession,
) -> dict[str, Any]:
    raw = request.cookies.get(COOKIE_NAME)
    resolved = actor or service.actor_from_checkpoint_cookie(db, raw)
    if resolved is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return service.submit_checkpoint_form(
        db,
        resolved,
        checkpoint_id=checkpoint_id,
        form=form,
        answers=body.answers,
        occasion=body.occasion,
        raw_token=raw,
    )
