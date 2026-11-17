"""The legacy fixed-order placement planner, re-implemented from `orchestrator/diagnostic.py`.

Fixed topological order, one item per skill; a second item only when the first was wrong and every
prerequisite's first answer was right; two misses on a skill skip all its dependents; at most 16
items (`DIAG_ITEM_CAP`). Estimate: known if any answer was right, skipped dependents not known,
untested skills 0.2. Kept here, not imported, so the comparison survives edits to the real file.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.learner.probe.sim import Rng, SimRun, score_marginals, start_is_ready
from app.learner.probe.space import implied_prerequisites
from app.learner.probe.types import ProbeItem, Space

LEGACY_CAP = 16  # DIAG_ITEM_CAP
UNTESTED = 0.2


def dependents(skill: str, prerequisites: Mapping[str, Sequence[str]]) -> set[str]:
    found = {skill}
    changed = True
    while changed:
        changed = False
        for sid, pres in prerequisites.items():
            if sid not in found and any(p in found for p in pres):
                found.add(sid)
                changed = True
    found.discard(skill)
    return found


def run_legacy(
    space: Space,
    truth: int,
    items: Sequence[ProbeItem],
    prerequisites: Mapping[str, Sequence[str]],
    rng: Rng,
) -> SimRun:
    pool: dict[str, list[ProbeItem]] = {}
    for it in items:
        pool.setdefault(it.skill_id, []).append(it)
    first: dict[str, bool] = {}
    est: dict[str, float] = {}
    skipped: set[str] = set()
    asked = 0

    def ask(skill: str, n: int) -> bool:
        item = pool[skill][n]
        known = bool(truth >> space.index(skill) & 1)
        return rng.random() < (1.0 - item.slip if known else item.guess)

    for skill in space.skills:
        if skill in skipped or asked >= LEGACY_CAP:
            continue
        results = [ask(skill, 0)]
        asked += 1
        prereqs_ok = all(first.get(p, False) for p in prerequisites.get(skill, ()))
        if not results[0] and prereqs_ok and asked < LEGACY_CAP and len(pool[skill]) > 1:
            results.append(ask(skill, 1))
            asked += 1
        first[skill] = results[0]
        est[skill] = 1.0 if any(results) else 0.0
        if len(results) == 2 and not any(results):
            for dep in dependents(skill, prerequisites):
                skipped.add(dep)
                est[dep] = 0.0
    marks = {s: est.get(s, UNTESTED) for s in space.skills}
    needs = implied_prerequisites(space)
    n = len(space.skills)
    fringe = [
        (space.depth[i], s)
        for i, s in enumerate(space.skills)
        if marks[s] < 0.5
        and all(marks[space.skills[j]] >= 0.5 for j in range(n) if needs[i] >> j & 1)
    ]
    start = min(fringe)[1] if fringe else None
    return SimRun(
        truth,
        asked,
        "legacy",
        marks,
        start,
        score_marginals(space, truth, marks),
        start_is_ready(space, truth, start),
    )
