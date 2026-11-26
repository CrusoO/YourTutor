# ruff: noqa: E501
"""Seeded faults for the chemistry lane, run through the factory's fault-injection harness.

Every mutant is WRONG by construction. Two flavours: an INCONSISTENT mutant changes the answer but
not the kernel's relation (the kernel must refuse it), and a CONSISTENT mutant lies everywhere the
lane controls (answer, key option, kernel equation, witness) so only the independent Methods can
refuse it. A class is only reported when it was actually applied; the release rule is a 100 percent
kill rate per class, both for the whole pipeline and for the named checker acting alone.
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
from app.factory.lanes.chemistry import catalog
from app.factory.lanes.chemistry.lane import LANE
from app.factory.registry import ItemContext

M1, WP = "verify.method_1", "wellposed.predicates"


def _set_key(ctx: ItemContext, answer: dict[str, Any]) -> ItemContext:
    out = copy.deepcopy(ctx)
    out.answer = answer
    for option in out.options:
        if option["id"] == out.key_option:
            option["value"] = copy.deepcopy(answer)
    return out


def _linear_vars(ctx: ItemContext) -> list[str]:
    values = ctx.answer.get("values")
    return (
        list(values) if isinstance(values, dict) and ctx.spec.get("kind") == "linear_system" else []
    )


def _bump_linear(ctx: ItemContext, var: str, new: Fraction, *, consistent: bool) -> ItemContext:
    out = _set_key(ctx, {**ctx.answer, "values": {**ctx.answer["values"], var: str(new)}})
    if consistent:
        # one equation per variable only for the single-unknown encodings; others are skipped
        eq = out.spec["equations"][0]
        eq["const"] = str(frac(eq["coeffs"][0]) * new)
        out.witness = {"values": {**ctx.witness["values"], var: str(new)}}
    return out


def value_off_by_one(ctx: ItemContext) -> list[ItemContext]:
    """Answer one too big, equation untouched (the kernel must refuse)."""
    out = []
    for var in _linear_vars(ctx):
        out.append(_bump_linear(ctx, var, frac(ctx.answer["values"][var]) + 1, consistent=False))
    if ctx.spec.get("kind") == "mass":
        out.append(_set_key(ctx, {**ctx.answer, "value": str(frac(ctx.answer["value"]) + 1)}))
    return out


def value_off_by_one_consistent(ctx: ItemContext) -> list[ItemContext]:
    """The lane lies everywhere it controls; only the independent methods can refuse it."""
    out = []
    if _linear_vars(ctx) and len(ctx.spec["variables"]) == 1:
        var = ctx.spec["variables"][0]
        out.append(_bump_linear(ctx, var, frac(ctx.answer["values"][var]) + 1, consistent=True))
    if "value" in ctx.answer and ctx.spec.get("kind") == "balance":
        out.append(_set_key(ctx, {**ctx.answer, "value": ctx.answer["value"] + 1}))
    return out


def sign_flip(ctx: ItemContext) -> list[ItemContext]:
    out = []
    for var in _linear_vars(ctx):
        v = frac(ctx.answer["values"][var])
        if v != 0:
            out.append(_bump_linear(ctx, var, -v, consistent=False))
    return out


def sign_flip_consistent(ctx: ItemContext) -> list[ItemContext]:
    out = []
    if _linear_vars(ctx) and len(ctx.spec["variables"]) == 1:
        var = ctx.spec["variables"][0]
        v = frac(ctx.answer["values"][var])
        if v != 0:
            out.append(_bump_linear(ctx, var, -v, consistent=True))
    return out


def coefficients_not_smallest(ctx: ItemContext) -> list[ItemContext]:
    """Every coefficient doubled: still balanced, but not the smallest whole numbers."""
    if ctx.spec.get("kind") != "balance":
        return []
    doubled = [2 * c for c in ctx.answer["coefficients"]]
    return [_set_key(ctx, {**ctx.answer, "coefficients": doubled})]


_TEXT_KEYS = ("name", "formula", "salt", "type", "outcome", "metal")


def label_swap(ctx: ItemContext) -> list[ItemContext]:
    """The key carries the label of a wrong option (the kernel cannot read labels)."""
    out = []
    for key in _TEXT_KEYS:
        if key not in ctx.answer:
            continue
        for option in ctx.options:
            if option["id"] != ctx.key_option and key in option["value"]:
                out.append(_set_key(ctx, {**ctx.answer, key: option["value"][key]}))
    return out


def payload_tampered(ctx: ItemContext) -> list[ItemContext]:
    """One number in the chemistry payload changed: the spec no longer says what the key says."""
    chem = ctx.spec.get("chem")
    if not isinstance(chem, dict):
        return []
    out = []
    for key, value in chem.items():
        if isinstance(value, int) and not isinstance(value, bool):
            mutant = copy.deepcopy(ctx)
            mutant.spec["chem"][key] = value + 1
            try:
                changed = chash(mutant.methods[0].solve(mutant.spec)) != chash(ctx.answer)
            except Exception:  # noqa: BLE001 - a method that refuses the payload also proves it wrong
                changed = True
            if changed:
                out.append(mutant)
    return out


LANE_FAULTS: tuple[Fault, ...] = (
    Fault("value_off_by_one", "answer one too big, equation untouched", value_off_by_one, (WP,)),
    Fault("value_off_by_one_consistent", "off by one everywhere the lane controls", value_off_by_one_consistent, (M1,)),
    Fault("sign_flip_linear", "answer sign flipped, equation untouched", sign_flip, (WP,)),
    Fault("sign_flip_consistent", "sign flipped everywhere the lane controls", sign_flip_consistent, (M1,)),
    Fault("coefficients_not_smallest", "all coefficients doubled", coefficients_not_smallest, (WP,)),
    Fault("label_swap", "the key carries a wrong option's label", label_swap, (M1,)),
    Fault("payload_tampered", "one payload number changed", payload_tampered, (M1,)),
)  # fmt: skip
GENERIC_IDS = (
    "off_by_one_atom", "wrong_constant", "unit_slip", "unit_dimension_slip", "swapped_option",
    "distractor_equals_key", "duplicate_distractor", "hint_leaks_key", "method_wrong_answer",
    "single_group",
)  # fmt: skip
GENERIC_FAULTS: tuple[Fault, ...] = tuple(f for f in generic.FAULTS if f.id in GENERIC_IDS)
ALL_FAULTS = LANE_FAULTS + GENERIC_FAULTS


def fault_cases(
    per_template: int = 4, seed: int = 7, only: list[str] | None = None
) -> list[ItemContext]:
    """A seeded, spread-out sample of rendered items from every template."""
    rng = random.Random(seed)
    cases: list[ItemContext] = []
    for tpl in catalog.template_records():
        if only and not any(o in tpl["id"] for o in only):
            continue
        axes = box_axes(tpl["box"])
        tuples = list(itertools.product(*[v for _, v in axes]))
        rng.shuffle(tuples)
        picked = 0
        for combo in tuples:
            params = {n: c for (n, _), c in zip(axes, combo, strict=True)}
            if LANE.well_posed(tpl, params):
                continue
            ctx = LANE.render(tpl, params)
            ctx.reference_index = ReferenceIndex()
            cases.append(ctx)
            picked += 1
            if picked >= per_template:
                break
    return cases


def run_all(
    per_template: int = 4, only: list[str] | None = None, seed: int = 7
) -> tuple[FaultReport, int]:
    cases = fault_cases(per_template, seed, only)
    return run_fault_injection(cases, ALL_FAULTS), len(cases)
