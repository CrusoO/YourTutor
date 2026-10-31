"""Video job API: queue, poll, cancel and retry engine video builds."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.ask.config import load_safety
from app.ask.guard import clean_question, screen
from app.auth.authz import FORBIDDEN
from app.auth.consent import has_scope
from app.auth.deps import ActorDep, DbSession
from app.auth.security import now_utc
from app.config import settings
from app.db.models import ChapterRow, SectionRow, StudentRow, VideoJobRow
from app.explain import proof
from app.registries.loaders import load_curriculum

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


PROMPT_MAX_CHARS = 300
STORY_MAX_CHARS = 120_000


class SourceSectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(max_length=proof.HEADING_MAX)
    body: str = Field(max_length=proof.BODY_MAX)


class SourceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=proof.TITLE_MAX)
    sections: list[SourceSectionIn] = Field(min_length=1, max_length=10)


class CreateJobIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str | None = None
    prompt: str | None = None
    source: SourceIn | None = None
    source_proof: str | None = None
    story: dict[str, Any] | None = None
    story_proof: str | None = None
    idempotency_key: str

    @model_validator(mode="after")
    def _exactly_one(self) -> CreateJobIn:
        given = (self.node_id, self.prompt, self.source, self.story)
        if sum(x is not None for x in given) != 1:
            raise ValueError("give exactly one of node_id, prompt, source or story")
        if (self.source is None) != (self.source_proof is None):
            raise ValueError("a source needs its proof, and only a source has one")
        if (self.story is None) != (self.story_proof is None):
            raise ValueError("a story needs its proof, and only a story has one")
        return self


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


# ── helpers ──────────────────────────────────────────────────────────────────


def _strip_paths(obj: Any) -> Any:
    """Remove 'path' keys (engine-internal filesystem references) from the JSON tree."""
    if isinstance(obj, dict):
        return {k: _strip_paths(v) for k, v in obj.items() if k != "path"}
    if isinstance(obj, list):
        return [_strip_paths(item) for item in obj]
    return obj


def _curriculum_from_node_id(node_id: str) -> dict[str, Any]:
    """Parse a node_id like 'cbse.10.maths.ch02.s2_3' into the engine's curriculum object.

    The engine's LessonRequest schema requires board (uppercase enum), grade (int),
    subject (lowercase), and nodeId. The node_id format encodes all four.
    """
    parts = node_id.split(".", 3)
    return {
        "board": parts[0].upper(),
        "grade": int(parts[1]),
        "subject": parts[2],
        "nodeId": node_id,
    }


def _student_curriculum(db: DbSession, student_id: uuid.UUID) -> dict[str, Any]:
    """Return the student's actual enrolled curriculum (board/grade/subject)."""
    student = db.get(StudentRow, student_id)
    if student is None:
        return {"board": "CBSE", "grade": 10, "subject": "maths"}
    subject = "maths"
    if student.curriculum_id and student.book_id:
        try:
            spec = load_curriculum(student.curriculum_id)
            book = next((b for b in spec.books if b.id == student.book_id), None)
            if book:
                subject = book.subject
        except Exception:
            pass
    return {
        "board": student.board.upper(),
        "grade": student.grade,
        "subject": subject,
    }


def _engine_options(place: dict[str, Any]) -> dict[str, Any]:
    """Story and source videos use the configured voice; prompt jobs use auto."""
    is_story = "story" in place
    is_source = "source" in place
    voice = settings.story_voice if (is_story or is_source) else "auto"
    theme = "dark" if is_story else "whiteboard"
    fps = 15 if is_story else 12
    return {
        "locale": "en-IN",
        "voice": voice,
        "fps": fps,
        "theme": theme,
    }


