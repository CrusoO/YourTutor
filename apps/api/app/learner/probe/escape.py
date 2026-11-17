"""Escape hatches as pure functions (spec section 6). Nothing here is wired to the app yet.

A tap is a claim, never evidence: it changes the mixture (how likely a strong or weak student is)
or ends the probe, and the next items verify it. No function here writes a mastery value, and
"too hard" never marks a skill failed: unresolved skills stay "unclear" (unknown, not failed).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from app.learner.probe.prior import _apply_floor, initial_belief
from app.learner.probe.result import NOT_KNOWN, summarise
from app.learner.probe.space import build_space, implied_prerequisites, shrink_skills
from app.learner.probe.types import Belief, ProbeConfig, ProbeResult, Space

STUDENT_STOP = "student_stop"
TOO_EASY_FACTOR = 3.0  # TUNABLE-DEFAULT: the high-base component is multiplied by this
JUMP_ANCESTOR_LEVELS = 2  # target plus ancestors within 2 levels
JUMP_MAX_SKILLS = 8
JUMP_MAX_ITEMS = 4

Claim = Literal["too_easy", "too_hard"]


def apply_claim(belief: Belief, claim: Claim, cfg: ProbeConfig) -> Belief:
    """ "Too easy" multiplies the high-base mixture component by 3 (renormalised, floored at
    `mixture_floor`); the claim is then checked by items chosen by the usual information gain.
    "Too hard" changes no belief: it ends the probe (see `stop_on_request`)."""
    if claim == "too_hard":
        return belief
    if claim != "too_easy":
        raise ValueError(f"unknown claim {claim!r}")
    high = max(range(len(cfg.prior_bases)), key=lambda c: cfg.prior_bases[c])
    raw = [m * (TOO_EASY_FACTOR if c == high else 1.0) for c, m in enumerate(belief.mixture)]
    target = _apply_floor(raw, cfg.mixture_floor)
    joint = [[w * target[c] / belief.mixture[c] for w in row] for c, row in enumerate(belief.joint)]
    return Belief.from_joint(belief.space, joint, belief.reset)


def stop_on_request(
    belief: Belief, asked: int, cfg: ProbeConfig, chapter_order: Sequence[str]
) -> ProbeResult:
    """ "That's enough" / "too hard": stop now with reason `student_stop`. Unresolved skills keep
    the label "unclear" (never "not_known" by this tap); `start_skill` is the first ready one."""
    return summarise(belief, asked, STUDENT_STOP, cfg, chapter_order)


def ancestors_space(
    target: str, prerequisites: Mapping[str, Sequence[str]], cfg: ProbeConfig
) -> Space:
    """The mini probe space for "jump here": the target plus ancestors within 2 levels, at most 8
    skills (nearest first)."""
    skills = shrink_skills(
        [target], prerequisites, levels=JUMP_ANCESTOR_LEVELS, cap=JUMP_MAX_SKILLS
    )
    return build_space(skills, prerequisites, max_states=cfg.max_states)


def jump_belief(
    target: str,
    prerequisites: Mapping[str, Sequence[str]],
    cfg: ProbeConfig,
    previous: Belief | None = None,
) -> Belief:
    """A fresh belief over `ancestors_space(target)`, carrying over the mixture posterior of any
    earlier probe (what we learned about the student's rough level)."""
    space = ancestors_space(target, prerequisites, cfg)
    return initial_belief(space, cfg, None if previous is None else previous.mixture)


@dataclass(frozen=True)
class JumpAdvice:
    """Advice after the mini probe. The student may always ignore it and start at the target."""

    target: str
    start_at_target: bool
    first_gap: str | None  # the shallowest ancestor judged not known, when there is one


def jump_advice(result: ProbeResult, target: str, space: Space) -> JumpAdvice:
    """Start at the target if its prerequisites resolve known or unclear; otherwise offer the first
    gap (lowest depth, ties by id) first."""
    i = space.index(target)
    need = implied_prerequisites(space)[i]
    gaps = [
        (space.depth[j], skill)
        for j, skill in enumerate(space.skills)
        if need >> j & 1 and result.labels[skill] == NOT_KNOWN
    ]
    if not gaps:
        return JumpAdvice(target, True, None)
    return JumpAdvice(target, False, min(gaps)[1])
