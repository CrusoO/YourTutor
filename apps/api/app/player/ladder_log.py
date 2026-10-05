"""Rebuild ladder events from the persisted event log (used to verify and to recompute on sync)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import as_utc
from app.db.models import EventRow, SessionRow
from app.learner.bkt import BktParams
from app.learner.ladder import (
    KIND_ANSWER,
    KIND_HINT,
    KIND_LESSON,
    LadderEvent,
    SkillLadder,
    compute,
)
from app.orchestrator.types import CatalogItem
from app.verifier.check import verify_response


def ladder_events_from_rows(
    rows: Sequence[tuple[EventRow, str]], catalog: Mapping[str, CatalogItem]
) -> list[LadderEvent]:
    """`rows` are (event, session type) in log order. Only practice sessions feed the ladder."""
    out: list[LadderEvent] = []
    for event, session_type in rows:
        if session_type != "practice" or not event.item_id:
            continue
        found = catalog.get(event.item_id)
        if found is None:
            continue
        item: CatalogItem = found

        def make(kind: str, *, correct: bool | None = None, keep_item: bool = True) -> LadderEvent:
            return LadderEvent(
                event_id=str(event.client_event_id or event.id),
                skill_id=item.primary_skill,
                kind=kind,
                at=as_utc(event.created_at),
                item_id=item.id if keep_item else "",
                correct=correct,
                pool="warmup" if event.state_before == "warmup" else "practice",
                role=item.role,
                structure=item.structure,
            )

        if event.event_type == "answer":
            correct = event.correct
            if correct is None:
                response = str((event.payload or {}).get("response") or "")
                correct = verify_response(
                    response,
                    answer_sympy=item.answer_sympy,
                    accept=list(item.accept),
                    item_type=item.type,
                    verify=item.verify,
                    options=list(item.options),
                )
            out.append(make(KIND_ANSWER, correct=correct))
        elif event.event_type == "request_hint":
            out.append(make(KIND_HINT))
        elif event.event_type == "continue" and event.state_before == "worked_example":
            out.append(make(KIND_LESSON, keep_item=False))
    return out


def recompute_ladders(
    session: Session,
    student_id: uuid.UUID,
    catalog: tuple[CatalogItem, ...],
    params_by_skill: Mapping[str, BktParams],
    *,
    now: datetime,
) -> dict[str, SkillLadder]:
    rows = session.execute(
        select(EventRow, SessionRow.type)
        .join(SessionRow, EventRow.session_id == SessionRow.id)
        .where(SessionRow.student_id == student_id)
        .order_by(EventRow.created_at, EventRow.id)
    ).all()
    events = ladder_events_from_rows(
        [(event, session_type) for event, session_type in rows],
        {item.id: item for item in catalog},
    )
    return compute(events, now, params_by_skill)
