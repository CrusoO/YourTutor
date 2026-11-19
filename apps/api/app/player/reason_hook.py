"""Glue between the player and the reason model: read the open episode, write the next one.

The model itself is pure (`app.learner.reason`). This module does the two things that touch the
database: it finds the latest episode in the session's own events, and it builds the `reason`
payload stored on the event being written. Off unless REASON_FIRST_ENABLED; every function then
returns exactly what the player produced before.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import EventRow
from app.learner.reason import assess
from app.learner.reason.episode import (
    Episode,
    after_answer,
    after_correction,
    after_move,
    public,
)
from app.learner.reason.moves import FAMILIES
from app.learner.types import LearnerState
from app.orchestrator.types import CatalogItem, SessionState
from app.player.signals import CORRECTION_EVENT, clean_correction

MOVE_EVENT = "move_chosen"
SIDE_EVENTS = frozenset({CORRECTION_EVENT, MOVE_EVENT})
LOOKBACK = 40  # events scanned for the latest episode


def enabled() -> bool:
    return settings.reason_first_enabled


def latest_episode(session: Session, session_id: uuid.UUID) -> Episode | None:
    rows: ScalarResult[Any] = session.scalars(
        select(EventRow.payload)
        .where(EventRow.session_id == session_id)
        .order_by(EventRow.created_at.desc())
        .limit(LOOKBACK)
    )
    for payload in rows:
        if isinstance(payload, dict):
            found = Episode.from_payload(payload.get("reason"))
            if found is not None:
                return found
    return None


def clean_move(payload: dict[str, Any]) -> dict[str, Any]:
    family = payload.get("family")
    return {"family": family} if isinstance(family, str) and family in FAMILIES else {}


def side_event_payload(
    session: Session, session_id: uuid.UUID, event_type: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """The stored payload for a "that's not why" or a "chose this kind of help" event."""
    cleaned = clean_correction(payload) if event_type == CORRECTION_EVENT else clean_move(payload)
    if not enabled():
        return cleaned
    episode = latest_episode(session, session_id)
    if episode is None:
        return cleaned
    if event_type == CORRECTION_EVENT and "diagnosed" in cleaned:
        episode = after_correction(episode, cleaned["diagnosed"])
    elif event_type == MOVE_EVENT and "family" in cleaned:
        episode = after_move(episode, cleaned["family"])
    return {**cleaned, "reason": episode.to_payload()}


def on_answer(
    session: Session,
    session_id: uuid.UUID,
    state: SessionState,
    learner: LearnerState,
    item: CatalogItem | None,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None] | None:
    """The `reason` payload for an answer event and what to show the learner, or None when off.

    "Hinted" here means a mistake was already open on this skill, so the answer came after help.
    """
    if not enabled() or item is None or state.session_type != "practice":
        return None
    if state.last_correct is None:
        return None
    skill = item.primary_skill
    prev = latest_episode(session, session_id)
    open_mistake = prev is not None and prev.skill == skill and prev.posterior is not None
    confidence = payload.get("confidence")
    sure = confidence if confidence in ("sure", "unsure") else None
    found = None
    if not state.last_correct:
        prior = prev.posterior if open_mistake and prev is not None else None
        found = assess(
            item, str(payload.get("response") or ""), learner, state, prior=prior, confidence=sure
        )
    episode, effect = after_answer(
        prev,
        skill,
        correct=bool(state.last_correct),
        hinted=open_mistake,
        confidence=sure,
        assessment=found,
    )
    stored = episode.to_payload()
    if effect:
        stored["effect"] = effect
    return stored, public(episode)
