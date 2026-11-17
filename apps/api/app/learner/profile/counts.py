"""Pure decay and merge for method and error counts (no database, no clock, no settings).

Counts are decayed on write with the form used in `traits.py`:
`c := c * 0.5 ** (gap_weeks * 7 / HALF_LIFE_DAYS)`, then 1 is added for a new event. Entries that
fall below DROP_BELOW are dropped, so an old habit or misconception cannot define a student.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

HALF_LIFE_DAYS = 60.0  # ESTIMATE: a half-life sweep on real logs picks the final value
DROP_BELOW = 0.5  # an entry this weak is forgotten rather than kept
SCHEMA_V = 1
_EPOCH = date(2025, 12, 29)  # the Monday that starts ISO week 1 of 2026


def week_index(day: date) -> int:
    """Whole weeks since the 2026 epoch: no day, no time of day (never below 0)."""
    return max(0, (day - _EPOCH).days // 7)


def decay_factor(gap_weeks: int) -> float:
    if gap_weeks <= 0:
        return 1.0
    return float(0.5 ** (gap_weeks * 7 / HALF_LIFE_DAYS))


@dataclass(frozen=True)
class Counts:
    methods: dict[str, float] = field(default_factory=dict)
    errors: dict[str, float] = field(default_factory=dict)
    n_events: float = 0.0
    week: int = 0


def _decay_map(values: dict[str, float], factor: float) -> dict[str, float]:
    scaled = {k: v * factor for k, v in values.items()}
    return {k: v for k, v in sorted(scaled.items()) if v >= DROP_BELOW}


def decayed(counts: Counts, week: int) -> Counts:
    """The same counts as seen in `week` (the read-time decay; stored values are not changed)."""
    factor = decay_factor(week - counts.week)
    return Counts(
        _decay_map(counts.methods, factor),
        _decay_map(counts.errors, factor),
        counts.n_events * factor,
        max(week, counts.week),
    )


def add_event(counts: Counts, *, kind: str, key: str, increment: int, week: int) -> Counts:
    """Decay to `week`, then add `increment` to one method or error id."""
    if kind not in ("method", "error"):
        raise ValueError("kind must be 'method' or 'error'")
    base = decayed(counts, week)
    methods, errors = dict(base.methods), dict(base.errors)
    target = methods if kind == "method" else errors
    target[key] = target.get(key, 0.0) + float(increment)
    return Counts(
        dict(sorted(methods.items())), dict(sorted(errors.items())), base.n_events + 1.0, week
    )


def to_payload(counts: Counts) -> dict[str, Any]:
    return {
        "v": SCHEMA_V,
        "m": counts.methods,
        "e": counts.errors,
        "n": counts.n_events,
        "w": counts.week,
    }


def from_payload(data: dict[str, Any]) -> Counts:
    if data.get("v") != SCHEMA_V:
        raise ValueError("unknown profile schema")
    return Counts(
        {str(k): float(v) for k, v in data["m"].items()},
        {str(k): float(v) for k, v in data["e"].items()},
        float(data["n"]),
        int(data["w"]),
    )
