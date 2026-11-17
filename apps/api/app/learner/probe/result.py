"""Turn a final belief into a placement result and mastery seeds (spec section 3)."""

from __future__ import annotations

from collections.abc import Sequence

from app.learner.probe.select import marginals
from app.learner.probe.space import implied_prerequisites
from app.learner.probe.types import Belief, ProbeConfig, ProbeResult

KNOWN = "known"
NOT_KNOWN = "not_known"
UNCLEAR = "unclear"


def _label(m: float, cfg: ProbeConfig) -> str:
    if m >= cfg.resolve_hi:
        return KNOWN
    if m <= cfg.resolve_lo:
        return NOT_KNOWN
    return UNCLEAR


def summarise(
    belief: Belief,
    asked: int,
    stop_reason: str,
    cfg: ProbeConfig,
    chapter_order: Sequence[str],
) -> ProbeResult:
    """Marginals, labels and the outer fringe: skills not yet known whose prerequisites are.

    `start_skill` is the fringe skill with the lowest depth, ties by `chapter_order` (skills missing
    from it come last, by id).
    """
    space = belief.space
    marks = marginals(belief)
    needs = implied_prerequisites(space)
    rank = {s: i for i, s in enumerate(chapter_order)}
    ready = []
    for i, skill in enumerate(space.skills):
        if marks[skill] >= 0.5:
            continue
        if all(
            marks[space.skills[j]] >= 0.5 for j in range(len(space.skills)) if needs[i] >> j & 1
        ):
            ready.append((space.depth[i], rank.get(skill, len(rank)), skill))
    ready.sort()
    fringe = tuple(skill for _, _, skill in ready)
    return ProbeResult(
        marginals=marks,
        labels={s: _label(m, cfg) for s, m in marks.items()},
        start_skill=fringe[0] if fringe else None,
        ready_skills=fringe,
        asked=asked,
        stop_reason=stop_reason,
        mixture=belief.mixture,
        belief_reset=belief.reset,
    )


def to_mastery_seed(result: ProbeResult, cfg: ProbeConfig) -> dict[str, float]:
    """Starting `p_known` per skill: known and not-known clamp to [seed_floor, seed_cap]; unclear
    skills use their marginal clipped to [unclear_lo, unclear_hi]. A placement is never proof."""
    seeds = {}
    for skill, m in result.marginals.items():
        if result.labels[skill] == UNCLEAR:
            seeds[skill] = min(cfg.unclear_hi, max(cfg.unclear_lo, m))
        else:
            seeds[skill] = min(cfg.seed_cap, max(cfg.seed_floor, m))
    return seeds
