"""Offline sync: replay a session the browser played without a network.

The browser sends the events it recorded. The server does not trust any verdict in them: it replays
the whole session through the same teaching policy the online player uses, from the learner state
it holds, against the same offline catalog the pack was cut from. Every answer is re-marked here,
a client's `correct` is only stored for audit, and an illegal sequence (a reveal before two hints,
a choice outside the picker) comes back as a rejected event with its guardrail flag and changes
nothing. Mastery, ladder and review cards are then the result of that replay, so the state the
browser reached by running the same code offline and the state stored here agree exactly.

Idempotent on `client_event_id`: sending a batch twice, or a longer batch that starts with events
already stored, applies each event once.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.actor import Actor
from app.auth.authz import require, student_or_404
from app.auth.consent import has_scope
from app.auth.security import as_utc, now_utc
from app.db.models import EventRow, SessionRow, StudentRow
from app.offline.pack import build_pack, canonical, learner_json, pack_catalog
from app.orchestrator.policy import policy
from app.orchestrator.types import Event
from app.player.lesson_events import LESSON_EVENTS
from app.player.runtime import (
    _build_state,
    _overlay_skills,
    _persist_state,
    persist_learner,
    sync_alerts,
)

MAX_EVENTS = 500
CLOCK_SKEW = timedelta(minutes=5)
POLICY_EVENTS = frozenset(
    {
        "answer",
        "request_help",
        "request_hint",
        "stuck_choice",
        "stuck_step",
        "show_solution",
        "break_choice",
        "continue",
        "predict_response",
        "explain_back",
        "idle_nudge",
        "resume",
    }
)


class ClientAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    item_id: str | None = None


class SyncEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_event_id: uuid.UUID
    event_type: str
    item_id: str | None = None
    at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    client_action: ClientAction | None = None  # what the browser showed next, for the audit


class SyncIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_session_id: uuid.UUID
    started_at: datetime
    pack_hash: str | None = None
    events: list[SyncEventIn] = Field(max_length=MAX_EVENTS)


def offline_session_id(student_id: uuid.UUID, client_session_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(student_id, str(client_session_id))


def state_hash(learner: dict[str, Any]) -> str:
    """The BKT and ladder state, canonically written: what must match the browser exactly."""
    core = {"mastery": learner["mastery"], "ladders": learner["ladders"]}
    return hashlib.sha256(canonical(core).encode("utf-8")).hexdigest()


def _event_for(body: SyncEventIn) -> Event:
    payload = body.payload
    response = str(payload["response"]) if payload.get("response") is not None else None
    if body.event_type in {"stuck_choice", "break_choice"}:
        response = str(payload.get("choice") or "")
    elif body.event_type == "stuck_step":
        response = str(payload.get("index")) if payload.get("index") is not None else ""
    return Event(
        type=body.event_type,
        response=response,
        client_correct=payload.get("correct"),
        latency_ms=payload.get("latency_ms"),
        item_id=body.item_id,
        idle_ms=payload.get("idle_ms"),
        text=payload.get("text"),
        event_id=str(body.client_event_id),
    )


def _bounded(at: datetime, previous: datetime, server_now: datetime) -> tuple[datetime, bool]:
    """A client timestamp, never earlier than the one before and never in the future."""
    when = as_utc(at)
    clamped = False
    if when > server_now + CLOCK_SKEW:
        when, clamped = server_now, True
    if when < previous:
        when, clamped = previous, True
    return when, clamped


def sync_offline_session(db: Session, actor: Actor, body: SyncIn) -> dict[str, Any]:
    require(actor.is_student and actor.student_id is not None)
    student: StudentRow = student_or_404(db, actor.student_id)  # type: ignore[arg-type]
    if not has_scope(db, student.id, "tutoring"):
        raise HTTPException(status_code=403, detail="tutoring consent required")
    server_now = now_utc()
    skills = _overlay_skills(db, student)
    pack = build_pack(db, student)
    session_id = offline_session_id(student.id, body.client_session_id)
    row = db.get(SessionRow, session_id)
    fresh = row is None
    started = _bounded(body.started_at, as_utc(body.started_at), server_now)[0]
    if row is None:
        row = SessionRow(
            id=session_id,
            student_id=student.id,
            started_at=started,
            type="practice",
            last_active_at=started,
            plan={"offline": True, "client_session_id": str(body.client_session_id)},
        )
        db.add(row)
        db.flush()
    state, learner = _build_state(db, row, student)
    state.catalog = pack_catalog(db, skills)
    last_seen = (row.plan or {}).get("last_event_at")
    previous = started if fresh or not last_seen else as_utc(datetime.fromisoformat(last_seen))
    results: list[dict[str, Any]] = []
    if fresh:
        state.now = started
        state.last_active_at = started
        policy(learner, state, None)
        previous = started
    for incoming in body.events:
        seen = db.scalar(
            select(EventRow).where(EventRow.client_event_id == incoming.client_event_id)
        )
        if seen is not None:
            same = seen.session_id == row.id
            results.append(
                {
                    "client_event_id": str(incoming.client_event_id),
                    "status": "duplicate" if same else "rejected",
                    "guardrail_flag": None if same else "event_id_conflict",
                }
            )
            continue
        when, clamped = _bounded(incoming.at, previous, server_now)
        flags = ["clock_skew"] if clamped else []
        if incoming.event_type in LESSON_EVENTS or incoming.event_type not in POLICY_EVENTS:
            flags.append("unsupported_offline_event")
            _store(db, row, incoming, when, None, None, flags=flags, applied=False)
            results.append(
                {
                    "client_event_id": str(incoming.client_event_id),
                    "status": "rejected",
                    "guardrail_flag": "unsupported_offline_event",
                }
            )
            continue
        state.now = when
        previous = when
        action = policy(learner, state, _event_for(incoming))
        if action.rejected:
            flags.append(str(action.guardrail_flag))
        _store(
            db,
            row,
            incoming,
            when,
            action,
            state.last_correct,
            flags=flags,
            applied=True,
            diagnosis=state.last_diagnosis,
        )
        diverged = None
        if incoming.client_action is not None:
            diverged = (incoming.client_action.type, incoming.client_action.item_id) != (
                action.type,
                action.item_id,
            )
        results.append(
            {
                "client_event_id": str(incoming.client_event_id),
                "status": "rejected" if action.rejected else "applied",
                "correct": state.last_correct if incoming.event_type == "answer" else None,
                "guardrail_flag": action.guardrail_flag,
                "action_type": action.type,
                "item_id": action.item_id,
                "rule_id": action.rule_id,
                "diverged": diverged,
            }
        )
    db.flush()  # the alert checks read the events just added
    persist_learner(db, student.id, learner)
    sync_alerts(db, student, state, learner)
    _persist_state(row, state)
    row.plan = {**row.plan, "last_event_at": previous.isoformat()}
    db.flush()
    snapshot = learner_json(learner)
    return {
        "session_id": str(row.id),
        "pack_hash_ok": body.pack_hash is None or body.pack_hash == pack["hash"],
        "server_pack_hash": pack["hash"],
        "applied": sum(r["status"] == "applied" for r in results),
        "duplicates": sum(r["status"] == "duplicate" for r in results),
        "rejected": sum(r["status"] == "rejected" for r in results),
        "results": results,
        "state": snapshot,
        "state_hash": state_hash(snapshot),
        "ended": state.phase == "ended",
        "ended_reason": state.ended_reason,
    }


def _store(
    db: Session,
    row: SessionRow,
    incoming: SyncEventIn,
    when: datetime,
    action: Any,
    correct: bool | None,
    *,
    flags: list[str],
    applied: bool,
    diagnosis: dict[str, Any] | None = None,
) -> None:
    payload = {**incoming.payload, "offline": True, "applied": applied}
    if flags:
        payload["flags"] = flags
    if diagnosis:
        payload["diagnosis"] = diagnosis  # the same record the online path keeps
    if "correct" in payload:
        payload["client_correct"] = payload.pop("correct")  # kept for audit, never trusted
    db.add(
        EventRow(
            id=uuid.uuid4(),
            client_event_id=incoming.client_event_id,
            session_id=row.id,
            item_id=incoming.item_id or (action.item_id if action else None),
            event_type="request_help"
            if incoming.event_type == "request_hint"
            else incoming.event_type,
            payload=payload,
            correct=correct if incoming.event_type == "answer" else None,
            hint_level=action.hint_level if action else None,
            latency_ms=incoming.payload.get("latency_ms"),
            created_at=when,
            state_before=action.state_before if action else None,
            state_after=action.state_after if action else None,
            rule_id=action.rule_id if action else None,
        )
    )
