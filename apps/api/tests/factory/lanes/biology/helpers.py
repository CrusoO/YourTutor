"""Shared helpers: find well-posed tuples and make small boxes for the biology lane tests."""

from __future__ import annotations

import copy
import functools
import itertools
from typing import Any

from app.factory.kernel.certify import box_axes
from app.factory.lanes.biology.lane import LANE
from app.factory.lanes.biology.models import ALL_MODELS
from app.factory.lanes.biology.templates import all_templates

TEMPLATES = all_templates()


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
    out = []
    for mid, model in ALL_MODELS.items():
        variants = model.box.get("variant") or ("",)
        out += [(mid, v) for v in variants]
    return out


def key_of(model_id: str, **params: str) -> str:
    """The key option text of the item at `params` (other axes take the first value that works)."""
    tpl = TEMPLATES[model_id]
    axes = [n for n, _ in box_axes(tpl["box"])]
    fixed = {k: v for k, v in params.items() if k in axes}
    ctx = LANE.render(tpl, first(model_id, **fixed))
    return str(next(o["text"] for o in ctx.options if o["id"] == "key"))


def small_template(model_id: str, **choices: list[str]) -> dict[str, Any]:
    """The real template with the named axes cut down to the given choices."""
    tpl = copy.deepcopy(TEMPLATES[model_id])
    for name, values in choices.items():
        tpl["box"][name] = {"choices": list(values)}
    return tpl
