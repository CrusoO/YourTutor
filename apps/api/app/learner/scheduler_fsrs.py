from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Protocol

from fsrs import Card, Rating, Scheduler

from app.learner.types import ReviewCard


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        from app.auth.security import now_utc

        return now_utc()


class FixedClock:
    def __init__(self, when: datetime) -> None:
        self._when = when

    def now(self) -> datetime:
        return self._when


_SCHEDULER = Scheduler(enable_fuzzing=False)


def _stable_card_id(skill_id: str) -> int:
    digest = hashlib.sha256(skill_id.encode()).digest()[:8]
    return int.from_bytes(digest, "big") % 10**12


def rating_from_warmup(*, correct: bool, hinted: bool, latency_ms: int | None) -> Rating:
    if not correct:
        return Rating.Again
    if hinted:
        return Rating.Hard
    if latency_ms is not None and latency_ms > 60_000:
        return Rating.Good
    return Rating.Easy


def rating_from_unhinted_rate(rate: float) -> Rating:
    if rate <= 0.0:
        return Rating.Again
    if rate <= 0.5:
        return Rating.Hard
    if rate < 0.85:
        return Rating.Good
    return Rating.Easy


def _card_from_state(state: dict | None, skill_id: str, now: datetime) -> Card:
    if not state:
        return Card(card_id=_stable_card_id(skill_id), due=now)
    return Card.from_dict(state)  # type: ignore[arg-type]


def review(
    card: ReviewCard | None,
    *,
    skill_id: str,
    rating: Rating,
    now: datetime,
) -> ReviewCard:
    fsrs_card = _card_from_state(card.fsrs_state if card else None, skill_id, now)
    updated, _log = _SCHEDULER.review_card(fsrs_card, rating, now)
    state = dict(updated.to_dict())
    due = updated.due
    if due.tzinfo is None and now.tzinfo is not None:
        due = due.replace(tzinfo=now.tzinfo)
    return ReviewCard(skill_id=skill_id, due_at=due, fsrs_state=state)
