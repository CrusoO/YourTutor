"""Replay an event log through BKT-F next to the live BKT, without touching the live path.

Pure and deterministic: the same log and parameters always give the same trace. Nothing here writes
mastery, the ladder or FSRS state; the live model is run on its own copy so the two can be compared
step by step. This is how BKT-F earns promotion (PLAN.md Decisions): on logged attempts, not on
faith.

How a log event becomes a BKT-F attempt (one update per item, like the live model):

- `request_hint` marks the item as hinted. It does not update BKT-F by itself.
- The first `answer` to an item is the attempt. It is HINTED if the item was hinted, RAPID_GUESS
  if it came back faster than `rapid_guess_ms`, and VALID otherwise.
- `gap_days` is the time since this skill's previous attempt, from `LearnerEvent.at`. Without
  timestamps the gap is zero and BKT-F cannot forget, so a log without them says little about decay.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from app.learner.bkt import BktParams
from app.learner.bktf import AttemptKind, BktFParams, decay, predict_correct, update
from app.learner.mastery_service import apply_event
from app.learner.scheduler_fsrs import FixedClock
from app.learner.types import LearnerEvent, LearnerState

# TUNABLE-DEFAULT: answers faster than this are treated as guesses. Placeholder until Loop C can
# fit a per-item threshold from latency distributions; a real value needs pilot data.
DEFAULT_RAPID_GUESS_MS = 2000
# TUNABLE-DEFAULT: forgetting time-constant and hint weight used when only legacy parameters exist.
DEFAULT_TAU_DAYS = 30.0
DEFAULT_HINT_WEIGHT = 0.5

_SECONDS_PER_DAY = 86_400.0
_CLOCK = FixedClock(datetime(2000, 1, 1, tzinfo=UTC))  # FSRS timestamps are unused here


def shadow_params(
    legacy: BktParams,
    *,
    tau_days: float = DEFAULT_TAU_DAYS,
    hint_weight: float = DEFAULT_HINT_WEIGHT,
) -> BktFParams:
    """BKT-F parameters that share the live model's prior, learn, slip and guess values."""
    return BktFParams(
        p_init=legacy.p_init,
        p_learn=legacy.p_learn,
        p_slip=legacy.p_slip,
        p_guess=legacy.p_guess,
        tau_days=tau_days,
        hint_weight=hint_weight,
    )


@dataclass(frozen=True)
class ShadowStep:
    """One attempt, seen by both models; `predicted_*` is P(correct) before the answer."""

    index: int
    skill_id: str
    item_id: str
    kind: AttemptKind
    correct: bool
    gap_days: float
    predicted_live: float
    predicted_shadow: float
    p_live: float
    p_shadow: float


def _gap_days(previous: datetime | None, current: datetime | None) -> float:
    if previous is None or current is None:
        return 0.0
    return max(0.0, (current - previous).total_seconds() / _SECONDS_PER_DAY)


def _kind(hinted: bool, latency_ms: int | None, rapid_guess_ms: int) -> AttemptKind:
    if hinted:
        return AttemptKind.HINTED
    if latency_ms is not None and latency_ms < rapid_guess_ms:
        return AttemptKind.RAPID_GUESS
    return AttemptKind.VALID


def replay_shadow(
    events: Sequence[LearnerEvent],
    legacy_params: dict[str, BktParams],
    shadow: dict[str, BktFParams] | None = None,
    *,
    rapid_guess_ms: int = DEFAULT_RAPID_GUESS_MS,
    rapid_guess_ms_by_item: Mapping[str, int] | None = None,
) -> list[ShadowStep]:
    """Walk the log once, advancing both models, and return one step per first answer.

    `rapid_guess_ms_by_item` overrides the default threshold for the items it names.
    """
    thresholds = rapid_guess_ms_by_item or {}
    shadow = shadow or {sid: shadow_params(p) for sid, p in legacy_params.items()}
    live_state = LearnerState()
    live_memory: dict = {
        "bkt_done": set(),
        "hinted": set(),
        "first_wrong": set(),
        "session_unhinted": defaultdict(lambda: defaultdict(lambda: [0, 0])),
        "warmup_skills": set(),
    }
    p_shadow: dict[str, float] = {}
    last_at: dict[str, datetime | None] = {}
    hinted: set[str] = set()
    answered: set[str] = set()
    steps: list[ShadowStep] = []

    for index, event in enumerate(events):
        counted = event.event_type == "answer" and event.pool != "checkpoint"
        first_answer = counted and event.item_id not in answered
        skill_id = event.skill_id
        before_live = None
        if first_answer:
            row = live_state.mastery.get(skill_id)
            before_live = row.p_known if row is not None else legacy_params[skill_id].p_init

        apply_event(live_state, event, legacy_params, clock=_CLOCK, memory=live_memory)

        if event.event_type == "request_hint" and event.pool != "checkpoint":
            hinted.add(event.item_id)
            continue
        if not first_answer or before_live is None:
            continue

        answered.add(event.item_id)
        params = shadow[skill_id]
        kind = _kind(
            event.item_id in hinted,
            event.latency_ms,
            thresholds.get(event.item_id, rapid_guess_ms),
        )
        gap = _gap_days(last_at.get(skill_id), event.at)
        prior = p_shadow.get(skill_id, params.p_init)
        correct = bool(event.correct)
        steps.append(
            ShadowStep(
                index=index,
                skill_id=skill_id,
                item_id=event.item_id,
                kind=kind,
                correct=correct,
                gap_days=gap,
                predicted_live=_live_prediction(before_live, legacy_params[skill_id]),
                predicted_shadow=predict_correct(decay(prior, gap, params), params, kind),
                p_live=live_state.mastery[skill_id].p_known,
                p_shadow=update(prior, correct=correct, kind=kind, gap_days=gap, params=params),
            )
        )
        p_shadow[skill_id] = steps[-1].p_shadow
        if event.at is not None:
            last_at[skill_id] = event.at
    return steps


def _live_prediction(p_known: float, params: BktParams) -> float:
    """The live model's P(correct): it has no forgetting, so the estimate is used as it stands."""
    return p_known * (1.0 - params.p_slip) + (1.0 - p_known) * params.p_guess


@dataclass(frozen=True)
class Comparison:
    attempts: int
    live_log_loss: float
    shadow_log_loss: float

    @property
    def shadow_is_better(self) -> bool:
        return self.shadow_log_loss < self.live_log_loss


def _clip(p: float) -> float:
    return min(1.0 - 1e-9, max(1e-9, p))


def _log_loss(pairs: Sequence[tuple[float, bool]]) -> float:
    total = 0.0
    for q, correct in pairs:
        q = _clip(q)
        total -= math.log(q if correct else 1.0 - q)
    return total / len(pairs)


def compare(steps: Sequence[ShadowStep]) -> Comparison:
    """How well each model predicted the answers it was about to see. Lower log-loss is better."""
    if not steps:
        raise ValueError("no attempts to compare")
    return Comparison(
        attempts=len(steps),
        live_log_loss=_log_loss([(s.predicted_live, s.correct) for s in steps]),
        shadow_log_loss=_log_loss([(s.predicted_shadow, s.correct) for s in steps]),
    )
