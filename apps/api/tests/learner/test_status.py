from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.learner.ladder import KIND_ANSWER, LadderEvent, SkillLadder, apply_ladder_event
from app.learner.scheduler_fsrs import FixedClock, rating_from_warmup, review
from app.learner.status import (
    CAN_DO_IT,
    LEARNING,
    NOT_STARTED,
    REVIEW_DUE,
    SOLID,
    chapter_status,
    review_overdue,
    skill_status,
)
from app.learner.types import ReviewCard

NOW = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        (0, NOT_STARTED),
        (1, LEARNING),
        (2, LEARNING),
        (3, LEARNING),
        (4, CAN_DO_IT),
        (5, CAN_DO_IT),
        (6, CAN_DO_IT),
        (7, SOLID),
    ],
)
def test_status_follows_ladder_levels(level: int, expected: str) -> None:
    assert skill_status(level) == expected


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        (0, NOT_STARTED),
        (3, LEARNING),
        (4, REVIEW_DUE),
        (6, REVIEW_DUE),
        (7, REVIEW_DUE),
    ],
)
def test_overdue_review_replaces_only_can_do_it_and_solid(level: int, expected: str) -> None:
    assert skill_status(level, review_overdue=True) == expected


def test_chapter_status_is_the_minimum_skill_status() -> None:
    assert chapter_status([SOLID, CAN_DO_IT, SOLID]) == CAN_DO_IT
    assert chapter_status([SOLID, LEARNING, CAN_DO_IT]) == LEARNING
    assert chapter_status([SOLID, SOLID]) == SOLID
    assert chapter_status([CAN_DO_IT, NOT_STARTED]) == NOT_STARTED
    assert chapter_status([]) == NOT_STARTED


def test_chapter_shows_review_due_if_any_skill_is_due() -> None:
    assert chapter_status([SOLID, REVIEW_DUE, LEARNING]) == REVIEW_DUE


def test_review_overdue_compares_due_date_with_now() -> None:
    assert review_overdue(NOW - timedelta(minutes=1), NOW)
    assert review_overdue(NOW, NOW)
    assert not review_overdue(NOW + timedelta(days=1), NOW)
    assert not review_overdue(None, NOW)


def test_review_due_appears_when_card_is_overdue_and_clears_on_correct_recall() -> None:
    """Level 6 skill, FSRS card falls due, a correct warm-up recall reschedules the card."""
    ladder = SkillLadder(skill_id="S1", achieved=[3, 4, 5, 6])
    card = review(
        None,
        skill_id="S1",
        rating=rating_from_warmup(correct=True, hinted=False, latency_ms=2000),
        now=NOW,
    )
    later = card.due_at + timedelta(days=1)
    assert skill_status(ladder.level, review_overdue=review_overdue(card.due_at, later)) == (
        REVIEW_DUE
    )
    # the correct recall happens (a warm-up answer), FSRS reschedules the card into the future
    ladders = {"S1": ladder}
    apply_ladder_event(
        ladders,
        LadderEvent(
            event_id="r1",
            skill_id="S1",
            kind=KIND_ANSWER,
            at=later,
            item_id="p1",
            correct=True,
            pool="warmup",
        ),
        p_known=0.99,
    )
    rescheduled: ReviewCard = review(
        card,
        skill_id="S1",
        rating=rating_from_warmup(correct=True, hinted=False, latency_ms=2000),
        now=FixedClock(later).now(),
    )
    assert rescheduled.due_at > later
    assert skill_status(
        ladders["S1"].level, review_overdue=review_overdue(rescheduled.due_at, later)
    ) == (CAN_DO_IT)
