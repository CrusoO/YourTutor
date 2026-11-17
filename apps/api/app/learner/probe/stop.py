"""When to stop asking (spec section 3). The first rule that holds wins."""

from __future__ import annotations

from collections.abc import Sequence

from app.learner.probe.select import marginals
from app.learner.probe.types import Answer, Belief, ProbeConfig

RESOLVED = "resolved"
LOW_GAIN = "low_gain"
ITEM_CAP = "item_cap"
TIME_CAP = "time_cap"
FRUSTRATION = "frustration"


def item_cap(n_skills: int, cfg: ProbeConfig) -> int:
    """12 items; 14 only for graphs of more than `wide_skills` probe skills."""
    return cfg.cap_items_wide if n_skills > cfg.wide_skills else cfg.cap_items


def should_stop(
    belief: Belief,
    asked: int,
    minutes: float,
    recent: Sequence[Answer],
    best_gain: float,
    cfg: ProbeConfig,
) -> str | None:
    """A stop reason, or None to keep going. `best_gain` is 0.0 when no item is left to ask."""
    marks = marginals(belief).values()
    if all(m >= cfg.resolve_hi or m <= cfg.resolve_lo for m in marks):
        return RESOLVED
    if best_gain < cfg.min_gain_bits:
        return LOW_GAIN
    if asked >= item_cap(len(belief.space.skills), cfg):
        return ITEM_CAP
    if minutes >= cfg.cap_minutes:
        return TIME_CAP
    tail = recent[-cfg.frustration_run :]
    if len(tail) >= cfg.frustration_run and all(not a.correct for a in tail):
        return FRUSTRATION
    return None
