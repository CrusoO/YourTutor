"""GET/POST /staff/review/...: the staff-only content review screen's API.

Only a signed-in teacher or admin may call it (a student, guest or parent gets 403, no token 401).
When `REVIEWER_ALLOWLIST` is set the account's label must be on it (see `reviewer_allowed`).
With `REVIEWER_DESK_ENABLED` on, an invited `reviewer` account may call it too (and nothing else),
cards are blind until the reviewer has decided, every decision is kept as history, and an admin
can invite and suspend reviewers and read the pay export.
It never returns student data and never writes repo files: decisions go to `content_reviews`, and
`python -m app.content apply-reviews` writes the YAML.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.auth.actor import Actor
from app.auth.authz import FORBIDDEN
from app.auth.deps import ActorDep, DbSession
from app.auth.security import now_utc
from app.config import settings
from app.content.signatures import item_content_hash
from app.content_review import service
from app.registries.paths import content_root

router = APIRouter(prefix="/staff/review", tags=["staff-review"])

Status = Literal["pending", "ready", "flagged", "all"]


class FixNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_index: int = Field(ge=0, le=service.CHECK_COUNT - 1)
    text: str = Field(max_length=2000)


class DecisionIn(BaseModel):
    """`skip`, `withdraw` and every field after `note` are for the reviewer desk
    (REVIEWER_DESK_ENABLED); with the desk off, sending any of them is a 422."""

    model_config = ConfigDict(extra="forbid")

    content_hash: str = Field(min_length=1, max_length=64)
    decision: Literal["approve", "reject", "fix", "skip", "withdraw"]
    note: str | None = Field(default=None, max_length=2000)
    severity: Literal["blocker", "must_fix", "nice_to_fix"] | None = None
    reason_code: Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"] | None = None
    checks: list[bool | None] | None = Field(
        default=None, min_length=service.CHECK_COUNT, max_length=service.CHECK_COUNT
    )
    fix_notes: list[FixNote] | None = Field(default=None, max_length=service.CHECK_COUNT)
    active_seconds: int | None = Field(default=None, ge=0, le=service.MAX_ACTIVE_SECONDS)

    def desk_fields_used(self) -> bool:
        extras = (self.severity, self.reason_code, self.checks, self.fix_notes, self.active_seconds)
        return self.decision in ("skip", "withdraw") or any(v is not None for v in extras)


class InviteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _reviewer(actor: Actor) -> tuple[uuid.UUID, str]:
    invited = actor.is_reviewer and settings.reviewer_desk_enabled
    if not (actor.is_teacher or actor.is_admin or invited) or actor.user_id is None:
        raise FORBIDDEN
    label = actor.email or str(actor.user_id)
    # an invited reviewer was let in by an admin, so the allowlist (for staff labels) is not asked
    if not invited and not service.reviewer_allowed(label):
        raise FORBIDDEN
    return actor.user_id, label


def _desk_admin(actor: Actor) -> uuid.UUID:
    """Admin-only desk routes. With the desk off they answer like an unknown route."""
    if not settings.reviewer_desk_enabled:
        raise HTTPException(status_code=404, detail="not found")
    if not actor.is_admin or actor.user_id is None:
        raise FORBIDDEN
    return actor.user_id


@router.get("/items")
def list_items(
    db: DbSession,
    actor: ActorDep,
    status: Status = "pending",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Draft items, in id order, one page at a time (each card runs the solver).

    pending: draft, not yet two approvals, nothing blocking. ready: two approvals, waiting for
    `apply-reviews`. flagged: a reject or fix stands. all: every draft. With the reviewer desk on,
    an item you have not decided yet always counts as pending (so a filter cannot show how others
    voted)."""
    me, _ = _reviewer(actor)
    root = content_root()
    items, labels = service.load_items(root)
    drafts = [item for item in items if service.is_draft(item)]
    pairs = {item.id: (item.id, item_content_hash(item)) for item in drafts}
    reviews = service.reviews_for_items(db, list(pairs.values()))
    chosen = []
    for item in drafts:
        state = service.list_state(reviews[pairs[item.id]], me)
        if status in ("all", state):
            chosen.append(item)
    page = chosen[offset : offset + limit]
    return {
        "total": len(chosen),
        "offset": offset,
        "items": [service.card(db, root, item, labels, me) for item in page],
    }


