"""Video job API: queue, poll, cancel and retry engine video builds."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.authz import FORBIDDEN
from app.auth.consent import has_scope
from app.auth.deps import ActorDep, DbSession
from app.auth.security import now_utc
from app.db.models import VideoJobRow

router = APIRouter(prefix="/video-jobs", tags=["video-jobs"])

# Error codes the engine emits that mean "not ready yet, not a fault".
_NOT_READY_CODES = {"no_curriculum_data", "no_lesson_for_topic"}

# Student-facing messages per error code.
_ERROR_MESSAGES: dict[str, str] = {
    "no_curriculum_data": "This topic isn't available yet.",
    "no_lesson_for_topic": "This topic isn't available yet.",
    "invalid_request": "Something went wrong — please try again.",
    "knowledge_base_invalid": "Something went wrong — please try again.",
    "ungrounded_claims": "Something went wrong — please try again.",
    "build_failed": "Something went wrong — please try again.",
    "render_failed": "Something went wrong — please try again.",
    "qa_failed": "Something went wrong — please try again.",
    "cancelled": "Request was cancelled.",
}

_STAGE_LABELS: dict[str, str] = {
    "request": "Preparing request…",
    "retrieve": "Looking up topic…",
    "ground": "Checking sources…",
    "build": "Building lesson…",
    "render": "Rendering video…",
    "qa": "Checking quality…",
    "job": "Finishing up…",
}


# ── request / response schemas ──────────────────────────────────────────────


class CreateJobIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    idempotency_key: str


class JobOut(BaseModel):
    id: uuid.UUID
    node_id: str
    status: str
    stage: str | None
    stage_label: str | None
    error_code: str | None
    error_message: str | None
    events: list[Any]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


# ── helpers ──────────────────────────────────────────────────────────────────


def _require_student_tutoring(actor: ActorDep, db: DbSession) -> uuid.UUID:
    """Return the student_id from the actor, or 403."""
    if not actor.is_student or actor.student_id is None:
        raise FORBIDDEN
    if not has_scope(db, actor.student_id, "tutoring"):
        raise HTTPException(status_code=403, detail="tutoring consent required")
    return actor.student_id


def _job_or_404(db: DbSession, job_id: uuid.UUID) -> VideoJobRow:
    row = db.get(VideoJobRow, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="video job not found")
    return row


def _require_owner(actor: ActorDep, job: VideoJobRow) -> None:
    if actor.is_admin:
        return
    if actor.is_student and actor.student_id == job.student_id:
        return
    raise FORBIDDEN


def _job_view(row: VideoJobRow) -> dict[str, Any]:
    return JobOut(
        id=row.id,
        node_id=row.node_id,
        status=row.status,
        stage=row.stage,
        stage_label=_STAGE_LABELS.get(row.stage or "", None),
        error_code=row.error_code,
        error_message=_ERROR_MESSAGES.get(row.error_code or "", None),
        events=row.events or [],
        created_at=row.created_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
    ).model_dump()


# ── endpoints ────────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_job(
    body: CreateJobIn, db: DbSession, actor: ActorDep, response: Response
) -> dict[str, Any]:
    """Queue an engine video job.

    Idempotent on ``idempotency_key``: a second call with the same key from
    the same student returns the existing job with 200 instead of 202.
    """
    student_id = _require_student_tutoring(actor, db)

    existing = db.scalar(
        select(VideoJobRow).where(VideoJobRow.idempotency_key == body.idempotency_key)
    )
    if existing is not None:
        if existing.student_id != student_id:
            raise HTTPException(status_code=409, detail="idempotency key already used")
        response.status_code = status.HTTP_200_OK
        return _job_view(existing)

    row = VideoJobRow(
        id=uuid.uuid4(),
        student_id=student_id,
        node_id=body.node_id,
        request_json={
            "requestId": str(uuid.uuid4()),
            "idempotencyKey": body.idempotency_key,
            "curriculum": {"nodeId": body.node_id},
            "options": {"locale": "en", "voice": "default", "fps": 24, "theme": "light"},
        },
        idempotency_key=body.idempotency_key,
        status="queued",
        events=[],
        created_at=now_utc(),
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(VideoJobRow).where(VideoJobRow.idempotency_key == body.idempotency_key)
        )
        if existing is not None and existing.student_id == student_id:
            response.status_code = status.HTTP_200_OK
            return _job_view(existing)
        raise HTTPException(status_code=409, detail="idempotency key conflict") from None

    return _job_view(row)


@router.get("/{job_id}")
def get_job(job_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    row = _job_or_404(db, job_id)
    _require_owner(actor, row)
    return _job_view(row)


@router.post("/{job_id}/cancel")
def cancel_job(job_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Cancel a queued or running job.

    A queued job is cancelled immediately. A running job is marked cancelled;
    the worker sends SIGTERM to the engine process on its next poll.
    """
    row = _job_or_404(db, job_id)
    _require_owner(actor, row)
    if row.status not in ("queued", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"job is {row.status} and cannot be cancelled",
        )
    row.status = "cancelled"
    row.error_code = "cancelled"
    row.completed_at = now_utc()
    db.commit()
    db.refresh(row)
    return _job_view(row)


@router.post("/{job_id}/retry", status_code=status.HTTP_201_CREATED)
def retry_job(job_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Create a new queued job from a failed one, with a fresh idempotency key."""
    original = _job_or_404(db, job_id)
    _require_owner(actor, original)
    if original.status != "failed":
        raise HTTPException(
            status_code=409,
            detail=f"job is {original.status}; only failed jobs can be retried",
        )
    new_idem = str(uuid.uuid4())
    row = VideoJobRow(
        id=uuid.uuid4(),
        student_id=original.student_id,
        node_id=original.node_id,
        request_json={
            "requestId": str(uuid.uuid4()),
            "idempotencyKey": new_idem,
            "curriculum": {"nodeId": original.node_id},
            "options": {"locale": "en", "voice": "default", "fps": 24, "theme": "light"},
        },
        idempotency_key=new_idem,
        status="queued",
        events=[],
        created_at=now_utc(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _job_view(row)
