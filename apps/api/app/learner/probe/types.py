"""Frozen value types for the probe. Validation lives in `__post_init__` (like `BktFParams`)."""

from __future__ import annotations

import math
from dataclasses import dataclass


class TooManyStates(Exception):
    """The prerequisite graph has more closed states than allowed; the caller shrinks the skills."""


def _open_unit(name: str, value: float) -> None:
    if not (math.isfinite(value) and 0.0 < value < 1.0):
        raise ValueError(f"{name} must be strictly between 0 and 1, got {value!r}")


def _positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be an integer of at least 1, got {value!r}")


@dataclass(frozen=True)
class ProbeConfig:
    """Loaded from config/probe.yaml. Every number is a TUNABLE-DEFAULT, validated here."""

    slip: float
    slip_multistep: float
    guess_typed: float
    guess_mcq_floor: float
    guess_mcq_cap: float
    idk_known: float
    idk_unknown: float
    prior_bases: tuple[float, ...]
    depth_decay: float
    mixture_floor: float
    resolve_hi: float
    resolve_lo: float
    min_gain_bits: float
    cap_items: int
    cap_items_wide: int
    cap_minutes: int
    max_per_skill: int
    max_states: int
    frustration_run: int
    seed_cap: float
    # Extras beyond the spec's list: constants the spec states in prose (sections 3 and 10).
    prior_clip: tuple[float, float] = (0.02, 0.98)
    guess_uncertain: float = 0.5
    opener_items: int = 2
    opener_min_success: float = 0.7
    wide_skills: int = 12
    seed_floor: float = 0.05
    unclear_lo: float = 0.2
    unclear_hi: float = 0.6

    def __post_init__(self) -> None:
        for name in (
            "slip",
            "slip_multistep",
            "guess_typed",
            "guess_mcq_floor",
            "guess_mcq_cap",
            "idk_known",
            "idk_unknown",
            "guess_uncertain",
        ):
            _open_unit(name, getattr(self, name))
        if self.guess_mcq_floor > self.guess_mcq_cap:
            raise ValueError("guess_mcq_floor must not exceed guess_mcq_cap")
        worst_slip = max(self.slip, self.slip_multistep)
        worst_guess = max(self.guess_typed, self.guess_mcq_cap, self.guess_uncertain)
        if worst_slip + worst_guess >= 1.0:
            raise ValueError("slip + guess must be below 1, or a correct answer says nothing")
        if self.idk_known >= self.idk_unknown:
            raise ValueError("idk_known must be below idk_unknown (IDK is evidence of not known)")
        if not self.prior_bases:
            raise ValueError("prior_bases must not be empty")
        for base in self.prior_bases:
            _open_unit("prior_bases entry", base)
        if not (math.isfinite(self.depth_decay) and 0.0 < self.depth_decay <= 1.0):
            raise ValueError(f"depth_decay must be in (0, 1], got {self.depth_decay!r}")
        lo, hi = self.prior_clip
        if not (0.0 < lo < hi < 1.0):
            raise ValueError("prior_clip must satisfy 0 < lo < hi < 1")
        if not (math.isfinite(self.mixture_floor) and 0.0 <= self.mixture_floor < 1.0):
            raise ValueError(f"mixture_floor must be in [0, 1), got {self.mixture_floor!r}")
        if self.mixture_floor * len(self.prior_bases) > 1.0 + 1e-12:
            raise ValueError("mixture_floor * len(prior_bases) must be at most 1")
        _open_unit("resolve_lo", self.resolve_lo)
        _open_unit("resolve_hi", self.resolve_hi)
        if not self.resolve_lo < 0.5 < self.resolve_hi:
            raise ValueError("resolve_lo must be below 0.5 and resolve_hi above it")
        if not (math.isfinite(self.min_gain_bits) and self.min_gain_bits >= 0.0):
            raise ValueError("min_gain_bits must be non-negative")
        for name in (
            "cap_items",
            "cap_items_wide",
            "cap_minutes",
            "max_per_skill",
            "max_states",
            "frustration_run",
            "wide_skills",
        ):
            _positive_int(name, getattr(self, name))
        if self.cap_items_wide < self.cap_items:
            raise ValueError("cap_items_wide must be at least cap_items")
        if isinstance(self.opener_items, bool) or self.opener_items < 0:
            raise ValueError("opener_items must be a non-negative integer")
        if not 0.0 <= self.opener_min_success <= 1.0:
            raise ValueError("opener_min_success must be in [0, 1]")
        if not (0.0 <= self.seed_floor < self.seed_cap <= 1.0):
            raise ValueError("need 0 <= seed_floor < seed_cap <= 1")
        if not (self.seed_floor <= self.unclear_lo <= self.unclear_hi <= self.seed_cap):
            raise ValueError("unclear bounds must lie within [seed_floor, seed_cap], lo <= hi")


@dataclass(frozen=True)
class ProbeItem:
    """A view of a catalog item with no content text; slip and guess are already decided."""

    item_id: str
    skill_id: str
    guess: float
    slip: float
    is_mcq: bool

    def __post_init__(self) -> None:
        if not self.item_id or not self.skill_id:
            raise ValueError("item_id and skill_id must not be empty")
        _open_unit("guess", self.guess)
        _open_unit("slip", self.slip)
        if self.slip + self.guess >= 1.0:
            raise ValueError("slip + guess must be below 1")


@dataclass(frozen=True)
class Answer:
    item_id: str
    skill_id: str
    correct: bool
    dont_know: bool = False
    rapid: bool = False
    unsure: bool = False

    def __post_init__(self) -> None:
        if self.dont_know and self.correct:
            raise ValueError("an 'I don't know' answer cannot be correct")


@dataclass(frozen=True)
class Space:
    """Built once per graph. `states` are bitmasks over `skills` (bit i is skills[i])."""

    skills: tuple[str, ...]
    states: tuple[int, ...]
    depth: tuple[int, ...]
    graph_hash: str

    def __post_init__(self) -> None:
        if len(self.depth) != len(self.skills):
            raise ValueError("depth must have one entry per skill")
        if not self.states:
            raise ValueError("a space has at least the empty state")

    def index(self, skill_id: str) -> int:
        try:
            return self.skills.index(skill_id)
        except ValueError:
            raise ValueError(f"skill {skill_id!r} is not in the probe space") from None


@dataclass(frozen=True)
class Belief:
    """Immutable. `joint[c][k]` is P(prior base c and state k); the rest are marginals of it."""

    space: Space
    weights: tuple[float, ...]
    mixture: tuple[float, ...]
    joint: tuple[tuple[float, ...], ...]
    reset: bool = False  # True if the weights underflowed and were restored to the prior

    @staticmethod
    def from_joint(
        space: Space, joint: list[list[float]] | tuple[tuple[float, ...], ...], reset: bool = False
    ) -> Belief:
        n = len(space.states)
        weights = tuple(sum(row[k] for row in joint) for k in range(n))
        mixture = tuple(sum(row) for row in joint)
        return Belief(space, weights, mixture, tuple(tuple(r) for r in joint), reset)


@dataclass(frozen=True)
class ProbeResult:
    marginals: dict[str, float]
    labels: dict[str, str]  # known | not_known | unclear
    start_skill: str | None
    ready_skills: tuple[str, ...]
    asked: int
    stop_reason: str
    mixture: tuple[float, ...]
    belief_reset: bool = False
