"""Item selection by expected information gain (spec section 3)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from app.learner.probe.types import Belief, ProbeConfig, ProbeItem


def marginals(belief: Belief) -> dict[str, float]:
    """P(skill known) for every skill in the space."""
    out = {}
    for i, skill in enumerate(belief.space.skills):
        out[skill] = min(
            1.0, sum(w for w, s in zip(belief.weights, belief.space.states) if s >> i & 1)
        )
    return out


def _entropy(weights: Sequence[float]) -> float:
    return -sum(w * math.log2(w) for w in weights if w > 0.0)


def _p_correct(known_mass: float, item: ProbeItem) -> float:
    return known_mass * (1.0 - item.slip) + (1.0 - known_mass) * item.guess


def expected_gain(belief: Belief, item: ProbeItem) -> float:
    """Expected drop in entropy over states, in bits, from asking `item` (always >= 0).

    "I don't know" is not modelled here: for selection it is treated like a wrong answer.
    """
    space = belief.space
    bit = 1 << space.index(item.skill_id)
    known = [bool(s & bit) for s in space.states]
    known_mass = sum(w for w, k in zip(belief.weights, known) if k)
    p_right = _p_correct(known_mass, item)
    after = 0.0
    for p_ans, lk, lu in (
        (p_right, 1.0 - item.slip, item.guess),
        (1.0 - p_right, item.slip, 1.0 - item.guess),
    ):
        if p_ans <= 0.0:
            continue
        post = [w * (lk if k else lu) / p_ans for w, k in zip(belief.weights, known)]
        after += p_ans * _entropy(post)
    return max(0.0, _entropy(belief.weights) - after)


def choose_item(
    belief: Belief,
    items: Sequence[ProbeItem],
    used: frozenset[str],
    skill_counts: Mapping[str, int],
    last_was_mcq: bool,
    cfg: ProbeConfig,
) -> ProbeItem | None:
    """The eligible item with the largest gain; ties by lower guess, then item id.

    Eligible: not used, skill in the space, under `max_per_skill`, and not a second MCQ in a row.
    For the first `opener_items` questions, items the student probably gets right (belief says
    P(correct) >= `opener_min_success`) are preferred, when any exist ("confidence opener").
    """
    skills = set(belief.space.skills)
    eligible = [
        it
        for it in items
        if it.item_id not in used
        and it.skill_id in skills
        and skill_counts.get(it.skill_id, 0) < cfg.max_per_skill
        and not (last_was_mcq and it.is_mcq)
    ]
    if not eligible:
        return None
    if len(used) < cfg.opener_items:
        mass = marginals(belief)
        easy = [
            it for it in eligible if _p_correct(mass[it.skill_id], it) >= cfg.opener_min_success
        ]
        eligible = easy or eligible
    cache: dict[tuple[str, float, float], float] = {}

    def key(it: ProbeItem) -> tuple[float, float, str]:
        k = (it.skill_id, it.slip, it.guess)
        if k not in cache:
            cache[k] = expected_gain(belief, it)
        return (-round(cache[k], 12), it.guess, it.item_id)

    return min(eligible, key=key)
