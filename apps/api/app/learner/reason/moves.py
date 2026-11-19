"""Which kinds of help to offer for a cause, and how much help to give. Pure, no I/O.

Help comes in families the player can already show: a picture (number line, balance), smaller steps
(the next hint), a worked example (the reveal), and a short video. The table says which family
suits which cause first; it is a starting rule, replaced by measured results once there are
enough answers to learn from. Nothing here reads a "style": a family is offered because of the
cause, and what the learner then picks and what works are both logged.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

FAMILIES = ("picture", "steps", "worked", "video")

# The first family listed is the best first guess for that cause.
PREFERENCE: dict[str, tuple[str, ...]] = {
    "misconception": ("picture", "worked", "steps", "video"),
    "prerequisite_gap": ("steps", "worked", "picture", "video"),
    "slip": ("steps", "picture", "worked", "video"),
    "incomplete_procedure": ("steps", "worked", "picture", "video"),
    "other": ("worked", "picture", "steps", "video"),
}

LEVEL_MIN, LEVEL_MAX = 0, 3  # 0 problem only, 1 hint only, 2 partly worked, 3 fully worked
START_LEVEL = 2
WINS_TO_FADE = 2  # unaided confident successes before help is reduced
MISSES_TO_RAISE = 2  # misses after help before more help is given


def offer(
    cause_kind: str,
    *,
    recent: Sequence[str] = (),
    available: Collection[str] = FAMILIES,
    count: int = 3,
) -> tuple[str, ...]:
    """Up to `count` families, best first. The one just used moves to the end, so "another way"
    really is another way; an unknown cause gets the general order."""
    order = PREFERENCE.get(cause_kind, PREFERENCE["other"])
    usable = [f for f in order if f in available]
    last = recent[-1] if recent else None
    if last in usable and len(usable) > 1:
        usable.remove(last)
        usable.append(last)
    return tuple(usable[:count])


@dataclass(frozen=True)
class Guidance:
    """How much help a learner gets on a skill: it fades with success and returns after misses."""

    level: int = START_LEVEL
    wins: int = 0
    misses: int = 0

    def as_payload(self) -> dict[str, int]:
        return {"level": self.level, "wins": self.wins, "misses": self.misses}

    @staticmethod
    def from_payload(raw: object) -> Guidance:
        if not isinstance(raw, dict):
            return Guidance()

        def num(key: str, default: int) -> int:
            value = raw.get(key, default)
            return value if isinstance(value, int) and not isinstance(value, bool) else default

        level = min(max(num("level", START_LEVEL), LEVEL_MIN), LEVEL_MAX)
        return Guidance(level, max(num("wins", 0), 0), max(num("misses", 0), 0))


def advance(g: Guidance, *, correct: bool, hinted: bool, confident: bool | None) -> Guidance:
    """The next level after one answer.

    Only an unaided answer that the learner was not unsure about counts as a win; two in a row take
    help away one step. A miss resets the wins; two misses give help back one step. Help that was
    asked for neither counts for nor against.
    """
    if correct:
        if hinted or confident is False:
            return Guidance(g.level, 0, 0)
        wins = g.wins + 1
        if wins >= WINS_TO_FADE:
            return Guidance(max(g.level - 1, LEVEL_MIN), 0, 0)
        return Guidance(g.level, wins, 0)
    misses = g.misses + 1
    if misses >= MISSES_TO_RAISE:
        return Guidance(min(g.level + 1, LEVEL_MAX), 0, 0)
    return Guidance(g.level, 0, misses)
