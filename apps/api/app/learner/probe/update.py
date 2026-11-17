"""Evidence: likelihood of one answer, and the Bayes update of a belief (spec section 3).

The posterior already contains slip and guess, so no separate BKT formula is applied on top.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace

from app.learner.probe.prior import initial_belief
from app.learner.probe.types import Answer, Belief, ProbeConfig, ProbeItem

FLOOR = 1e-12  # no state ever becomes impossible
_MIN_TOTAL = 1e-300


def item_params(
    item_id: str,
    skill_id: str,
    cfg: ProbeConfig,
    *,
    options: int | None = None,
    multistep: bool = False,
) -> ProbeItem:
    """Slip and guess for a catalog item: typed 0.05; MCQ with k options is 1/k, clipped."""
    if options is None:
        guess = cfg.guess_typed
    elif options < 2:
        raise ValueError("an MCQ has at least two options")
    else:
        guess = min(cfg.guess_mcq_cap, max(cfg.guess_mcq_floor, 1.0 / options))
    slip = cfg.slip_multistep if multistep else cfg.slip
    return ProbeItem(item_id, skill_id, guess, slip, options is not None)


def likelihood(item: ProbeItem, answer: Answer, cfg: ProbeConfig) -> tuple[float, float]:
    """(P(answer | skill known), P(answer | skill unknown)).

    "I don't know" is strong evidence of not known. A rapid or unsure *correct* answer is weak
    evidence (guess raised to `guess_uncertain`); time never lowers an estimate on its own.
    """
    if answer.dont_know:
        return cfg.idk_known, cfg.idk_unknown
    if not answer.correct:
        return item.slip, 1.0 - item.guess
    guess = item.guess
    if answer.rapid or answer.unsure:
        guess = max(guess, cfg.guess_uncertain)
    guess = min(guess, 1.0 - item.slip - 0.05)  # keep slip + guess below 1 (monotone evidence)
    return 1.0 - item.slip, max(guess, item.guess)


def update(belief: Belief, item: ProbeItem, answer: Answer, cfg: ProbeConfig) -> Belief:
    """A new belief after one answer; the input is never changed."""
    if answer.item_id != item.item_id or answer.skill_id != item.skill_id:
        raise ValueError("answer does not match the item it is applied to")
    space = belief.space
    bit = 1 << space.index(item.skill_id)
    known, unknown = likelihood(item, answer, cfg)
    factor = [known if s & bit else unknown for s in space.states]
    joint = [[w * f for w, f in zip(row, factor, strict=True)] for row in belief.joint]
    top = max(max(row) for row in joint)
    if not math.isfinite(top) or top < _MIN_TOTAL:
        return replace(initial_belief(space, cfg), reset=True)
    joint = [[w / top for w in row] for row in joint]
    total = sum(sum(row) for row in joint)
    joint = [[max(FLOOR, w / total) for w in row] for row in joint]
    total = sum(sum(row) for row in joint)
    joint = [[w / total for w in row] for row in joint]
    return Belief.from_joint(space, joint, belief.reset)


def apply_answers(
    belief: Belief, items: Sequence[ProbeItem], answers: Sequence[Answer], cfg: ProbeConfig
) -> Belief:
    """Fold a list of answers (with their items, in order) into a belief."""
    if len(items) != len(answers):
        raise ValueError("items and answers must have the same length")
    for item, answer in zip(items, answers, strict=True):
        belief = update(belief, item, answer, cfg)
    return belief
