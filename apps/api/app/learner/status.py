"""Student-facing status from the mastery ladder (ARCHITECTURE §11.3): pure, no I/O."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

NOT_STARTED = "not_started"
LEARNING = "learning"
CAN_DO_IT = "can_do_it"
SOLID = "solid"
REVIEW_DUE = "review_due"

# order used for "minimum over skills" (review_due is handled separately)
_ORDER = (NOT_STARTED, LEARNING, CAN_DO_IT, SOLID)


def skill_status(level: int, *, review_overdue: bool = False) -> str:
    """0 not started, 1-3 learning, 4-6 can do it, 7 solid.

    An overdue FSRS card shows *review due* instead of can do it / solid until the next correct
    recall; it never replaces not started / learning.
    """
    if level <= 0:
        return NOT_STARTED
    if level <= 3:
        return LEARNING
    if review_overdue:
        return REVIEW_DUE
    return CAN_DO_IT if level <= 6 else SOLID


def review_overdue(due_at: datetime | None, now: datetime) -> bool:
    return due_at is not None and due_at <= now


def chapter_status(statuses: Iterable[str]) -> str:
    """Minimum skill status, or review due if any skill is due. An empty chapter is not started."""
    rows = list(statuses)
    if not rows:
        return NOT_STARTED
    if REVIEW_DUE in rows:
        return REVIEW_DUE
    return min(rows, key=_ORDER.index)
