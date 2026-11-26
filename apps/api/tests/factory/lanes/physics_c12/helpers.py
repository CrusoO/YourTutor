"""Shared helpers: find well-posed tuples and make small boxes for the physics lane tests."""

from __future__ import annotations

import copy
import functools
import itertools
from typing import Any

from app.factory.kernel.certify import box_axes
from app.factory.lanes.physics_c12.lane import LANE
from app.factory.lanes.physics_c12.models import ALL_MODELS
from app.factory.lanes.physics_c12.templates import TEMPLATES


def tuples(model_id: str, limit: int | None = None, **fixed: Any):
    tpl = TEMPLATES[model_id]
    axes = box_axes(tpl["box"])
    count = 0
    for combo in itertools.product(*[v for _, v in axes]):
        params = {n: c for (n, _), c in zip(axes, combo, strict=True)}
        if any(params.get(k) != v for k, v in fixed.items()):
            continue
        if LANE.well_posed(tpl, params) is None:
            yield params
            count += 1
            if limit and count >= limit:
                return


@functools.cache
def _first(model_id: str, fixed: tuple[tuple[str, Any], ...]) -> tuple[tuple[str, Any], ...]:
    return tuple(next(tuples(model_id, 1, **dict(fixed))).items())


def first(model_id: str, **fixed: Any) -> dict[str, Any]:
    return dict(_first(model_id, tuple(sorted(fixed.items()))))


def all_variant_cases() -> list[tuple[str, str]]:
    return [(m, v) for m, model in ALL_MODELS.items() for v in model.variants]


def small_template(model_id: str, per_axis: int = 2) -> dict[str, Any]:
    """The real template with each axis cut to its first values (variant and form kept whole)."""
    tpl = copy.deepcopy(TEMPLATES[model_id])
    for name, spec in tpl["box"].items():
        if name not in ("variant", "form") and len(spec["choices"]) > per_axis:
            spec["choices"] = spec["choices"][:per_axis]
    return tpl
