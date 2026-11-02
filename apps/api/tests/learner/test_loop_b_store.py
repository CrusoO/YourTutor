"""Loop B against the real database: durable state, real compare-and-set, and deletion."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.service import purge_students
from app.db.models import LoopBRecordRow, LoopBSnapshotRow
from app.learner.bkt import BktParams
from app.learner.loop_b import HELP_SEEKING, LearnerRecord, Snapshot, Versions, run_loop_b
from app.learner.loop_b_store import SqlRecordStore
from app.learner.traits import TraitPrior
from app.learner.types import LearnerEvent
from tests.conftest import World

PARAMS = {"s1": BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)}
PRIORS = {HELP_SEEKING: TraitPrior(mu0=0.2, sigma0_sq=0.04, sigma_obs_sq=0.04, half_life_days=30)}
VERSIONS = Versions("g1", "p1", "pol1")
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
EVENTS = [
    LearnerEvent(item_id="a", skill_id="s1", event_type="request_hint", session_id="A"),
    LearnerEvent(item_id="a", skill_id="s1", event_type="answer", correct=True, session_id="A"),
    LearnerEvent(item_id="b", skill_id="s1", event_type="answer", correct=True, session_id="A"),
]


def run(db: Session, learner_id: str, *, session_id="A", watermark=1, at=T0):
    return run_loop_b(
        SqlRecordStore(db),
        learner_id=learner_id,
        session_id=session_id,
        watermark=watermark,
        all_events=EVENTS,
        session_events=EVENTS,
        params_by_skill=PARAMS,
        trait_priors=PRIORS,
        versions=VERSIONS,
        at=at,
    )


def count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def snapshot_for(student_id: uuid.UUID, version: int) -> Snapshot:
    return Snapshot(
        learner_id=str(student_id),
        session_id="A",
        watermark=1,
        record_version=version,
        versions=VERSIONS,
        created_at=T0,
        mastery={},
        mastery_delta={},
        traits={},
    )


def test_a_session_is_stored_and_read_back_exactly(db: Session, world: World) -> None:
    learner = world.student_share_id
    out = run(db, learner)
    assert out.status == "applied"
    db.commit()

    loaded = SqlRecordStore(db).load(learner)
    assert loaded.version == 1 and loaded.processed == {"A": 1}
    assert loaded.mastery["s1"] == out.snapshot.mastery["s1"]
    [obs] = loaded.observations[HELP_SEEKING]
    assert (obs.session_id, obs.at, obs.x) == ("A", T0, 0.5)

    row = db.scalars(select(LoopBSnapshotRow)).one()
    assert row.versions == {"graph_version": "g1", "param_version": "p1", "policy_version": "pol1"}
    assert row.record_version == 1 and row.watermark == 1


def test_repeating_a_session_is_a_duplicate_and_adds_nothing(db: Session, world: World) -> None:
    run(db, world.student_share_id)
    assert run(db, world.student_share_id).status == "duplicate"
    assert count(db, LoopBSnapshotRow) == 1
    assert db.get(LoopBRecordRow, uuid.UUID(world.student_share_id)).version == 1  # type: ignore[union-attr]


def test_late_events_make_a_second_version_and_replace_the_observation(
    db: Session, world: World
) -> None:
    run(db, world.student_share_id, watermark=1)
    assert run(db, world.student_share_id, watermark=2).status == "applied"
    loaded = SqlRecordStore(db).load(world.student_share_id)
    assert loaded.version == 2 and len(loaded.observations[HELP_SEEKING]) == 1
    assert count(db, LoopBSnapshotRow) == 2


def test_a_stale_version_cannot_overwrite_a_newer_record(db: Session, world: World) -> None:
    learner = world.student_share_id
    run(db, learner)
    store = SqlRecordStore(db)
    stale = LearnerRecord(version=1, processed={"Z": 9})

    assert store.compare_and_set(learner, 0, stale, snapshot_for(uuid.UUID(learner), 1)) is False
    assert store.load(learner).processed == {"A": 1}
    assert count(db, LoopBSnapshotRow) == 1


def test_a_lost_race_for_the_first_record_leaves_the_session_usable(
    db: Session, world: World
) -> None:
    learner = world.student_share_id
    run(db, learner)
    store = SqlRecordStore(db)
    mine = LearnerRecord(version=1, processed={"Y": 1})

    assert store.compare_and_set(learner, 0, mine, snapshot_for(uuid.UUID(learner), 1)) is False
    assert store.load(learner).processed == {"A": 1}  # the session still works after the failure


def test_deleting_a_student_removes_their_loop_b_data(db: Session, world: World) -> None:
    run(db, world.student_share_id)
    db.commit()
    assert count(db, LoopBRecordRow) == 1

    purge_students(db, [uuid.UUID(world.student_share_id)])
    db.commit()

    assert count(db, LoopBRecordRow) == 0 and count(db, LoopBSnapshotRow) == 0


def test_two_learners_are_kept_apart(db: Session, world: World) -> None:
    run(db, world.student_share_id, at=T0)
    run(db, world.student_noshare_id, at=T0 + timedelta(days=1))
    assert count(db, LoopBRecordRow) == 2
    assert SqlRecordStore(db).load(world.student_share_id).version == 1
