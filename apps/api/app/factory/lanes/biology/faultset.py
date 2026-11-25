"""Seeded faults for the biology lane, run through the factory's fault-injection harness.

Every mutant is WRONG by construction. An INCONSISTENT mutant changes the answer but not what the
kernel checks it against (the kernel must refuse it); a CONSISTENT mutant lies everywhere the lane
controls (answer, key option, kernel equation, witness) so only the independent Methods can refuse
it. A class is reported only when it was applied; the release rule is a 100 percent kill rate per
class, for the whole pipeline and for each named checker acting alone.
"""

from __future__ import annotations

import copy
import itertools
import random
from fractions import Fraction
from typing import Any

from app.content.originality import ReferenceIndex
from app.factory import faults as generic
from app.factory.faults import Fault, FaultReport, run_fault_injection
from app.factory.kernel.certify import box_axes
from app.factory.kernel.exact import chash, frac
from app.factory.lanes.biology.lane import LANE
from app.factory.lanes.biology.models import ALL_MODELS
from app.factory.lanes.biology.templates import all_templates
from app.factory.registry import ItemContext

M1, WP = "verify.method_1", "wellposed.predicates"


def _retarget(ctx: ItemContext, value: dict[str, Any], *, consistent: bool) -> ItemContext:
    """A copy of the item whose key is `value` (a wrong answer of the same shape)."""
    out = copy.deepcopy(ctx)
    out.answer = copy.deepcopy(value)
    for option in out.options:
        if option["id"] == out.key_option:
            option["value"] = copy.deepcopy(value)
    if consistent and out.spec.get("kind") == "linear_system":
        eq = out.spec["equations"][0]
        new = frac(value["values"]["x"])
        eq["const"] = str(frac(eq["coeffs"][0]) * new)
        out.witness = {"values": {"x": str(new)}}
    return out


def _wrong_values(ctx: ItemContext) -> list[dict[str, Any]]:
    return [o["value"] for o in ctx.options if o["id"] != ctx.key_option]


def wrong_key_inconsistent(ctx: ItemContext) -> list[ItemContext]:
    return [_retarget(ctx, v, consistent=False) for v in _wrong_values(ctx)[:2]]


def wrong_key_consistent(ctx: ItemContext) -> list[ItemContext]:
    return [_retarget(ctx, v, consistent=True) for v in _wrong_values(ctx)[:2]]


def named_wrong_is_key(ctx: ItemContext) -> list[ItemContext]:
    """A named misconception result is certified as the key everywhere the lane controls."""
    out = []
    for option in ctx.options:
        if option["id"] != ctx.key_option and str(option["procedure"]).startswith("BIO.MC."):
            out.append(_retarget(ctx, option["value"], consistent=True))
            break
    return out


def unit_label_wrong(ctx: ItemContext) -> list[ItemContext]:
    unit = ctx.answer.get("unit")
    if not unit:
        return []
    other = "minutes" if unit != "minutes" else "hours"
    value = {**ctx.answer, "unit": other}
    return [_retarget(ctx, value, consistent=True)]


def ratio_order_swapped(ctx: ItemContext) -> list[ItemContext]:
    ordered = ctx.answer.get("ordered")
    if not ordered or len(set(ordered)) < 2:
        return []
    swapped = list(ordered)
    i = next(k for k in range(len(swapped) - 1) if swapped[k] != swapped[k + 1])
    swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
    return [_retarget(ctx, {**ctx.answer, "ordered": swapped}, consistent=False)]


def dropped_class(ctx: ItemContext) -> list[ItemContext]:
    out = []
    if "ratio" in ctx.answer and len(ctx.answer["ratio"]) > 1:
        short = {"ratio": ctx.answer["ratio"][:-1], "ordered": ctx.answer["ordered"][:-1]}
        out.append(_retarget(ctx, short, consistent=False))
    if "probabilities" in ctx.answer and len(ctx.answer["probabilities"]) > 1:
        keys = sorted(ctx.answer["probabilities"])
        rest = {k: v for k, v in ctx.answer["probabilities"].items() if k != keys[0]}
        out.append(_retarget(ctx, {"probabilities": rest}, consistent=False))
    return out


