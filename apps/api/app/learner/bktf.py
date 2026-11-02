"""BKT-F: Bayesian knowledge tracing with forgetting and attempt-quality handling.

Pure functions only: no database, no clock, no logging. Callers pass the elapsed time since the last
attempt, so the same inputs always give the same output on the client, the server and in replay.

This is a *shadow* model. It sits beside `app.learner.bkt` and is not wired into the runtime: the
"exactly one BKT update per item" guardrail (PLAN.md section 5) still belongs to `bkt.py` until
BKT-F has been compared against it on logged attempts and promoted.

Per attempt, in this order:

1. Decay over the gap: P' = floor + (P - floor) * exp(-gap / tau). Knowledge drifts toward the
   floor, so a decayed estimate never falls below the floor and a low estimate is never pushed
   further down.
2. Evidence, by attempt kind:
   - VALID: the normal slip/guess update.
   - RAPID_GUESS: skipped. A guess says nothing about knowledge. (Setting guess to 1 would be
     wrong: the "incorrect" formula then returns exactly 1.)
   - HINTED: a correct answer is tempered, posterior proportional to prior * likelihood**w with
     w in [0, 1] (w = 0 is no evidence). A wrong answer gets the normal update.
3. Learning: P = P + (1 - P) * T after VALID and HINTED attempts, never after a rapid guess.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class AttemptKind(StrEnum):
    VALID = "valid"
    RAPID_GUESS = "rapid_guess"
    HINTED = "hinted"


@dataclass(frozen=True)
class BktFParams:
    """Per-skill parameters. Probabilities are open intervals: 0 and 1 make the model degenerate."""

    p_init: float
    p_learn: float
    p_slip: float
    p_guess: float
    tau_days: float
    p_floor: float = 0.0
    hint_weight: float = 0.5

    def __post_init__(self) -> None:
        for name in ("p_init", "p_learn", "p_slip", "p_guess"):
            value = getattr(self, name)
            if not (math.isfinite(value) and 0.0 < value < 1.0):
                raise ValueError(f"{name} must be strictly between 0 and 1, got {value!r}")
        if self.p_slip + self.p_guess >= 1.0:
            raise ValueError("p_slip + p_guess must be below 1, or a correct answer says nothing")
        if not (math.isfinite(self.tau_days) and self.tau_days > 0.0):
            raise ValueError(f"tau_days must be positive, got {self.tau_days!r}")
        if not (math.isfinite(self.p_floor) and 0.0 <= self.p_floor < 1.0):
            raise ValueError(f"p_floor must be in [0, 1), got {self.p_floor!r}")
        if not (math.isfinite(self.hint_weight) and 0.0 <= self.hint_weight <= 1.0):
            raise ValueError(f"hint_weight must be in [0, 1], got {self.hint_weight!r}")

    @property
    def floor(self) -> float:
        """The level forgetting settles at: the larger of the prior and the configured floor."""
        return max(self.p_init, self.p_floor)


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


def decay(p_known: float, gap_days: float, params: BktFParams) -> float:
    """Pull the estimate toward the floor over `gap_days`; a negative gap (clock skew) is zero."""
    if math.isnan(gap_days):
        raise ValueError("gap_days must not be NaN")
    p = _clamp01(p_known)
    floor = params.floor
    retained = math.exp(-max(0.0, gap_days) / params.tau_days)
    return _clamp01(floor + (p - floor) * retained)


def predict_correct(
    p_known: float, params: BktFParams, kind: AttemptKind = AttemptKind.VALID
) -> float:
    """Probability the next answer is correct, given the (already decayed) estimate.

    A rapid guess is correct at the guess rate whatever the learner knows.
    """
    if kind is AttemptKind.RAPID_GUESS:
        return params.p_guess
    p = _clamp01(p_known)
    return p * (1.0 - params.p_slip) + (1.0 - p) * params.p_guess


def _posterior(p: float, *, correct: bool, params: BktFParams, weight: float) -> float:
    if correct:
        like_known, like_unknown = 1.0 - params.p_slip, params.p_guess
    else:
        like_known, like_unknown = params.p_slip, 1.0 - params.p_guess
    # Both likelihoods are strictly positive (guaranteed by BktFParams), so the denominator is too.
    numer = p * like_known**weight
    denom = numer + (1.0 - p) * like_unknown**weight
    return numer / denom


def update(
    p_known: float,
    *,
    correct: bool,
    kind: AttemptKind,
    gap_days: float,
    params: BktFParams,
) -> float:
    """One attempt: decay, then evidence, then learning. Returns the new estimate in [0, 1]."""
    p = decay(p_known, gap_days, params)
    if kind is AttemptKind.RAPID_GUESS:
        return p
    weight = params.hint_weight if (kind is AttemptKind.HINTED and correct) else 1.0
    p = _posterior(p, correct=correct, params=params, weight=weight)
    return _clamp01(p + (1.0 - p) * params.p_learn)
