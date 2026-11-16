# ruff: noqa: E501
"""Shared helpers for the maths-lane tests."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from app.factory.kernel.certify import box_axes
from app.factory.lanes.maths.catalog import all_templates
from app.factory.lanes.maths.lane import LANE

REPO = Path(__file__).resolve().parents[6]
CONTENT = REPO / "content" / "cbse" / "10" / "maths"


def tuples(template: dict[str, Any], n: int, seed: int = 3) -> list[dict[str, Any]]:
    """Up to n well-posed parameter tuples of a template, in a seeded order."""
    axes = box_axes(template["box"])
    total = 1
    for _, values in axes:
        total *= len(values)
    rng = random.Random(seed)
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for _ in range(6000):
        index = rng.randrange(total)
        if index in seen:
            continue
        seen.add(index)
        params: dict[str, Any] = {}
        rest = index
        for name, values in reversed(axes):
            rest, pos = divmod(rest, len(values))
            params[name] = values[pos]
        if LANE.well_posed(template, params) is None:
            out.append(params)
            if len(out) == n:
                break
    return out


TEMPLATES = all_templates()
