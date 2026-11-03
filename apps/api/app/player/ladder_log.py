"""Rebuild ladder events from the persisted event log (used to verify and to recompute on sync)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import as_utc
from app.config import settings
from app.db.models import EventRow, SessionRow
from app.learner.bkt import BktParams
from app.learner.bktf_shadow import ShadowStep, replay_shadow
from app.learner.ladder import (
    KIND_ANSWER,
    KIND_HINT,
    KIND_LESSON,
    KIND_TEST_OUT,
    LadderEvent,
    SkillLadder,
    compute,
)
from app.learner.types import LearnerEvent
from app.orchestrator.types import CatalogItem
from app.verifier.check import verify_response


def _confidence(event: EventRow) -> str:
    """The learner's own "sure" or "unsure", only when the deployment uses it."""
    if not settings.confidence_rules or not isinstance(event.payload, dict):
        return ""
    value = event.payload.get("confidence")
    return value if value in ("sure", "unsure") else ""


def ladder_events_from_rows(
    rows: Sequence[tuple[EventRow, str]], catalog: Mapping[str, CatalogItem]
) -> list[LadderEvent]:
    """`rows` are (event, session type) in log order. Only practice sessions feed the ladder."""
    out: list[LadderEvent] = []
    for event, session_type in rows:
        if session_type == "test_out":
            if event.event_type == "test_out_passed":
                out.append(
                    LadderEvent(
                        event_id=str(event.client_event_id or event.id),
                        skill_id=str((event.payload or {}).get("skill_id") or ""),
                        kind=KIND_TEST_OUT,
                        at=as_utc(event.created_at),
                    )
                )
            continue
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
                latency_ms=event.latency_ms,
                confidence=_confidence(event),
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
        elif event.event_type in {"request_help", "request_hint"}:
            out.append(make(KIND_HINT))
        elif event.event_type == "continue" and event.state_before == "worked_example":
            out.append(make(KIND_LESSON, keep_item=False))
    return out


def learner_events_from_ladder(events: Sequence[LadderEvent]) -> list[LearnerEvent]:
    """Attempts and hint requests as timestamped learner events, which the BKT-F replay reads."""
    return [
        LearnerEvent(
            item_id=event.item_id,
            skill_id=event.skill_id,
            event_type=event.kind,
            correct=event.correct,
            pool=event.pool,
            latency_ms=event.latency_ms,
            is_warmup=event.pool == "warmup",
            at=event.at,
        )
        for event in events
        if event.kind in {KIND_ANSWER, KIND_HINT}
    ]


def shadow_steps_for_student(
    session: Session,
    student_id: uuid.UUID,
    catalog: tuple[CatalogItem, ...],
    params_by_skill: Mapping[str, BktParams],
) -> list[ShadowStep]:
    """Replay one student's logged practice through the live model and BKT-F, side by side.

    Read-only. The authored `min_plausible_ms` of each item is its rapid-guess threshold, so a fast
    answer is judged against what that item can plausibly take, not one number for every item.
    """
    rows = session.execute(
        select(EventRow, SessionRow.type)
        .join(SessionRow, EventRow.session_id == SessionRow.id)
        .where(SessionRow.student_id == student_id)
        .order_by(EventRow.created_at, EventRow.id)
    ).all()
    ladder_events = ladder_events_from_rows(
        [(event, session_type) for event, session_type in rows],
        {item.id: item for item in catalog},
    )
    thresholds = {
        item.id: item.min_plausible_ms for item in catalog if item.min_plausible_ms is not None
    }
    return replay_shadow(
        learner_events_from_ladder(ladder_events),
        dict(params_by_skill),
        rapid_guess_ms_by_item=thresholds,
    )


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
