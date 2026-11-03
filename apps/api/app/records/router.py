"""POST/GET/DELETE /students/me/lesson-records: the learning card, kept in the account on request.

Signed-in learners only. A guest holds no consent, so a guest's card stays on the device; the
learner must hold tutoring consent. Nothing here is read by the tutor's policy.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select

from app.auth.authz import FORBIDDEN
from app.auth.consent import has_scope, is_guest
from app.auth.deps import ActorDep, DbSession
from app.auth.security import now_utc
from app.db.models import LessonRecordRow
from app.records.service import MAX_LESSONS, clean_record

router = APIRouter(tags=["records"])


class RecordsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[dict[str, Any]] = Field(max_length=MAX_LESSONS)


def _student(db: DbSession, actor: ActorDep) -> uuid.UUID:
    if not actor.is_student or actor.student_id is None:
        raise FORBIDDEN
    if is_guest(db, actor.student_id) or not has_scope(db, actor.student_id, "tutoring"):
        raise HTTPException(status_code=403, detail="sign in and agree to keep a record")
    return actor.student_id


def _utc(moment: datetime) -> datetime:
    """A database without time zones (the test one) returns naive times that were stored as UTC."""
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


@router.post("/students/me/lesson-records")
def save_records(body: RecordsIn, db: DbSession, actor: ActorDep) -> dict[str, int]:
    student_id = _student(db, actor)
    held = {
        (row.topic, _utc(row.taken_at))
        for row in db.scalars(
            select(LessonRecordRow).where(LessonRecordRow.student_id == student_id)
        )
    }
    saved = 0
    for raw in body.records:
        cleaned = clean_record(raw)
        if cleaned is None:
            continue
        topic, taken_at, items = cleaned
        taken_at = taken_at.astimezone(UTC)
        if (topic, taken_at) in held:
            continue
        db.add(
            LessonRecordRow(
                student_id=student_id,
                topic=topic,
                taken_at=taken_at,
                items=items,
                created_at=now_utc(),
            )
        )
        held.add((topic, taken_at))
        saved += 1
    db.flush()
    # keep the latest MAX_LESSONS only
    rows = list(
        db.scalars(
            select(LessonRecordRow)
            .where(LessonRecordRow.student_id == student_id)
            .order_by(LessonRecordRow.taken_at.desc())
        )
    )
    for old in rows[MAX_LESSONS:]:
        db.delete(old)
    db.commit()
    return {"saved": saved}


@router.get("/students/me/lesson-records")
def list_records(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    student_id = _student(db, actor)
    rows = db.scalars(
        select(LessonRecordRow)
        .where(LessonRecordRow.student_id == student_id)
        .order_by(LessonRecordRow.taken_at.desc())
        .limit(MAX_LESSONS)
    )
    return {
        "records": [
            {"topic": r.topic, "at": _utc(r.taken_at).isoformat(), "items": r.items} for r in rows
        ]
    }


@router.delete("/students/me/lesson-records")
def clear_records(db: DbSession, actor: ActorDep) -> dict[str, bool]:
    student_id = _student(db, actor)
    db.execute(delete(LessonRecordRow).where(LessonRecordRow.student_id == student_id))
    db.commit()
    return {"cleared": True}
