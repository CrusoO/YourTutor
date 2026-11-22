"""Mistake notebook routes (slice 1): what is due, record a return, a short summary.

Off unless MISTAKE_NOTEBOOK_ENABLED. Same gates as the practice routes: a signed-in student who is
not a guest and holds the tutoring consent, and not paused. Ids, labels and counts only; no learner
text comes in or goes out, and no score is shown as a probability.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.auth.deps import ActorDep, DbSession
from app.auth.security import now_utc
from app.config import settings
from app.learner import notebook_store as store
from app.safety import is_paused

router = APIRouter(prefix="/notebook", tags=["notebook"])


class ResultBody(BaseModel):
    """The verifier's outcome for the return. Nothing else is accepted: no answer text."""

    model_config = ConfigDict(extra="forbid")
    outcome: Literal["right", "wrong"]


def refuse(status: int, code: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code})


def _student(db: DbSession, actor: ActorDep) -> uuid.UUID:
    if not settings.mistake_notebook_enabled:
        raise refuse(404, "notebook_disabled")
    if not actor.is_student or actor.student_id is None:
        raise refuse(403, "notebook_students_only")
    if not store.may_use(db, actor.student_id):
        raise refuse(403, "notebook_consent_required")
    if is_paused(db, actor.student_id):
        raise refuse(403, "notebook_paused")
    return actor.student_id


@router.get("/due")
def due(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    sid = _student(db, actor)
    return {"entries": store.due_entries(db, sid, now_utc())}


@router.get("")
def overview(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    sid = _student(db, actor)
    return store.summary(db, sid, now_utc())


@router.post("/{entry_id}/result")
def result(entry_id: uuid.UUID, body: ResultBody, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    sid = _student(db, actor)
    try:
        return store.record_result(db, sid, entry_id, body.outcome, now_utc())
    except store.NotFound:
        raise refuse(404, "notebook_entry_not_found") from None
    except store.NotDue:
        raise refuse(409, "notebook_entry_not_due") from None
