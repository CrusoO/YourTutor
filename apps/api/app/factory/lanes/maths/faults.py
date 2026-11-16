# ruff: noqa: E501
"""Fault injection for the maths lane: seeded wrong items that every checker must reject.

Generic fault classes come from app.factory.faults (sign flip, dropped root, swapped option,
duplicate distractor, hint leak, a wrong method, methods that are not independent). The lane adds
the slips its own families can make: a model parameter that disagrees with the answer, an answer
that is off by one, a surd answer with the wrong radical, and an angle slip in a trig model.

A mutant must be WRONG by construction. Mutators that could produce a still-correct item (a
sign flip of a symmetric root pair, for example) drop such mutants instead of counting them.
"""

from __future__ import annotations

import copy
import random
from collections.abc import Callable
from fractions import Fraction
from typing import Any

from app.factory import faults as generic
from app.factory.faults import Fault, FaultReport, run_fault_injection
from app.factory.kernel.certify import box_axes
from app.factory.kernel.exact import chash, frac, is_number_text
from app.factory.registry import ItemContext


def _witness_key(w: dict[str, Any]) -> Any:
    split = w.get("split")
    if split:
        return (str(split["lead"]), sorted((str(r), int(m)) for r, m in split["roots"]))
    return chash(w)


def _wrong_only(mutator: Callable[[ItemContext], list[ItemContext]]):  # type: ignore[no-untyped-def]
    """Keep only mutants that really differ from the original item."""

    def run(ctx: ItemContext) -> list[ItemContext]:
        keep = []
        for m in mutator(ctx):
            same = chash(m.answer) == chash(ctx.answer) and _witness_key(m.witness) == _witness_key(
                ctx.witness
            )
            if not same:
                keep.append(m)
        return keep

    return run


def _set_answer(ctx: ItemContext, answer: dict[str, Any]) -> ItemContext:
    out = copy.deepcopy(ctx)
    out.answer = answer
    for option in out.options:
        if option["id"] == out.key_option:
            option["value"] = copy.deepcopy(answer)
    return out


def off_by_one_answer(ctx: ItemContext) -> list[ItemContext]:
    """A scalar answer one too big (a classic count slip), key option moved with it."""
    roots = ctx.answer.get("roots")
    if not roots or len(roots) != 1 or ctx.spec.get("kind") != "polynomial":
        return []
    bumped = str(frac(roots[0]) + 1)
    changed = {**ctx.answer, "roots": [bumped]}
    if "value" in changed and is_number_text(changed["value"]):
        changed["value"] = bumped
    return [_set_answer(ctx, changed)]


def _roots_sign_flip(ctx: ItemContext) -> list[ItemContext]:
    """Sign flip of a root set (the kernel substitutes every claimed root into the equation)."""
    return generic.sign_flip(ctx) if ctx.answer.get("roots") else []


def value_sign_flip(ctx: ItemContext) -> list[ItemContext]:
    """Sign flip of a value the kernel cannot see (it checks a linear system, not the value)."""
    if ctx.answer.get("roots") or "value" not in ctx.answer:
        return []
    if not is_number_text(ctx.answer["value"]) or frac(ctx.answer["value"]) == 0:
        return []
    return [_set_answer(ctx, {**ctx.answer, "value": str(-frac(ctx.answer["value"]))})]


def model_tamper(ctx: ItemContext) -> list[ItemContext]:
    """A parameter of the structured model changed while the answer stays: the methods disagree."""
    model = ctx.spec.get("model", {})
    out = []
    if (
        model.get("family") == "tri_complement"
    ):  # the identity's value ignores the angle: swap the kind
        mutant = copy.deepcopy(ctx)
        mutant.spec["model"]["kind"] = "difference" if model["kind"] != "difference" else "product"
        return [mutant]
    for key, value in model.items():
        if isinstance(value, int) and not isinstance(value, bool) and key not in ("pw",):
            mutant = copy.deepcopy(ctx)
            mutant.spec["model"][key] = value + (1 if value >= 0 else -1)
            try:  # a tamper that leaves the answer unchanged is not a fault: try the next parameter
                same = chash(ctx.methods[0].solve(mutant.spec)) == chash(ctx.answer)
            except Exception:  # noqa: BLE001 - a method that errors has noticed the tamper
                same = False
            if same:
                continue
            out.append(mutant)
            break  # one mutant per case is enough to prove the point
    return out


def surd_radical_slip(ctx: ItemContext) -> list[ItemContext]:
    """The surd answer written with the wrong multiple (the kernel cannot see the value text)."""
    value = ctx.answer.get("value")
    if ctx.answer.get("count") != 2 or "roots" in ctx.answer or not isinstance(value, str):
        return []
    if "√3" not in value:
        return []
    return [_set_answer(ctx, {**ctx.answer, "value": value.replace("√3", "√3/3", 1)})]


def angle_slip(ctx: ItemContext) -> list[ItemContext]:
    """Degree slip in a trigonometry model: an angle moved to a different standard angle."""
    model = ctx.spec.get("model", {})
    out = []
    if isinstance(model.get("angle"), int):
        mutant = copy.deepcopy(ctx)
        mutant.spec["model"]["angle"] = {30: 60, 60: 30, 45: 30}[model["angle"]]
        out.append(mutant)
    if isinstance(model.get("angles"), list):
        mutant = copy.deepcopy(ctx)
        mutant.spec["model"]["angles"] = list(reversed(model["angles"]))
        mutant.spec["model"]["angles"][0] = {30: 45, 45: 30, 60: 45}[
            mutant.spec["model"]["angles"][0]
        ]
        out.append(mutant)
    return out


LANE_FAULTS: tuple[Fault, ...] = (
    Fault(
        "sign_flip", "root sign flipped", _wrong_only(_roots_sign_flip), ("wellposed.predicates",)
    ),
    Fault(
        "value_sign_flip",
        "value the kernel cannot see flipped",
        value_sign_flip,
        ("verify.method_1",),
    ),
    Fault(
        "dropped_root",
        "a root dropped",
        _wrong_only(generic.dropped_root),
        ("wellposed.predicates",),
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
        "off_by_one_answer",
        "scalar answer one too big",
        off_by_one_answer,
        ("wellposed.predicates", "verify.method_1"),
    ),
    Fault(
        "model_tamper",
        "model parameter disagrees with the answer",
        model_tamper,
        ("verify.method_1",),
    ),
    Fault(
        "surd_radical_slip",
        "surd answer with the wrong radical",
        surd_radical_slip,
        ("verify.method_1",),
    ),
    Fault("angle_slip", "angle slip in a trig model", angle_slip, ("verify.method_1",)),
)


def corpus(per_template: int = 2, seed: int = 7) -> list[ItemContext]:
    """Known-good items: a few well-posed tuples from every template, chosen by seed."""
    from app.factory.lanes.maths.catalog import all_templates
    from app.factory.lanes.maths.lane import LANE

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
                from app.content.originality import ReferenceIndex

                ctx.reference_index = ReferenceIndex()
                cases.append(ctx)
                picked += 1
                if picked == per_template:
                    break
    return cases


def run_lane_fault_injection(per_template: int = 2, seed: int = 7) -> FaultReport:
    return run_fault_injection(corpus(per_template, seed), LANE_FAULTS)


__all__ = ["LANE_FAULTS", "corpus", "run_lane_fault_injection", "Fraction"]
