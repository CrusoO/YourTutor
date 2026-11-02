from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.learner.bkt import BktParams
from app.learner.loop_b import (
    HELP_SEEKING,
    MAX_ATTEMPTS,
    LearnerRecord,
    Snapshot,
    Versions,
    help_seeking_rate,
    run_loop_b,
)
from app.learner.traits import TraitPrior
from app.learner.types import LearnerEvent

PARAMS = {"s1": BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)}
PRIORS = {HELP_SEEKING: TraitPrior(mu0=0.2, sigma0_sq=0.04, sigma_obs_sq=0.04, half_life_days=30)}
VERSIONS = Versions(graph_version="g1", param_version="p1", policy_version="pol1")
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


def ev(item: str, event_type: str = "answer", **kw) -> LearnerEvent:
    base = {"item_id": item, "skill_id": "s1", "event_type": event_type, "session_id": "A"}
    base.update(kw)
    return LearnerEvent(**base)  # type: ignore[arg-type]


class MemoryStore:
    """In-memory RecordStore. `interfere` runs once before the first write, to simulate a race."""

    def __init__(self, interfere=None) -> None:
        self.records: dict[str, LearnerRecord] = {}
        self.snapshots: list[Snapshot] = []
        self.interfere = interfere
        self.write_attempts = 0

    def load(self, learner_id: str) -> LearnerRecord:
        return self.records.get(learner_id, LearnerRecord())

    def compare_and_set(self, learner_id, expected_version, record, snapshot) -> bool:
        self.write_attempts += 1
        if self.interfere is not None:
            hook, self.interfere = self.interfere, None
            hook(self)
        if self.load(learner_id).version != expected_version:
            return False
        self.records[learner_id] = record
        self.snapshots.append(snapshot)
        return True


def run(
    store: MemoryStore,
    session_events,
    *,
    watermark: int = 1,
    session_id: str = "A",
    at=T0,
    all_events=None,
):
    return run_loop_b(
        store,
        learner_id="L",
        session_id=session_id,
        watermark=watermark,
        all_events=session_events if all_events is None else all_events,
        session_events=session_events,
        params_by_skill=PARAMS,
        trait_priors=PRIORS,
        versions=VERSIONS,
        at=at,
    )


GOOD = [ev("a", correct=True), ev("b", correct=True)]
HINTY = [ev("a", "request_hint"), ev("a", correct=True), ev("b", correct=True)]


def test_help_seeking_rate_is_the_share_of_answered_items_hinted_first() -> None:
    assert help_seeking_rate(HINTY) == 0.5
    assert help_seeking_rate(GOOD) == 0.0
    assert help_seeking_rate([ev("a", "request_hint")]) is None
    assert help_seeking_rate([]) is None


def test_a_session_writes_a_versioned_snapshot() -> None:
    store = MemoryStore()
    out = run(store, GOOD)
    assert out.status == "applied"
    snap = out.snapshot
    assert snap is not None
    assert snap.versions == VERSIONS and snap.record_version == 1 and snap.watermark == 1
    assert snap.mastery["s1"] > PARAMS["s1"].p_init
    assert snap.mastery_delta["s1"] == pytest.approx(snap.mastery["s1"] - PARAMS["s1"].p_init)
    assert snap.traits[HELP_SEEKING].n > 0


def test_running_the_same_watermark_twice_changes_nothing() -> None:
    store = MemoryStore()
    run(store, GOOD)
    again = run(store, GOOD)
    assert again.status == "duplicate"
    assert len(store.snapshots) == 1 and store.records["L"].version == 1


def test_a_lower_watermark_is_also_a_duplicate() -> None:
    store = MemoryStore()
    run(store, GOOD, watermark=5)
    assert run(store, GOOD, watermark=3).status == "duplicate"


def test_late_events_with_a_higher_watermark_are_processed_again() -> None:
    store = MemoryStore()
    run(store, GOOD[:1], watermark=1)
    late = run(store, GOOD, watermark=2)
    assert late.status == "applied"
    assert store.records["L"].version == 2
    assert store.records["L"].processed["A"] == 2


def test_a_rerun_replaces_the_sessions_trait_observation_instead_of_adding() -> None:
    store = MemoryStore()
    run(store, GOOD, watermark=1)
    run(store, HINTY, watermark=2)
    obs = store.records["L"].observations[HELP_SEEKING]
    assert len(obs) == 1 and obs[0].x == 0.5


def test_each_session_adds_one_observation() -> None:
    store = MemoryStore()
    run(store, GOOD, session_id="A", at=T0)
    run(store, HINTY, session_id="B", at=T0 + timedelta(days=1))
    assert len(store.records["L"].observations[HELP_SEEKING]) == 2


def test_a_session_with_no_answers_records_no_observation() -> None:
    store = MemoryStore()
    out = run(store, [ev("a", "request_hint")])
    assert out.status == "applied"
    assert HELP_SEEKING not in store.records["L"].observations
    assert out.snapshot is not None and HELP_SEEKING not in out.snapshot.traits


def test_a_lost_race_is_retried_and_applied_once() -> None:
    def rival(store: MemoryStore) -> None:
        store.records["L"] = LearnerRecord(version=1, processed={"Z": 1})

    store = MemoryStore(interfere=rival)
    out = run(store, GOOD)
    assert out.status == "applied"
    assert store.write_attempts == 2
    assert store.records["L"].version == 2
    assert store.records["L"].processed == {"Z": 1, "A": 1}
    assert len(store.snapshots) == 1


def test_a_rival_that_already_did_this_session_makes_the_retry_a_duplicate() -> None:
    def rival(store: MemoryStore) -> None:
        store.records["L"] = LearnerRecord(version=1, processed={"A": 1})

    store = MemoryStore(interfere=rival)
    assert run(store, GOOD).status == "duplicate"
    assert store.snapshots == []


def test_endless_contention_gives_up_without_writing() -> None:
    class Busy(MemoryStore):
        def compare_and_set(self, *args, **kwargs) -> bool:  # noqa: ARG002
            self.write_attempts += 1
            return False

    store = Busy()
    assert run(store, GOOD).status == "contended"
    assert store.write_attempts == MAX_ATTEMPTS and store.snapshots == []


def test_the_same_input_gives_the_same_snapshot() -> None:
    a, b = MemoryStore(), MemoryStore()
    assert run(a, HINTY).snapshot == run(b, HINTY).snapshot


def test_mastery_comes_from_replaying_the_whole_log_not_just_the_session() -> None:
    earlier = [ev("x", correct=True), ev("y", correct=True), ev("z", correct=True)]
    store = MemoryStore()
    out = run(store, GOOD, all_events=[*earlier, *GOOD])
    alone = run(MemoryStore(), GOOD)
    assert out.snapshot is not None and alone.snapshot is not None
    assert out.snapshot.mastery["s1"] > alone.snapshot.mastery["s1"]
