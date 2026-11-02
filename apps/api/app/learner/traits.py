"""Shadow learner traits: a decaying normal-normal estimate per trait.

Pure functions, no database and no clock. A trait here is a weak, revisable estimate of something
like how comfortable a learner is with one representation, or how much load they tolerate. It is
*shadow only*: computed and stored so it can be compared later, and never used to choose what a
learner sees.

For each trait the population gives a prior (mu0, sigma0_sq). A learner is summarised by two
decayed sufficient statistics: n (effective sessions) and sum_x (their summed observations). One
observation per session per trait, so n counts sessions and not correlated attempts.

    precision = 1 / sigma0_sq + n / sigma_obs_sq
    mean      = (mu0 / sigma0_sq + sum_x / sigma_obs_sq) / precision
    variance  = 1 / precision

Before each new observation, n and sum_x are multiplied by gamma ** gap_days with
gamma = 0.5 ** (1 / half_life_days), so old evidence fades and the estimate drifts back to the
prior. The mean is never overwritten by one session's value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

_SECONDS_PER_DAY = 86_400.0


@dataclass(frozen=True)
class TraitPrior:
    """Population prior and noise for one trait; every number is a TUNABLE-DEFAULT to fit later."""

    mu0: float
    sigma0_sq: float
    sigma_obs_sq: float
    half_life_days: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.mu0):
            raise ValueError("mu0 must be finite")
        for name in ("sigma0_sq", "sigma_obs_sq", "half_life_days"):
            value = getattr(self, name)
            if not (math.isfinite(value) and value > 0.0):
                raise ValueError(f"{name} must be positive, got {value!r}")


@dataclass(frozen=True)
class TraitState:
    """Decayed sufficient statistics for one learner and one trait."""

    n: float = 0.0
    sum_x: float = 0.0
    last_at: datetime | None = None


@dataclass(frozen=True)
class TraitEstimate:
    mean: float
    variance: float
    n: float


def decay_factor(half_life_days: float, gap_days: float) -> float:
    """gamma ** gap, gamma = 0.5 ** (1 / half_life); a negative gap (clock skew) counts as zero."""
    if math.isnan(gap_days):
        raise ValueError("gap_days must not be NaN")
    return 0.5 ** (max(0.0, gap_days) / half_life_days)


def _gap_days(previous: datetime | None, current: datetime) -> float:
    if previous is None:
        return 0.0
    return max(0.0, (current - previous).total_seconds() / _SECONDS_PER_DAY)


def decayed(state: TraitState, prior: TraitPrior, at: datetime) -> TraitState:
    """The state as it stands at `at`, with older evidence faded."""
    factor = decay_factor(prior.half_life_days, _gap_days(state.last_at, at))
    return TraitState(n=state.n * factor, sum_x=state.sum_x * factor, last_at=at)


def observe(state: TraitState, prior: TraitPrior, x: float, at: datetime) -> TraitState:
    """Fold in one session's aggregate observation of the trait."""
    if not math.isfinite(x):
        raise ValueError("an observation must be finite")
    faded = decayed(state, prior, at)
    return TraitState(n=faded.n + 1.0, sum_x=faded.sum_x + x, last_at=at)


def estimate(state: TraitState, prior: TraitPrior, at: datetime | None = None) -> TraitEstimate:
    """The current belief. Pass `at` to read it with evidence faded to that moment."""
    current = decayed(state, prior, at) if at is not None and state.last_at is not None else state
    precision = 1.0 / prior.sigma0_sq + current.n / prior.sigma_obs_sq
    mean = (prior.mu0 / prior.sigma0_sq + current.sum_x / prior.sigma_obs_sq) / precision
    return TraitEstimate(mean=mean, variance=1.0 / precision, n=current.n)