def _story_request(
    student_id: uuid.UUID, story: dict[str, Any], story_proof: str, curriculum: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """A job from a story this API wrote for this student: only one with a valid proof."""
    if not proof.verify(student_id, story, story_proof):
        raise HTTPException(status_code=422, detail="story proof is not valid")
    if len(json.dumps(story)) > STORY_MAX_CHARS:
        raise HTTPException(status_code=422, detail="story is too large")
    digest = hashlib.sha256(json.dumps(story, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"story:{digest}", {"curriculum": curriculum, "story": story}


def _source_request(
    student_id: uuid.UUID, source: SourceIn, source_proof: str, curriculum: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """A job from text this API wrote for this student: only a source with a valid proof."""
    text = source.model_dump()
    if not proof.verify(student_id, text, source_proof):
        raise HTTPException(status_code=422, detail="source proof is not valid")
    digest = hashlib.sha256(json.dumps(text, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"source:{digest}", {"curriculum": curriculum, "source": text}


def _prompt_request(prompt: str, curriculum: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """A job node id and the curriculum part of the engine request for a typed question.

    The student's actual enrolled curriculum is used so the engine searches the right
    knowledge base. A guest who chose CBSE grade 10 science gets science, not a hardcoded
    maths default. The question is cleaned and screened before queuing.
    """
    cleaned = clean_question(prompt, PROMPT_MAX_CHARS)
    if cleaned.empty or cleaned.too_long:
        raise HTTPException(status_code=422, detail="prompt must be 1 to 300 characters")
    if screen(cleaned.text, load_safety("en")).kind != "ok":
        raise HTTPException(status_code=422, detail="prompt not accepted")
    digest = hashlib.sha256(cleaned.text.encode("utf-8")).hexdigest()[:12]
    return f"prompt:{digest}", {"curriculum": curriculum, "prompt": cleaned.text}


# ── endpoints ────────────────────────────────────────────────────────────────


@router.get("/topics")
def list_topics(
    db: DbSession,
    actor: ActorDep,  # noqa: ARG001  # auth gate only
    node_prefix: str = "cbse.10.maths",
) -> dict[str, Any]:
    """List sections available as video-lesson topics, grouped under their chapter."""
    rows = db.execute(
        select(SectionRow, ChapterRow)
        .join(ChapterRow, SectionRow.chapter_id == ChapterRow.id)
        .where(SectionRow.id.like(f"{node_prefix}%"))
        .order_by(ChapterRow.position, SectionRow.order)
    ).all()
    topics = []
    for section, chapter in rows:
        topics.append(
            {
                "node_id": section.id,
                "chapter_title": (chapter.titles or {}).get("en") or chapter.chapter_key,
                "section_title": (section.titles or {}).get("en") or section.id,
                "page_start": section.page_start,
                "page_end": section.page_end,
            }
        )
    return {"topics": topics}


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

    curriculum = _student_curriculum(db, student_id)
    if body.story is not None:
        node_id, place = _story_request(student_id, body.story, body.story_proof or "", curriculum)
    elif body.source is not None:
        node_id, place = _source_request(
            student_id, body.source, body.source_proof or "", curriculum
        )
    elif body.prompt is not None:
        node_id, place = _prompt_request(body.prompt, curriculum)
    else:
        assert body.node_id is not None
        node_id, place = body.node_id, {"curriculum": _curriculum_from_node_id(body.node_id)}
    row = VideoJobRow(
        id=uuid.uuid4(),
        student_id=student_id,
        node_id=node_id,
        request_json={
            "requestId": str(uuid.uuid4()),
            "idempotencyKey": body.idempotency_key,
            **place,
            "options": _engine_options(place),
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


def _job_file(result_path: str, filename: str) -> Path:
    """Resolve a job output file.

    When ENGINE_JOBS_DIR is set (Docker), the worker stores a host absolute path that the
    container cannot reach. We extract just the UUID (the last path component) and look the
    file up under the mounted directory instead. On the host (ENGINE_JOBS_DIR empty) the
    stored path is used directly.
    """
    if settings.engine_jobs_dir:
        # result_path is a Windows absolute path stored by the host worker.
        # PureWindowsPath parses backslash-separated paths on any host OS.
        job_uuid = PureWindowsPath(result_path).name
        return Path(settings.engine_jobs_dir) / job_uuid / filename
    return Path(result_path) / filename


@router.get("/{job_id}/lesson.mp4")
def serve_lesson_mp4(job_id: uuid.UUID, db: DbSession, actor: ActorDep) -> FileResponse:
    """Stream the rendered MP4. Owner or admin; job must be in done status."""
    row = _job_or_404(db, job_id)
    _require_owner(actor, row)
    if row.status != "done" or not row.result_path:
        raise HTTPException(status_code=404, detail="video not ready")
    mp4 = _job_file(row.result_path, "lesson.mp4")
    if not mp4.exists():
        raise HTTPException(status_code=404, detail="video file not found")
    return FileResponse(str(mp4), media_type="video/mp4", filename="lesson.mp4")


@router.get("/{job_id}/sources.json")
def serve_sources_json(job_id: uuid.UUID, db: DbSession, actor: ActorDep) -> Any:
    """Return stripped sources.json. Internal 'path' keys are removed before sending."""
    row = _job_or_404(db, job_id)
    _require_owner(actor, row)
    if row.status != "done" or not row.result_path:
        raise HTTPException(status_code=404, detail="sources not ready")
    src = _job_file(row.result_path, "sources.json")
    if not src.exists():
        raise HTTPException(status_code=404, detail="sources file not found")
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail="sources unreadable") from exc
    return _strip_paths(data)


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
    if any(k in original.request_json for k in ("source", "story", "prompt")):
        keep = ("curriculum", "source", "story", "prompt")
        place = {k: original.request_json[k] for k in keep if k in original.request_json}
    else:
        place = {"curriculum": _curriculum_from_node_id(original.node_id)}
    row = VideoJobRow(
        id=uuid.uuid4(),
        student_id=original.student_id,
        node_id=original.node_id,
        request_json={
            "requestId": str(uuid.uuid4()),
            "idempotencyKey": new_idem,
            **place,
            "options": _engine_options(place),
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
