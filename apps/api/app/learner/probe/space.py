"""Knowledge states: subsets of skills closed under prerequisites, as int bitmasks.

Bit i of a state is set when `skills[i]` is known. A state is closed when every known skill has all
its prerequisites known too. Prerequisites that are not in the probe skill set are ignored.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from app.learner.probe.types import Space, TooManyStates


def _dedupe(items: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def _edges(
    skills: tuple[str, ...], prerequisites: Mapping[str, Sequence[str]]
) -> list[tuple[int, ...]]:
    """Per skill index, its sorted distinct in-set prerequisite indices."""
    index = {s: i for i, s in enumerate(skills)}
    return [
        tuple(sorted({index[p] for p in prerequisites.get(s, ()) if p in index})) for s in skills
    ]


def _order_and_depth(prereqs: list[tuple[int, ...]]) -> tuple[list[int], list[int]]:
    """Topological order (prerequisites first) and longest prerequisite path per skill."""
    n = len(prereqs)
    depth = [0] * n
    color = [0] * n  # 0 unseen, 1 in progress, 2 done
    order: list[int] = []

    def visit(i: int) -> None:
        color[i] = 1
        for p in prereqs[i]:
            if color[p] == 1:
                raise ValueError("prerequisite graph has a cycle")
            if color[p] == 0:
                visit(p)
            depth[i] = max(depth[i], depth[p] + 1)
        color[i] = 2
        order.append(i)

    for i in range(n):
        if color[i] == 0:
            visit(i)
    return order, depth


def build_space(
    skills: Sequence[str], prerequisites: Mapping[str, Sequence[str]], *, max_states: int
) -> Space:
    """Enumerate every prerequisite-closed state by depth-first search.

    Raises ValueError on a cycle and `TooManyStates` above `max_states` (the caller shrinks).
    """
    names = _dedupe(skills)
    prereqs = _edges(names, prerequisites)
    order, depth = _order_and_depth(prereqs)
    need = [sum(1 << p for p in ps) for ps in prereqs]
    states: list[int] = []

    def walk(pos: int, mask: int) -> None:
        if pos == len(order):
            if len(states) >= max_states:
                raise TooManyStates(f"more than {max_states} closed states")
            states.append(mask)
            return
        i = order[pos]
        walk(pos + 1, mask)  # skill i unknown
        if mask & need[i] == need[i]:
            walk(pos + 1, mask | (1 << i))  # skill i known: its prerequisites already are

    walk(0, 0)
    canon = (
        "|".join(names)
        + ";"
        + ";".join(f"{names[p]}>{names[i]}" for i, ps in enumerate(prereqs) for p in ps)
    )
    graph_hash = hashlib.sha256(canon.encode()).hexdigest()[:16]
    return Space(names, tuple(sorted(states)), tuple(depth), graph_hash)


def implied_prerequisites(space: Space) -> tuple[int, ...]:
    """Per skill, the bitmask of all (transitive) prerequisites, read back from the states."""
    full = (1 << len(space.skills)) - 1
    out = []
    for i in range(len(space.skills)):
        mask = full
        for state in space.states:
            if state >> i & 1:
                mask &= state
        out.append(mask & ~(1 << i))
    return tuple(out)


def shrink_skills(
    target: Sequence[str],
    prerequisites: Mapping[str, Sequence[str]],
    *,
    levels: int,
    cap: int,
) -> tuple[str, ...]:
    """The target skills plus ancestors within `levels` steps, nearest first, at most `cap`."""
    if cap < 1 or levels < 0:
        raise ValueError("cap must be at least 1 and levels non-negative")
    chosen = list(_dedupe(target))
    seen = set(chosen)
    frontier = list(chosen)
    for _ in range(levels):
        nxt = sorted({p for s in frontier for p in prerequisites.get(s, ())} - seen)
        chosen.extend(nxt)
        seen.update(nxt)
        frontier = nxt
        if not frontier:
            break
    return tuple(chosen[:cap])
