"""Access to your own data: everything recorded about an account's learners, as plain JSON.

Each table lists the columns it must never show. Anything not listed is shown, so a new column is
exported by default; the tests check that no secret, hash or token key appears.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.models import (
    CheckpointResultRow,
    ConsentRow,
    EventRow,
    LessonRecordRow,
    LlmCallRow,
    LoopBRecordRow,
    MasteryRow,
    MisconceptionHitRow,
    PaperEntryRow,
    ReportLogRow,
    ReviewCardRow,
    SafetyFlagRow,
    SessionRow,
    StudentRow,
    StudyParticipantRow,
    TeacherAlertRow,
    VideoJobRow,
)

# Columns that are credentials, or that reveal where files sit on the server.
STUDENT_HIDDEN = frozenset({"pin_hash", "pin_failed_attempts", "pin_locked_until", "family_code"})
VIDEO_HIDDEN = frozenset(
    {"result_path", "sources_json_path", "qa_json_path", "idempotency_key", "org_id"}
)
PARTICIPANT_HIDDEN = frozenset({"assignment_seed", "household_id"})


def _plain(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_plain(v) for v in value]
    return value


def row_dict(row: Any, hidden: frozenset[str] = frozenset()) -> dict[str, Any]:
    columns = inspect(type(row)).columns
    return {c.key: _plain(getattr(row, c.key)) for c in columns if c.key not in hidden}


def _rows(session: Session, model: Any, column: Any, ids: Any, order: Any = None) -> list[Any]:
    query = select(model).where(column.in_(ids))
    return list(session.scalars(query.order_by(order) if order is not None else query))


def learner_export(session: Session, student: StudentRow) -> dict[str, Any]:
    """One learner's records. Only reads rows keyed to this learner (never another family's)."""
    sid = [student.id]
    sessions = _rows(session, SessionRow, SessionRow.student_id, sid, SessionRow.started_at)
    session_ids = [s.id for s in sessions]
    events = _rows(session, EventRow, EventRow.session_id, session_ids, EventRow.created_at)
    llm = _rows(session, LlmCallRow, LlmCallRow.session_id, session_ids, LlmCallRow.created_at)
    participants = _rows(session, StudyParticipantRow, StudyParticipantRow.student_id, sid)
    participant_ids = [p.id for p in participants]
    results = list(
        session.scalars(
            select(CheckpointResultRow).where(
                (CheckpointResultRow.student_id == student.id)
                | CheckpointResultRow.participant_id.in_(participant_ids)
            )
        )
    )
    papers = _rows(session, PaperEntryRow, PaperEntryRow.participant_id, participant_ids)
    return {
        "learner": row_dict(student, STUDENT_HIDDEN),
        "sessions": [row_dict(r) for r in sessions],
        "answers": [row_dict(r) for r in events],
        "mastery": [row_dict(r) for r in _rows(session, MasteryRow, MasteryRow.student_id, sid)],
        "review_cards": [
            row_dict(r) for r in _rows(session, ReviewCardRow, ReviewCardRow.student_id, sid)
        ],
        "misconception_hits": [
            row_dict(r)
            for r in _rows(session, MisconceptionHitRow, MisconceptionHitRow.student_id, sid)
        ],
        "lesson_records": [
            row_dict(r)
            for r in _rows(
                session, LessonRecordRow, LessonRecordRow.student_id, sid, LessonRecordRow.taken_at
            )
        ],
        "learner_profile": [
            row_dict(r) for r in _rows(session, LoopBRecordRow, LoopBRecordRow.student_id, sid)
        ],
        "safety_flags": [
            row_dict(r) for r in _rows(session, SafetyFlagRow, SafetyFlagRow.student_id, sid)
        ],
        "teacher_alerts": [
            row_dict(r) for r in _rows(session, TeacherAlertRow, TeacherAlertRow.student_id, sid)
        ],
        "reports_sent": [
            row_dict(r) for r in _rows(session, ReportLogRow, ReportLogRow.student_id, sid)
        ],
        "video_jobs": [
            row_dict(r, VIDEO_HIDDEN)
            for r in _rows(
                session, VideoJobRow, VideoJobRow.student_id, sid, VideoJobRow.created_at
            )
        ],
        "ai_calls": [row_dict(r) for r in llm],
        "research": {
            "participants": [row_dict(r, PARTICIPANT_HIDDEN) for r in participants],
            "checkpoint_results": [row_dict(r) for r in results],
            "paper_entries": [row_dict(r) for r in papers],
        },
        "consents": [row_dict(r) for r in _rows(session, ConsentRow, ConsentRow.student_id, sid)],
    }