def witness_corrupted(ctx: ItemContext) -> list[ItemContext]:
    out = copy.deepcopy(ctx)
    if "gametes" in out.witness:
        out.witness["gametes"][0] = out.witness["gametes"][0][:-1] or ["X"]
    elif "values" in out.witness:
        out.witness["values"]["x"] = str(frac(out.witness["values"]["x"]) + 1)
    else:
        return []
    return [out]


def equation_perturbed(ctx: ItemContext) -> list[ItemContext]:
    if ctx.spec.get("kind") != "linear_system":
        return []
    out = copy.deepcopy(ctx)
    eq = out.spec["equations"][0]
    eq["const"] = str(frac(eq["const"]) + 1)
    return [out]


def probability_certain(ctx: ItemContext) -> list[ItemContext]:
    """A probability key stated as 1 (or 0) for an outcome that is neither certain nor not."""
    value = ctx.answer.get("probability")
    if value is None:
        return []
    other = "0" if frac(value) == 1 else "1"
    return [_retarget(ctx, {"probability": other}, consistent=False)]


def _fault(fid: str, desc: str, fn: Any, *catchers: str) -> Fault:
    return Fault(fid, desc, fn, catchers)


LANE_FAULTS: tuple[Fault, ...] = (
    _fault(
        "wrong_key_inconsistent",
        "key is a wrong option, kernel relation untouched",
        wrong_key_inconsistent,
        WP,
        M1,
    ),
    _fault(
        "wrong_key_consistent",
        "key is a wrong option and the lane lies everywhere it controls",
        wrong_key_consistent,
        M1,
    ),
    _fault(
        "named_wrong_is_key",
        "a named misconception result is certified as the key",
        named_wrong_is_key,
        M1,
    ),
    _fault("unit_label_wrong", "the unit label on the answer is wrong", unit_label_wrong, M1),
    _fault(
        "ratio_order_swapped",
        "the parts of a ratio are in the wrong order",
        ratio_order_swapped,
        M1,
    ),
    _fault(
        "dropped_class", "a class of offspring is dropped from the answer", dropped_class, WP, M1
    ),
    _fault("witness_corrupted", "the witness is wrong", witness_corrupted, WP),
    _fault("equation_perturbed", "the kernel equation is off by one", equation_perturbed, WP),
    _fault(
        "probability_certain",
        "a probability is stated as certain or impossible",
        probability_certain,
        WP,
        M1,
    ),
)
GENERIC_FAULTS: tuple[Fault, ...] = tuple(
    f
    for f in generic.FAULTS
    if f.id in ("swapped_option", "distractor_equals_key", "duplicate_distractor", "hint_leaks_key",
                "method_wrong_answer", "single_group")
)  # fmt: skip
ALL_FAULTS = LANE_FAULTS + GENERIC_FAULTS


def fault_cases(per_model: int = 3, seed: int = 7) -> list[ItemContext]:
    """A seeded, spread-out sample of rendered items: a few tuples of every model and variant."""
    rng = random.Random(seed)
    cases: list[ItemContext] = []
    for mid, template in all_templates().items():
        axes = box_axes(template["box"])
        tuples = list(itertools.product(*[v for _, v in axes]))
        rng.shuffle(tuples)
        variants: dict[str, int] = {}
        picked = 0
        for combo in tuples:
            params = {n: c for (n, _), c in zip(axes, combo, strict=True)}
            if LANE.well_posed(template, params):
                continue
            v = str(params.get("variant", ""))
            if variants.get(v, 0) >= 1 and len(variants) < len(
                ALL_MODELS[mid].box.get("variant", ("",))
            ):
                continue
            ctx = LANE.render(template, params)
            ctx.reference_index = ReferenceIndex()
            cases.append(ctx)
            variants[v] = variants.get(v, 0) + 1
            picked += 1
            if picked >= per_model:
                break
    return cases


def run_all(per_model: int = 3, seed: int = 7) -> tuple[FaultReport, int]:
    cases = fault_cases(per_model, seed)
    return run_fault_injection(cases, ALL_FAULTS), len(cases)


_ = (Fraction, chash)
