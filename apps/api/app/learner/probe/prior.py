"""Mixture-of-bases prior over closed states (spec section 3).

For base b, skill i is known with p_i = clip(b * depth_decay ** depth_i). A closed state K has
weight proportional to the product of p_i (i in K) and 1 - p_i (i not in K), normalised over the
closed states. The prior is the weighted sum of one such distribution per base.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from app.learner.probe.types import Belief, ProbeConfig, Space

# Class tap (ESTIMATE): grade distance -> weights over the three default bases (low, mid, high).
_BY_DELTA = {1: (0.15, 0.35, 0.50), 0: (0.25, 0.45, 0.30), -1: (0.50, 0.35, 0.15)}


def _apply_floor(weights: Sequence[float], floor: float) -> tuple[float, ...]:
    """Normalise, then lift every weight to `floor`, taking the mass from the others."""
    total = sum(weights)
    w = [x / total for x in weights]
    n = len(w)
    for _ in range(n):
        low = [i for i in range(n) if w[i] < floor]
        if not low:
            break
        high = [i for i in range(n) if w[i] >= floor]
        spare = 1.0 - floor * len(low)
        mass = sum(w[i] for i in high)
        w = [floor if i in low else w[i] * spare / mass for i in range(n)]
    return tuple(w)


def mixture_weights_for(grade_delta: int | None, cfg: ProbeConfig) -> tuple[float, ...]:
    """The only place the class tap is used; every weight is at least `mixture_floor`."""
    n = len(cfg.prior_bases)
    if grade_delta is None or n != 3:
        raw: Sequence[float] = [1.0 / n] * n
    else:
        raw = _BY_DELTA[max(-1, min(1, grade_delta))]
    return _apply_floor(raw, cfg.mixture_floor)


def _component(space: Space, base: float, cfg: ProbeConfig) -> list[float]:
    lo, hi = cfg.prior_clip
    p = [min(hi, max(lo, base * cfg.depth_decay**d)) for d in space.depth]
    logs = []
    for state in space.states:
        logs.append(
            sum(math.log(p[i]) if state >> i & 1 else math.log(1.0 - p[i]) for i in range(len(p)))
        )
    top = max(logs)
    raw = [math.exp(x - top) for x in logs]
    total = sum(raw)
    return [x / total for x in raw]


def initial_belief(
    space: Space, cfg: ProbeConfig, mixture_weights: Sequence[float] | None = None
) -> Belief:
    """The prior as a belief. Given weights are validated and floored at `mixture_floor`."""
    n = len(cfg.prior_bases)
    if mixture_weights is None:
        weights = _apply_floor([1.0 / n] * n, cfg.mixture_floor)
    else:
        if len(mixture_weights) != n:
            raise ValueError(f"need {n} mixture weights, got {len(mixture_weights)}")
        if any(not math.isfinite(w) or w < 0.0 for w in mixture_weights):
            raise ValueError("mixture weights must be finite and non-negative")
        if sum(mixture_weights) <= 0.0:
            raise ValueError("mixture weights must not all be zero")
        weights = _apply_floor(mixture_weights, cfg.mixture_floor)
    joint = [
        [w * x for x in _component(space, base, cfg)]
        for w, base in zip(weights, cfg.prior_bases, strict=True)
    ]
    return Belief.from_joint(space, joint)
