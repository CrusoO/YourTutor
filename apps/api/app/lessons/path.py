"""R38 lesson path: which of a lesson's beats a student is served, and in what order.

Pure. A student whose prerequisites are all at ladder level 4 or more is "ready" and gets the
problem-first order (predict, explore, explain scene, worked example, check). Anyone else gets
worked-example-first: the explore and scene beats before the first worked example are skipped.
Beats after the worked example (such as a second explore) stay.
A lesson with no worked-example beat is served whole, so the student is never left without one.
The beats keep their authored order, and predict stays first and check last.
"""

from __future__ import annotations

from collections.abc import Sequence

READY_LEVEL = 4  # every prerequisite at this ladder level or more
SKIPPED_FOR_NOVICE = frozenset({"explore", "explain_scene"})


def lesson_path(
    prerequisite_levels: Sequence[int], beat_kinds: Sequence[str]
) -> tuple[str, list[str]]:
    """The order name and the beat kinds to serve."""
    ready = all(level >= READY_LEVEL for level in prerequisite_levels)
    if ready or "worked_example" not in beat_kinds:
        return ("problem_first" if ready else "worked_example_first"), list(beat_kinds)
    first_example = list(beat_kinds).index("worked_example")
    serve = [
        k for i, k in enumerate(beat_kinds) if i > first_example or k not in SKIPPED_FOR_NOVICE
    ]
    return "worked_example_first", serve