@router.post("/items/{item_id}/decision")
def decide(item_id: str, body: DecisionIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    me, label = _reviewer(actor)
    root = content_root()
    items, labels = service.load_items(root)
    item = next((i for i in items if i.id == item_id), None)
    if item is None or not service.is_draft(item):
        raise HTTPException(status_code=404, detail="item not found")
    if body.content_hash != item_content_hash(item):
        raise HTTPException(status_code=409, detail="the item changed; reload and review again")
    note = (body.note or "").strip() or None
    if body.decision == "withdraw" and settings.reviewer_desk_enabled:
        rows = service.reviews_for(db, item_id, body.content_hash)
        if me not in service.standing(rows):
            raise HTTPException(status_code=409, detail="you have no decision to withdraw")
    desk = settings.reviewer_desk_enabled
    if not desk and body.desk_fields_used():
        raise HTTPException(status_code=422, detail="the reviewer desk is not switched on")
    extra: dict[str, Any] = {}
    if desk:
        written = [(n.question_index, n.text.strip()) for n in body.fix_notes or []]
        errors = service.check_desk_decision(
            decision=body.decision,
            severity=body.severity,
            reason_code=body.reason_code,
            checks=body.checks,
            fix_notes=written,
            note=note,
        )
        if errors:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "invalid_decision",
                    "errors": [{"field": e.field, "message": e.message} for e in errors],
                },
            )
        extra = {
            "severity": body.severity,
            "reason_code": body.reason_code,
            "checks": body.checks,
            "fix_notes": [{"question_index": i, "text": t} for i, t in written] or None,
            "active_seconds": body.active_seconds,
        }
    elif body.decision in ("reject", "fix") and note is None:
        raise HTTPException(status_code=422, detail="a note is required to reject or ask for a fix")
    service.record_decision(
        db,
        item_id=item_id,
        content_hash=body.content_hash,
        reviewer_id=me,
        reviewer_label=label,
        decision=body.decision,
        note=note,
        now=now_utc(),
        **extra,
    )
    return service.card(db, root, item, labels, me)


def _reviewer_out(user: Any) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "suspended": user.suspended_at is not None,
    }


@router.post("/reviewers")
def invite_reviewer(body: InviteIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Admin only: invite an outside reviewer by email. They then sign in with the usual email
    code. Never turns an existing teacher, parent or admin account into a reviewer."""
    _desk_admin(actor)
    user = service.invite_reviewer(db, body.email, now_utc())
    if user.role != "reviewer":
        raise HTTPException(status_code=409, detail="that email already belongs to another account")
    return _reviewer_out(user)


@router.post("/reviewers/{reviewer_id}/suspend")
def suspend_reviewer(reviewer_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    _desk_admin(actor)
    user = service.set_reviewer_suspended(db, reviewer_id, True, now_utc())
    if user is None:
        raise HTTPException(status_code=404, detail="reviewer not found")
    return _reviewer_out(user)


@router.post("/reviewers/{reviewer_id}/reinstate")
def reinstate_reviewer(reviewer_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    _desk_admin(actor)
    user = service.set_reviewer_suspended(db, reviewer_id, False, now_utc())
    if user is None:
        raise HTTPException(status_code=404, detail="reviewer not found")
    return _reviewer_out(user)


@router.get("/reviewers")
def list_reviewers(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Admin only: every invited reviewer with suspended, invited at, last decision time and
    decision count. Account and activity facts only; no learner data, no votes."""
    _desk_admin(actor)
    return {"reviewers": service.list_reviewers(db)}


@router.get("/me/today")
def my_time_today(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """The caller's active review seconds today (UTC) and the daily cap, for the "time today"
    display. Desk on only."""
    if not settings.reviewer_desk_enabled:
        raise HTTPException(status_code=404, detail="not found")
    me, _ = _reviewer(actor)
    return {
        "active_seconds_today": service.seconds_today(db, me, now_utc()),
        "daily_cap_seconds": settings.reviewer_daily_cap_seconds,
    }


@router.get("/export")
def pay_export(
    db: DbSession,
    actor: ActorDep,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
) -> dict[str, Any]:
    """Admin only, read-only: per reviewer, decisions by type and total active seconds between two
    dates (both included, UTC). Ids and pseudonymous labels only; no email, no learner data."""
    _desk_admin(actor)
    if end < start:
        raise HTTPException(status_code=422, detail="`to` is before `from`")
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "reviewers": service.reviewer_export(db, start, end),
    }
