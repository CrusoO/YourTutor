"""Group lessons: share one checked lesson by link, collect anonymous results, show the group.

An organiser (a teacher or manager) publishes a lesson they generated and reviewed. Anyone with
the link can open it; no model is called for the participants, so it is instant and costs nothing
per person. A participant may send back how they did, once, with no name. Results are only
accepted while learners are treated as adults (a stand-in for an age gate that production
refuses to run without).
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.auth.authz import FORBIDDEN
from app.auth.deps import ActorDep, DbSession
from app.auth.security import now_utc
from app.config import adults_assumed, settings
from app.db.models import GroupLessonRow, GroupResultRow
from app.explain.service_lesson import clean_published_blocks
from app.groups.service import (
    MAX_ITEMS,
    accept_items,
    new_code,
    participant_key,
    summarise,
)
from app.llm.rules import default_rules

router = APIRouter(prefix="/groups", tags=["groups"])

CODE = re.compile(r"^[A-Za-z0-9_-]{6,16}$")


class GroupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=2, max_length=300)
    language: Literal["en", "hi"] = "en"
    # The lesson as the organiser saw it and approved it; cleaned again here, never trusted as sent.
    blocks: list[dict[str, Any]] = Field(max_length=14)


class ResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(max_length=300)
    kind: Literal["predict", "check"]
    right: bool
    confidence: Literal["sure", "unsure"] | None = None
    idea: str | None = Field(default=None, max_length=80)


class ResultsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ResultItem] = Field(min_length=1, max_length=MAX_ITEMS)


def _organiser(actor: ActorDep) -> uuid.UUID:
    """Only a teacher or an admin publishes a group lesson."""
    if not (actor.is_teacher or actor.is_admin) or actor.user_id is None:
        raise FORBIDDEN
    return actor.user_id


def _group(db: DbSession, code: str) -> GroupLessonRow:
    row = (
        db.scalar(select(GroupLessonRow).where(GroupLessonRow.code == code))
        if CODE.match(code)
        else None
    )
    if row is None:
        raise HTTPException(status_code=404, detail="group_not_found")
    return row


def _own(db: DbSession, actor: ActorDep, code: str) -> GroupLessonRow:
    group = _group(db, code)
    if not (actor.is_admin or (actor.is_teacher and actor.user_id == group.owner_id)):
        raise FORBIDDEN
    return group


def _path(group: GroupLessonRow) -> str:
    return f"/brownie-chat?group={group.code}"


@router.post("")
def create_group(body: GroupIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    owner = _organiser(actor)
    blocks = clean_published_blocks(body.blocks)
    if blocks is None:
        raise HTTPException(status_code=422, detail="lesson_not_usable")
    lowered = json.dumps(blocks, ensure_ascii=False).lower()
    if any(term in lowered for term in default_rules().blocked_terms):
        raise HTTPException(status_code=422, detail="lesson_not_allowed")
    for _ in range(5):
        code = new_code()
        if db.scalar(select(GroupLessonRow.id).where(GroupLessonRow.code == code)) is None:
            break
    else:  # pragma: no cover - a collision five times running is not going to happen
        raise HTTPException(status_code=503, detail="try_again")
    group = GroupLessonRow(
        id=uuid.uuid4(),
        owner_id=owner,
        code=code,
        prompt=" ".join(body.prompt.split()),
        language=body.language,
        blocks=blocks,
        created_at=now_utc(),
    )
    db.add(group)
    db.flush()
    return {"code": group.code, "path": _path(group)}


@router.get("")
def my_groups(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    owner = _organiser(actor)
    rows = db.scalars(
        select(GroupLessonRow)
        .where(GroupLessonRow.owner_id == owner)
        .order_by(GroupLessonRow.created_at.desc())
        .limit(100)
    ).all()
    counts = dict(
        db.execute(
            select(GroupResultRow.group_id, func.count())
            .where(GroupResultRow.group_id.in_([r.id for r in rows]))
            .group_by(GroupResultRow.group_id)
        ).all()
    )
    return {
        "groups": [
            {
                "code": r.code,
                "path": _path(r),
                "prompt": r.prompt,
                "created_at": r.created_at.isoformat(),
                "closed": r.closed_at is not None,
                "participants": int(counts.get(r.id, 0)),
            }
            for r in rows
        ]
    }


@router.get("/{code}")
def open_group(code: str, db: DbSession) -> dict[str, Any]:
    """The shared lesson itself. Public on purpose: the code is the key and it opens from a link."""
    group = _group(db, code)
    return {
        "code": group.code,
        "prompt": group.prompt,
        "language": group.language,
        "blocks": group.blocks,
        "closed": group.closed_at is not None,
        # while learners count as adults results can be sent; otherwise the page offers no button
        "results_open": adults_assumed() and group.closed_at is None,
    }


@router.post("/{code}/results")
def send_results(code: str, body: ResultsIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    if not actor.is_student or actor.student_id is None:
        raise FORBIDDEN
    if not adults_assumed():
        raise HTTPException(status_code=403, detail="age_gate_required")
    group = _group(db, code)
    if group.closed_at is not None:
        raise HTTPException(status_code=409, detail="group_closed")
    items = accept_items(group.blocks, [i.model_dump() for i in body.items])
    if not items:
        raise HTTPException(status_code=422, detail="nothing_to_record")
    key = participant_key(settings.token_pepper, group.id, actor.student_id)
    row = db.scalar(
        select(GroupResultRow).where(
            GroupResultRow.group_id == group.id, GroupResultRow.participant == key
        )
    )
    if row is None:
        db.add(
            GroupResultRow(
                id=uuid.uuid4(),
                group_id=group.id,
                participant=key,
                submitted_at=now_utc(),
                items=items,
            )
        )
    else:  # sending again replaces the earlier answer: one voice each
        row.items = items
        row.submitted_at = now_utc()
    return {"accepted": len(items)}


@router.get("/{code}/summary")
def group_summary(code: str, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    group = _own(db, actor, code)
    results = [
        list(r.items)
        for r in db.scalars(select(GroupResultRow).where(GroupResultRow.group_id == group.id))
    ]
    return {"code": group.code, "prompt": group.prompt, **summarise(group.blocks, results)}


@router.post("/{code}/close")
def close_group(code: str, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    group = _own(db, actor, code)
    if group.closed_at is None:
        group.closed_at = now_utc()
    return {"closed": True}
