"""Support level for a skill: how much of the solution the student sees (pure, no wiring).

`full` is a worked example that fades, `partial` a completion problem, `problems` a plain
practice item. The probe label only sets the start. Support then follows the observed first
attempts, so after `decide_after_items` items the starting label no longer matters.
No database, settings, clock or randomness here; the YAML loader is `support_config.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Support = Literal["full", "partial", "problems"]
_ORDER: tuple[Support, ...] = ("full", "partial", "problems")  # most to least support
LABELS = ("known", "unclear", "not_known")


@dataclass(frozen=True)
class SupportConfig:
    """Numbers for the policy; the defaults mirror config/support.yaml (TUNABLE-DEFAULT)."""

    full_below: float = 0.25
    problems_above: float = 0.70
    stale_after_days: float = 21.0
    fade_after_clean: int = 2
    raise_after_misses: int = 2
    min_items_between_changes: int = 2
    decide_after_items: int = 3
    full_max_partial_hidden: int = 2

    def __post_init__(self) -> None:
        if not 0.0 <= self.full_below <= self.problems_above <= 1.0:
            raise ValueError("need 0 <= full_below <= problems_above <= 1")
        if self.stale_after_days <= 0:
            raise ValueError("stale_after_days must be positive")
        for name in ("fade_after_clean", "raise_after_misses", "decide_after_items"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be at least 1")
        if self.min_items_between_changes < 0 or self.full_max_partial_hidden < 0:
            raise ValueError("min_items_between_changes and full_max_partial_hidden must be >= 0")
        if self.decide_after_items < max(self.fade_after_clean, self.raise_after_misses):
            raise ValueError("decide_after_items must cover the fade and raise windows")


@dataclass(frozen=True)
class AttemptOutcome:
    """What happened on one item, first attempt only. A reveal is never also a clean pass."""

    correct_first: bool
    hinted: bool = False
    revealed: bool = False

    def __post_init__(self) -> None:
        if self.revealed and self.correct_first:
            raise ValueError("a revealed item cannot be a correct first attempt")

    @property
    def clean(self) -> bool:
        return self.correct_first and not self.hinted

    @property
    def miss(self) -> bool:
        return self.revealed or not self.correct_first


DEFAULT_CONFIG = SupportConfig()


def initial_support(
    p_known: float,
    label: str,
    evidence_age_days: float | None,
    cfg: SupportConfig = DEFAULT_CONFIG,
) -> Support:
    """Starting support from the probe. Old evidence is never strong: known becomes partial."""
    if label not in LABELS:
        raise ValueError(f"unknown label {label!r}")
    if not 0.0 <= p_known <= 1.0:
        raise ValueError("p_known must lie in [0, 1]")
    if evidence_age_days is not None and evidence_age_days < 0:
        raise ValueError("evidence_age_days must not be negative")
    if label == "not_known" or p_known < cfg.full_below:
        return "full"
    if label == "unclear" or p_known <= cfg.problems_above:
        return "partial"
    stale = evidence_age_days is not None and evidence_age_days > cfg.stale_after_days
    return "partial" if stale else "problems"


def _shift(current: Support, step: int) -> Support:
    index = min(len(_ORDER) - 1, max(0, _ORDER.index(current) + step))
    return _ORDER[index]


def _tail(outcomes: Sequence[AttemptOutcome], wanted: str) -> int:
    count = 0
    for outcome in reversed(outcomes):
        if not getattr(outcome, wanted):
            break
        count += 1
    return count


def next_support(
    current: Support,
    first_attempts: Sequence[AttemptOutcome],
    cfg: SupportConfig = DEFAULT_CONFIG,
) -> Support:
    """One step of the fading rule, with no hysteresis (see `support_after`).

    Enough clean first attempts at the end: one step less support. Enough misses at the end, or a
    reveal as the last item: one step more. Anything else leaves it unchanged.
    """
    if current not in _ORDER:
        raise ValueError(f"unknown support {current!r}")
    if not first_attempts:
        return current
    if first_attempts[-1].revealed or _tail(first_attempts, "miss") >= cfg.raise_after_misses:
        return _shift(current, -1)
    if _tail(first_attempts, "clean") >= cfg.fade_after_clean:
        return _shift(current, +1)
    return current


def support_from_recent(
    first_attempts: Sequence[AttemptOutcome], cfg: SupportConfig = DEFAULT_CONFIG
) -> Support:
    """Support decided by the last `decide_after_items` outcomes alone (no prior, no history).

    Misses at the end (or a final reveal) give `full`; a clean run of the whole window gives
    `problems`; anything else gives `partial`.
    """
    window = tuple(first_attempts[-cfg.decide_after_items :])
    if not window:
        raise ValueError("need at least one outcome")
    if window[-1].revealed or _tail(window, "miss") >= cfg.raise_after_misses:
        return "full"
    if _tail(window, "clean") >= cfg.decide_after_items:
        return "problems"
    return "partial"


def support_after(
    initial: Support,
    first_attempts: Sequence[AttemptOutcome],
    cfg: SupportConfig = DEFAULT_CONFIG,
) -> Support:
    """Support now, given the starting level and every first attempt so far.

    Before `decide_after_items` items it fades from `initial`, at most one change per
    `min_items_between_changes` items. From then on only the last outcomes decide, so the starting
    label stops mattering (property k).
    """
    if initial not in _ORDER:
        raise ValueError(f"unknown support {initial!r}")
    if len(first_attempts) >= cfg.decide_after_items:
        return support_from_recent(first_attempts, cfg)
    level = initial
    since_change = cfg.min_items_between_changes  # the first change is allowed immediately
    for index in range(len(first_attempts)):
        since_change += 1
        if since_change < cfg.min_items_between_changes:
            continue
        moved = next_support(level, first_attempts[: index + 1], cfg)
        if moved != level:
            level, since_change = moved, 0
    return level


def hidden_steps(
    support: Support, total_steps: int, fade_index: int, cfg: SupportConfig = DEFAULT_CONFIG
) -> int:
    """Solution steps to hide. `full` fades 0, 1, 2, then all along the example (`fade_index`);
    `partial` shows only the first step; `problems` hides everything. Never more than the total."""
    if support not in _ORDER:
        raise ValueError(f"unknown support {support!r}")
    if total_steps < 0 or fade_index < 0:
        raise ValueError("total_steps and fade_index must not be negative")
    if support == "problems":
        return total_steps
    if support == "partial":
        return max(total_steps - 1, 0)
    if fade_index > cfg.full_max_partial_hidden:
        return total_steps
    return min(fade_index, total_steps)
