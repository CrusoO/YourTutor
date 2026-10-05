"""G1 step 8 end to end: session end creates FSRS cards, an overdue card brings a warm-up."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.db.models import ReviewCardRow, SessionRow
from app.learner.status import REVIEW_DUE, review_overdue, skill_status
from tests.conftest import World
from tests.player.test_ladder_persistence import SKILL, Player, _seed, _stored


def _card(db: Session, world: World) -> ReviewCardRow | None:
    db.expire_all()
    return db.get(ReviewCardRow, (uuid.UUID(world.student_share_id), SKILL))


def test_ending_a_session_creates_a_review_card(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world)
    player = Player(client, world)
    player.lesson()
    for _ in range(2):
        player.answer_current()
    assert _card(db, world) is None
    player.send("idle_nudge", idle_ms=11 * 60 * 1000)
    assert player.action["type"] == "end_session"
    card = _card(db, world)
    assert card is not None and card.fsrs_state


def test_overdue_card_brings_a_warmup_and_shows_review_due_until_recalled(
    client: TestClient, world: World, db: Session
) -> None:
    _seed(db, world)
    first = Player(client, world)
    first.lesson()
    for _ in range(3):
        first.answer_current()
    first.send("idle_nudge", idle_ms=11 * 60 * 1000)
    ladder_level = _stored(db, world).ladder_level
    assert ladder_level == 4

    card = _card(db, world)
    assert card is not None
    card.due_at = now_utc() - timedelta(days=1)  # the card falls due
    ended = db.get(SessionRow, uuid.UUID(first.session_id))
    assert ended is not None
    ended.resumable = False  # a new day starts a new session instead of resuming the idle one
    db.commit()
    assert skill_status(ladder_level, review_overdue=review_overdue(card.due_at, now_utc())) == (
        REVIEW_DUE
    )

    second = Player(client, world)
    assert second.action["type"] == "warmup_item"
    second.answer_current()
    recalled = _card(db, world)
    assert recalled is not None
    assert not review_overdue(recalled.due_at, now_utc())  # correct recall clears review due
