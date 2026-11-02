"""BKT-F shadow replay on the persisted event log: timestamps, latencies and per-item thresholds."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import EventRow, SessionRow
from app.learner.bkt import BktParams
from app.learner.bktf import AttemptKind
from app.learner.ladder import KIND_ANSWER, KIND_HINT, KIND_LESSON, LadderEvent
from app.orchestrator.types import CatalogItem
from app.player.ladder_log import (
    ladder_events_from_rows,
    learner_events_from_ladder,
    shadow_steps_for_student,
)
from tests.conftest import World

SKILL = "MATH.SHADOW.ONE"
PARAMS = {SKILL: BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)}
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


def item(item_id: str, *, min_plausible_ms: int | None = None) -> CatalogItem:
    return CatalogItem(
        id=item_id,
        skill_ids=(SKILL,),
        difficulty=0.25,
        pool="practice",
        status="approved",
        min_plausible_ms=min_plausible_ms,
    )


def row(
    session_id: uuid.UUID,
    item_id: str,
    event_type: str,
    at: datetime,
    *,
    correct: bool | None = None,
    latency_ms: int | None = None,
) -> EventRow:
    return EventRow(
        id=uuid.uuid4(),
        client_event_id=uuid.uuid4(),
        session_id=session_id,
        item_id=item_id,
        event_type=event_type,
        payload={},
        correct=correct,
        latency_ms=latency_ms,
        created_at=at,
    )


def test_latency_survives_the_trip_from_log_row_to_learner_event() -> None:
    rows = [(row(uuid.uuid4(), "A", "answer", T0, correct=True, latency_ms=1234), "practice")]
    [ladder] = ladder_events_from_rows(rows, {"A": item("A")})
    assert ladder.latency_ms == 1234
    [learner] = learner_events_from_ladder([ladder])
    assert (learner.latency_ms, learner.at, learner.correct) == (1234, T0, True)


def test_only_attempts_and_hints_become_learner_events() -> None:
    events = [
        LadderEvent("1", SKILL, KIND_ANSWER, T0, item_id="A", correct=True),
        LadderEvent("2", SKILL, KIND_HINT, T0, item_id="B"),
        LadderEvent("3", SKILL, KIND_LESSON, T0),
    ]
    assert [e.event_type for e in learner_events_from_ladder(events)] == ["answer", "request_hint"]


def test_replay_reads_the_stored_log_with_per_item_thresholds(db: Session, world: World) -> None:
    student_id = uuid.UUID(world.student_share_id)
    session = SessionRow(
        id=uuid.uuid4(),
        student_id=student_id,
        started_at=T0,
        type="practice",
        last_active_at=T0,
    )
    db.add(session)
    db.flush()
    later = T0 + timedelta(days=20)
    db.add_all(
        [
            row(session.id, "A", "answer", T0, correct=True, latency_ms=9000),
            # 3 s: faster than A's authored minimum (5 s), slower than the 2 s default for B.
            row(session.id, "A2", "answer", later, correct=True, latency_ms=3000),
            row(
                session.id,
                "B",
                "answer",
                later + timedelta(minutes=1),
                correct=True,
                latency_ms=3000,
            ),
            row(session.id, "C", "request_hint", later + timedelta(minutes=2)),
            row(
                session.id,
                "C",
                "answer",
                later + timedelta(minutes=3),
                correct=True,
                latency_ms=100,
            ),
        ]
    )
    db.commit()
    catalog = (
        item("A"),
        item("A2", min_plausible_ms=5000),
        item("B"),
        item("C", min_plausible_ms=5000),
    )

    steps = shadow_steps_for_student(db, student_id, catalog, PARAMS)

    assert [s.item_id for s in steps] == ["A", "A2", "B", "C"]
    assert [s.kind for s in steps] == [
        AttemptKind.VALID,
        AttemptKind.RAPID_GUESS,
        AttemptKind.VALID,
        AttemptKind.HINTED,
    ]
    assert round(steps[1].gap_days) == 20
    # A rapid guess is predicted at the guess rate, however well the skill was known.
    assert steps[1].predicted_shadow == PARAMS[SKILL].p_guess


def test_a_student_with_no_log_gives_no_steps(db: Session, world: World) -> None:
    assert (
        shadow_steps_for_student(db, uuid.UUID(world.student_share_id), (item("A"),), PARAMS) == []
    )
