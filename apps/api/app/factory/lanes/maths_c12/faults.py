# ruff: noqa: E501
"""Fault injection for the Class 12 maths lane: seeded wrong items that every checker must reject.

The generic classes (sign flip, swapped option, duplicate distractor, hint leak, a wrong method,
methods that are not independent) come from app.factory.faults. The lane adds the slips its models
can make: a vector or matrix component off by one, a scalar off by one, and a model parameter that
disagrees with the stored answer (so the independent methods must notice). A mutant must be WRONG
by construction; mutators drop any mutant that happens to equal the original.
"""

from __future__ import annotations

import random
from typing import Any

from app.content.originality import ReferenceIndex
from app.factory import faults as generic
from app.factory.faults import Fault, FaultReport, run_fault_injection
from app.factory.kernel.certify import box_axes
from app.factory.kernel.exact import frac
from app.factory.lanes.maths.faults import (
    _roots_sign_flip,
    _set_answer,
    _wrong_only,
    model_tamper,
    off_by_one_answer,
)
from app.factory.registry import ItemContext


def component_slip(ctx: ItemContext) -> list[ItemContext]:
    """One component of a vector or matrix answer is one too big, the key option moved with it."""
    values = ctx.answer.get("values")
    if not values:
        return []
    first = next(iter(values))
    changed = {"values": {**values, first: str(frac(values[first]) + 1)}}
    return [_set_answer(ctx, changed)]


def component_swap(ctx: ItemContext) -> list[ItemContext]:
    """Two different components of a vector or matrix answer exchanged (a layout slip)."""
    values = ctx.answer.get("values")
    if not values or len(set(values.values())) < 2:
        return []
    keys = list(values)
    i = next(j for j in range(1, len(keys)) if values[keys[j]] != values[keys[0]])
    swapped = dict(values)
    swapped[keys[0]], swapped[keys[i]] = values[keys[i]], values[keys[0]]
    return [_set_answer(ctx, {"values": swapped})]


LANE_FAULTS: tuple[Fault, ...] = (
    Fault(
        "sign_flip",
        "scalar answer sign flipped",
        _wrong_only(_roots_sign_flip),
        ("wellposed.predicates",),
    ),
    Fault(
        "off_by_one_answer",
        "scalar answer one too big",
        off_by_one_answer,
        ("wellposed.predicates", "verify.method_1"),
    ),
    Fault(
        "component_slip",
        "one component one too big",
        component_slip,
        ("wellposed.predicates", "verify.method_1"),
    ),
    Fault(
        "component_swap",
        "two components exchanged",
        component_swap,
        ("wellposed.predicates", "verify.method_1"),
    ),
    Fault(
        "swapped_option",
        "key moved to a wrong option",
        generic.swapped_option,
        ("answer.key_consistency",),
    ),
    Fault(
        "distractor_equals_key",
        "a distractor equals the key",
        generic.distractor_equals_key,
        ("mcq.distractors",),
    ),
    Fault(
        "duplicate_distractor",
        "two distractors identical",
        generic.duplicate_distractor,
        ("mcq.distractors",),
    ),
    Fault("hint_leaks_key", "hint 1 states the answer", generic.hint_leaks_key, ("leak.hints",)),
    Fault(
        "method_wrong_answer",
        "method 1 returns a wrong answer",
        generic.method_wrong_answer,
        ("verify.method_1",),
    ),
    Fault(
        "single_group",
        "methods share the kernel group",
        generic.single_group,
        ("verify.methods_2n",),
    ),
    Fault(
        "model_tamper",
        "model parameter disagrees with the answer",
        model_tamper,
        ("verify.method_1",),
    ),
)


def corpus(per_template: int = 2, seed: int = 7) -> list[ItemContext]:
    """Known-good items: a few well-posed tuples from every template, chosen by seed."""
    from app.factory.lanes.maths_c12.lane import LANE
    from app.factory.lanes.maths_c12.template import all_templates

    cases: list[ItemContext] = []
    rng = random.Random(seed)
    for t in all_templates():
        axes = box_axes(t["box"])
        total = 1
        for _, vals in axes:
            total *= len(vals)
        picked = 0
        for _ in range(4000):
            index = rng.randrange(total)
            params: dict[str, Any] = {}
            rest = index
            for name, vals in reversed(axes):
                rest, pos = divmod(rest, len(vals))
                params[name] = vals[pos]
            if LANE.well_posed(t, params) is None:
                ctx = LANE.render(t, params)
                ctx.reference_index = ReferenceIndex()
                cases.append(ctx)
                picked += 1
                if picked == per_template:
                    break
    return cases


def run_lane_fault_injection(per_template: int = 2, seed: int = 7) -> FaultReport:
    return run_fault_injection(corpus(per_template, seed), LANE_FAULTS)


__all__ = ["LANE_FAULTS", "corpus", "run_lane_fault_injection"]
