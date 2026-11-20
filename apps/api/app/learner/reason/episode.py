"""One mistake episode on one skill: what we believe, how much help, and what was tried. Pure.

An episode opens at a wrong answer and closes at the next right one. Between those it carries the
shares of belief about the cause, the help families offered and used, and the guidance level. Each
step returns a new immutable episode, so the state can be rebuilt from the events log: the log row
for an answer stores `to_payload()`, and the next answer reads it back.

The "effect" it returns is one row of the effect ledger: after the learner chose a kind of help,
did the next answer come out right? Counts of those rows, per cause kind and family, are what
later decide which help to offer first. Nothing here is a label for the learner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.learner.reason.assess import Assessment
from app.learner.reason.moves import FAMILIES, Guidance, advance, offer
from app.learner.reason.posterior import (
    Confidence,
    Posterior,
    apply_correction,
    cause_kind,
    view,
)

MAX_RECENT = 3


@dataclass(frozen=True)
class Episode:
    skill: str
    posterior: Posterior | None = None  # None when no mistake is open
    guidance: Guidance = Guidance()
    recent: tuple[str, ...] = ()  # help families used, newest last
    offered: tuple[str, ...] = ()  # families shown with the last wrong answer
    pending: str | None = None  # a family chosen, waiting to see how the next answer goes

    def to_payload(self) -> dict[str, Any]:
        return {
            "skill": self.skill,
            "weights": dict(self.posterior.weights) if self.posterior else {},
            "guidance": self.guidance.as_payload(),
            "recent": list(self.recent),
            "offered": list(self.offered),
            "pending": self.pending,
        }

    @staticmethod
    def from_payload(raw: object) -> Episode | None:
        """An episode from a stored payload, or None when it is missing or damaged."""
        if not isinstance(raw, dict) or not isinstance(raw.get("skill"), str):
            return None
        weights = raw.get("weights")
        clean = (
            {k: float(v) for k, v in weights.items() if isinstance(k, str) and _is_number(v)}
            if isinstance(weights, dict)
            else {}
        )
        families = [f for f in raw.get("recent") or [] if f in FAMILIES][-MAX_RECENT:]
        offered = tuple(f for f in raw.get("offered") or [] if f in FAMILIES)
        pending = raw.get("pending")
        return Episode(
            skill=raw["skill"],
            posterior=Posterior.from_mapping(clean) if clean else None,
            guidance=Guidance.from_payload(raw.get("guidance")),
            recent=tuple(families),
            offered=offered,
            pending=pending if pending in FAMILIES else None,
        )


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _confident(confidence: Confidence | None) -> bool | None:
    return None if confidence is None else confidence == "sure"


def after_answer(
    prev: Episode | None,
    skill: str,
    *,
    correct: bool,
    hinted: bool,
    confidence: Confidence | None,
    assessment: Assessment | None,
) -> tuple[Episode, dict[str, Any] | None]:
    """The episode after an answer, and the effect row for the help chosen before it, if any."""
    base = prev if prev is not None and prev.skill == skill else Episode(skill)
    guidance = advance(
        base.guidance, correct=correct, hinted=hinted, confident=_confident(confidence)
    )
    effect = {"family": base.pending, "correct": correct} if base.pending else None
    if correct or assessment is None:
        return Episode(skill, None, guidance, base.recent, (), None), effect
    cause = assessment.view.cause
    offered = offer(cause_kind(cause) if cause else "other", recent=base.recent)
    return Episode(skill, assessment.posterior, guidance, base.recent, offered, None), effect


def after_correction(ep: Episode, diagnosed_kind: str) -> Episode:
    """ "That's not why": lower the leading cause of the kind the learner disagreed with."""
    if ep.posterior is None:
        return ep
    named = [c for c, _ in ep.posterior.weights if cause_kind(c) == diagnosed_kind]
    if not named:
        return ep
    lowered = apply_correction(ep.posterior, named[0])
    lead = view(lowered).cause
    offered = offer(cause_kind(lead) if lead else "other", recent=ep.recent)
    return Episode(ep.skill, lowered, ep.guidance, ep.recent, offered, ep.pending)


def after_move(ep: Episode, family: str) -> Episode:
    """The learner chose a kind of help; remember it and wait to see how the next answer goes."""
    if family not in FAMILIES:
        return ep
    recent = (*ep.recent, family)[-MAX_RECENT:]
    return Episode(ep.skill, ep.posterior, ep.guidance, recent, ep.offered, family)


def public(ep: Episode) -> dict[str, Any] | None:
    """What the learner's screen may use after a wrong answer: no labels, only how to help."""
    if ep.posterior is None:
        return None
    seen = view(ep.posterior)
    return {
        "band": seen.band,
        "cause": seen.cause,
        "rivals": list(seen.rivals),
        "offer": list(ep.offered),
        "level": ep.guidance.level,
    }
