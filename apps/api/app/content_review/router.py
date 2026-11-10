"""GET/POST /staff/review/...: the staff-only content review screen's API.

Only a signed-in teacher or admin may call it (a student, guest or parent gets 403, no token 401).
When `REVIEWER_ALLOWLIST` is set the account's label must be on it (see `reviewer_allowed`).
It never returns student data and never writes repo files: decisions go to `content_reviews`, and
`python -m app.content apply-reviews` writes the YAML.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.auth.actor import Actor
from app.auth.authz import FORBIDDEN
from app.auth.deps import ActorDep, DbSession
from app.auth.security import now_utc
from app.content.signatures import item_content_hash
from app.content_review import service
from app.registries.paths import content_root

router = APIRouter(prefix="/staff/review", tags=["staff-review"])

Status = Literal["pending", "ready", "flagged", "all"]


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_hash: str = Field(min_length=1, max_length=64)
    decision: Literal["approve", "reject", "fix"]
    note: str | None = Field(default=None, max_length=2000)


def _reviewer(actor: Actor) -> tuple[uuid.UUID, str]:
    if not (actor.is_teacher or actor.is_admin) or actor.user_id is None:
        raise FORBIDDEN
    label = actor.email or str(actor.user_id)
    if not service.reviewer_allowed(label):
        raise FORBIDDEN
    return actor.user_id, label


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
    `apply-reviews`. flagged: a reject or fix stands. all: every draft."""
    me, _ = _reviewer(actor)
    root = content_root()
    items, labels = service.load_items(root)
    chosen = []
    for item in items:
        if not service.is_draft(item):
            continue
        counted = service.tally(service.reviews_for(db, item.id, item_content_hash(item)))
        state = "flagged" if counted.blocked else "ready" if counted.ready else "pending"
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
    if body.decision in ("reject", "fix") and note is None:
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
    )
    return service.card(db, root, item, labels, me)
