"""Loop B: the post-session job that reconciles a learner's record, as pure logic over a store.

After a session it (1) replays the learner's whole log to reconcile mastery, the replay being the
authority, (2) records one shadow-trait observation for the session, and (3) writes a versioned
snapshot. Everything that touches storage goes through `RecordStore`, so the same code runs against
memory in tests and a database later.

Safe to repeat:

- Dedupe key (learner, session, watermark). A session already processed at this watermark or a
  higher one is skipped; late events carry a higher watermark and are processed again.
- A re-run replaces that session's trait observation instead of adding a second one, because the
  trait state is always folded from the stored per-session observations in time order.
- Writes are compare-and-set on the record version. If another writer got there first, the job
  re-reads and tries again, a bounded number of times.

Shadow only: nothing here changes what a learner is shown. Only help-seeking can be measured from
the log today; representation fluency and load tolerance need item metadata that does not exist
yet, so no observation is produced for them (and none is invented).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.learner.bkt import BktParams
from app.learner.mastery_service import recompute_from_log
from app.learner.scheduler_fsrs import FixedClock
from app.learner.traits import TraitEstimate, TraitPrior, TraitState, estimate, observe
from app.learner.types import LearnerEvent

HELP_SEEKING = "help_seeking_rate"

# TUNABLE-DEFAULT: older observations are decayed to almost nothing by then, so they are dropped to
# keep the record small. Raise it if a trait's half-life is long.
MAX_OBSERVATIONS_PER_TRAIT = 200
# TUNABLE-DEFAULT: how many times to re-read and retry when another writer wins the race.
MAX_ATTEMPTS = 5


@dataclass(frozen=True)
class Versions:
    """What the numbers in a snapshot were computed under, so they can be replayed or migrated."""

    graph_version: str
    param_version: str
    policy_version: str


@dataclass(frozen=True)
class TraitObservation:
    session_id: str
    at: datetime
    x: float


@dataclass(frozen=True)
class LearnerRecord:
    """The stored Loop B state for one learner."""

    version: int = 0
    processed: Mapping[str, int] = field(default_factory=dict)  # session_id -> highest watermark
    observations: Mapping[str, tuple[TraitObservation, ...]] = field(default_factory=dict)
    mastery: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Snapshot:
    learner_id: str
    session_id: str
    watermark: int
    record_version: int
    versions: Versions
    created_at: datetime
    mastery: Mapping[str, float]
    mastery_delta: Mapping[str, float]
    traits: Mapping[str, TraitEstimate]


class RecordStore(Protocol):
    def load(self, learner_id: str) -> LearnerRecord: ...

    def compare_and_set(
        self, learner_id: str, expected_version: int, record: LearnerRecord, snapshot: Snapshot
    ) -> bool:
        """Store `record` and `snapshot` only if the stored version is still `expected_version`."""
        ...


@dataclass(frozen=True)
class Outcome:
    status: str  # "applied", "duplicate" or "contended"
    snapshot: Snapshot | None = None


def help_seeking_rate(session_events: Sequence[LearnerEvent]) -> float | None:
    """Share of the items answered in this session that were hinted first. None if none answered."""
    hinted = {e.item_id for e in session_events if e.event_type == "request_hint"}
    answered = {e.item_id for e in session_events if e.event_type == "answer"}
    if not answered:
        return None
    return len(hinted & answered) / len(answered)


def _fold(observations: Sequence[TraitObservation], prior: TraitPrior) -> TraitState:
    state = TraitState()
    for obs in sorted(observations, key=lambda o: (o.at, o.session_id)):
        state = observe(state, prior, obs.x, obs.at)
    return state


def _with_observation(
    existing: tuple[TraitObservation, ...], new: TraitObservation
) -> tuple[TraitObservation, ...]:
    kept = [o for o in existing if o.session_id != new.session_id]  # a re-run replaces, not adds
    kept.append(new)
    kept.sort(key=lambda o: (o.at, o.session_id))
    return tuple(kept[-MAX_OBSERVATIONS_PER_TRAIT:])


def run_loop_b(
    store: RecordStore,
    *,
    learner_id: str,
    session_id: str,
    watermark: int,
    all_events: Sequence[LearnerEvent],
    session_events: Sequence[LearnerEvent],
    params_by_skill: Mapping[str, BktParams],
    trait_priors: Mapping[str, TraitPrior],
    versions: Versions,
    at: datetime,
) -> Outcome:
    """Process one session. `all_events` is the learner's whole log, in order; the replay is the
    authority for mastery. `at` is server time, passed in so the job has no clock of its own."""
    for _ in range(MAX_ATTEMPTS):
        record = store.load(learner_id)
        if record.processed.get(session_id, -1) >= watermark:
            return Outcome("duplicate")

        state = recompute_from_log(list(all_events), dict(params_by_skill), clock=FixedClock(at))
        mastery = {skill: row.p_known for skill, row in sorted(state.mastery.items())}
        delta = {
            skill: p - record.mastery.get(skill, params_by_skill[skill].p_init)
            for skill, p in mastery.items()
        }

        observations = dict(record.observations)
        x = help_seeking_rate(session_events)
        if x is not None and HELP_SEEKING in trait_priors:
            observations[HELP_SEEKING] = _with_observation(
                observations.get(HELP_SEEKING, ()), TraitObservation(session_id, at, x)
            )

        traits = {
            name: estimate(_fold(obs, trait_priors[name]), trait_priors[name], at=at)
            for name, obs in sorted(observations.items())
            if name in trait_priors
        }
        new_record = LearnerRecord(
            version=record.version + 1,
            processed={**record.processed, session_id: watermark},
            observations=observations,
            mastery=mastery,
        )
        snapshot = Snapshot(
            learner_id=learner_id,
            session_id=session_id,
            watermark=watermark,
            record_version=new_record.version,
            versions=versions,
            created_at=at,
            mastery=mastery,
            mastery_delta=delta,
            traits=traits,
        )
        if store.compare_and_set(learner_id, record.version, new_record, snapshot):
            return Outcome("applied", snapshot)
    return Outcome("contended")
