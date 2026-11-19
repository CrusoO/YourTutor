"""Numbers for the reason model: TUNABLE-DEFAULTs, validated here, to be tuned from pilot data."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# The kinds of cause the model can weigh. `other` is "none of the authored causes": a guess, a
# misread, or a mistake nobody has written down yet. It is always present, so an unmatched answer
# never forces a false label.
KINDS = ("misconception", "prerequisite_gap", "slip", "incomplete_procedure", "other")
OTHER = "other"


def _unit(name: str, value: float) -> None:
    if not (math.isfinite(value) and 0.0 < value < 1.0):
        raise ValueError(f"{name} must be strictly between 0 and 1, got {value!r}")


def _positive(name: str, value: float) -> None:
    if not (math.isfinite(value) and value > 0.0):
        raise ValueError(f"{name} must be a positive number, got {value!r}")


@dataclass(frozen=True)
class ReasonConfig:
    # How well each kind of cause explains an answer that matches its authored signature.
    lik_misconception: float = 0.9
    lik_prerequisite_gap: float = 0.7
    lik_slip: float = 0.5
    lik_incomplete_procedure: float = 0.6
    lik_other: float = 0.15  # the baseline for "none of the above"
    lik_absent: float = 0.08  # a cause seen before that does not explain this answer
    # How the learner's own "sure" or "unsure" tap moves the weights. A confident wrong answer
    # points at a held belief; an unsure one points at a guess or a slip.
    sure_boost: dict[str, float] = field(
        default_factory=lambda: {
            "misconception": 1.5,
            "prerequisite_gap": 1.3,
            "incomplete_procedure": 1.0,
            "slip": 0.6,
            "other": 0.6,
        }
    )
    unsure_boost: dict[str, float] = field(
        default_factory=lambda: {
            "misconception": 0.7,
            "prerequisite_gap": 1.0,
            "incomplete_procedure": 1.0,
            "slip": 1.2,
            "other": 1.6,
        }
    )
    correction_factor: float = 0.25  # "that's not why": the named cause keeps this share
    forget: float = 0.25  # share of the older evidence mixed back to even before a new answer
    unseen_prior: float = 0.2  # the weight a newly seen cause starts with
    band_likely: float = 0.7  # name the cause only above this share ...
    band_margin: float = 0.2  # ... and this lead over the next one
    band_maybe: float = 0.45

    def __post_init__(self) -> None:
        for name in (
            "lik_misconception",
            "lik_prerequisite_gap",
            "lik_slip",
            "lik_incomplete_procedure",
            "lik_other",
            "lik_absent",
            "correction_factor",
            "forget",
            "unseen_prior",
            "band_likely",
            "band_margin",
            "band_maybe",
        ):
            _unit(name, getattr(self, name))
        if self.band_maybe >= self.band_likely:
            raise ValueError("band_maybe must be below band_likely")
        for table_name in ("sure_boost", "unsure_boost"):
            table = getattr(self, table_name)
            for kind in KINDS:
                _positive(f"{table_name}[{kind}]", table.get(kind, math.nan))


DEFAULT_CONFIG = ReasonConfig()
