"""Seeded faults for the Class 12 physics lane, run through the factory's fault-injection harness.

Every mutant is WRONG by construction. Two flavours: an INCONSISTENT mutant changes the answer but
not the kernel equation (the kernel must refuse it), and a CONSISTENT mutant lies everywhere the
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
from app.factory.kernel.exact import frac
from app.factory.lanes.physics_c12.consts import constant
from app.factory.lanes.physics_c12.lane import LANE
from app.factory.lanes.physics_c12.methods import answer_dict
from app.factory.lanes.physics_c12.models import ALL_MODELS
from app.factory.lanes.physics_c12.quantities import evaluate, expr_names, sig_figs, to_si, unit_si
from app.factory.lanes.physics_c12.templates import TEMPLATES
from app.factory.registry import ItemContext

_UNITS_BY_DIM: dict[tuple[int, ...], list[str]] = {}
for _u in (
    "A",
    "mA",
    "uA",
    "V",
    "mV",
    "kV",
    "ohm",
    "kohm",
    "W",
    "kW",
    "J",
    "mJ",
    "uJ",
    "kJ",
    "eV",
    "MeV",
    "C",
    "uC",
    "nC",
    "pC",
    "m",
    "cm",
    "mm",
    "nm",
    "pm",
    "km",
    "s",
    "ms",
    "us",
    "F",
    "uF",
    "pF",
    "H",
    "mH",
    "T",
    "mT",
    "uT",
    "nT",
    "Wb",
    "mWb",
    "Hz",
    "MHz",
    "N",
    "mN",
    "unit",
    "W/m^2",
    "m/s",
    "kg",
    "per_m",
    "per_m3",
    "kgm/s",
    "rad/s",
    "N/C",
    "V/m",
    "N/m",
    "mN/m",
    "Nm",
    "mNm",
    "Cm",
    "A/m",
    "m^2",
    "cm^2",
    "mm^2",
):
    _UNITS_BY_DIM.setdefault(tuple(unit_si(_u)[1]), []).append(_u)
_SLIP_NAMES = ("UNIT_SLIP", "UNIT_PREFIX_SLIP", "POWER_OF_TEN_SLIP")
_DROP_WORDS = ("FORGOTTEN", "IGNORED", "LEFT_OUT")


def _same_dim(unit: str) -> str | None:
    """A different unit of the same dimension and a different size, or None."""
    factor, dim = unit_si(unit)
    for other in _UNITS_BY_DIM.get(tuple(dim), []):
        if other != unit and unit_si(other)[0] != factor:
            return other
    return None


def _wrong_dim(unit: str) -> str:
    dim = tuple(unit_si(unit)[1])
    for other in ("m", "s", "kg", "A", "unit"):
        if tuple(unit_si(other)[1]) != dim:
            return other
    raise ValueError("no wrong dimension found")


def _find(ctx: ItemContext) -> str:
    return str(ctx.spec["physics"]["find"])


def _value(ctx: ItemContext) -> Fraction:
    return frac(ctx.answer["values"][_find(ctx)])


def _lie(
    ctx: ItemContext, new: Fraction, *, consistent: bool, unit: str | None = None
) -> ItemContext:
    """A copy of the item whose key is `new`. consistent=True also rewrites eq and witness."""
    out = copy.deepcopy(ctx)
    find = _find(ctx)
    answer = answer_dict(find, new, unit or ctx.answer["unit"])
    out.answer = answer
    for option in out.options:
        if option["id"] == out.key_option:
            option["value"] = copy.deepcopy(answer)
    if consistent:
        eq = out.spec["equations"][0]
        eq["const"] = str(frac(eq["coeffs"][0]) * new)
        out.witness = {"values": {find: str(new)}}
    return out


def sign_flip(ctx: ItemContext) -> list[ItemContext]:
    return [_lie(ctx, -_value(ctx), consistent=False)] if _value(ctx) != 0 else []


def sign_flip_consistent(ctx: ItemContext) -> list[ItemContext]:
    return [_lie(ctx, -_value(ctx), consistent=True)] if _value(ctx) != 0 else []


def unit_slip(ctx: ItemContext) -> list[ItemContext]:
    other = _same_dim(ctx.answer["unit"])
    return [_lie(ctx, _value(ctx), consistent=False, unit=other)] if other else []


def unit_dimension_slip(ctx: ItemContext) -> list[ItemContext]:
    return [_lie(ctx, _value(ctx), consistent=False, unit=_wrong_dim(ctx.answer["unit"]))]


def _from_procedures(ctx: ItemContext, words: tuple[str, ...]) -> list[ItemContext]:
    find = _find(ctx)
    out = []
    for option in ctx.options:
        proc = str(option["procedure"]).rsplit(".", 1)[-1]
        if proc != "correct" and any(w in proc for w in words):
            out.append(_lie(ctx, frac(option["value"]["values"][find]), consistent=True))
    return out


def unit_slip_consistent(ctx: ItemContext) -> list[ItemContext]:
    return _from_procedures(ctx, _SLIP_NAMES)


def dropped_factor(ctx: ItemContext) -> list[ItemContext]:
    return _from_procedures(ctx, _DROP_WORDS)


def _const_names(ctx: ItemContext) -> list[str]:
    phys = ctx.spec["physics"]
    model = ALL_MODELS[phys["model"]]
    variant = model.variants[phys["variant"]]
    return [s for s in model.consts if s in expr_names(variant.expr)]


def wrong_constant(ctx: ItemContext) -> list[ItemContext]:
    """The lane computed with a wrong constant (x10 or x1/2) and lied consistently."""
    names = _const_names(ctx)
    if not names:
        return []
    phys = ctx.spec["physics"]
    variant = ALL_MODELS[phys["model"]].variants[phys["variant"]]
    out = []
    for factor in (Fraction(10), Fraction(1, 2)):
        env: dict[str, Fraction] = {}
        for sym, q in phys["given"].items():
            if "const" in q:
                c = constant(q["const"])
                env[sym] = to_si(c.value, c.unit) * (factor if sym in names else 1)
            else:
                env[sym] = to_si(q["value"], q["unit"])
        new = evaluate(variant.expr, env) / unit_si(ctx.answer["unit"])[0]
        out.append(_lie(ctx, new, consistent=True))
    return out


def literal_constant(ctx: ItemContext) -> list[ItemContext]:
    """The constant is typed into the spec as a number instead of referenced from the table."""
    names = _const_names(ctx)
    out = []
    for sym in names:
        mutant = copy.deepcopy(ctx)
        c = constant(mutant.spec["physics"]["given"][sym]["const"])
        mutant.spec["physics"]["given"][sym] = {"value": c.value, "unit": c.unit}
        out.append(mutant)
    return out


def _one_sig_fig_less(x: Fraction) -> Fraction | None:
    sf = sig_figs(x)
    if sf is None or sf < 2:
        return None
    exp = 0
    mag = abs(x)
    while mag >= 10:
        mag /= 10
        exp += 1
    while mag < 1:
        mag *= 10
        exp -= 1
    quantum = Fraction(10) ** (exp - (sf - 2))
    rounded = Fraction(int(abs(x) / quantum + Fraction(1, 2))) * quantum
    rounded = rounded if x > 0 else -rounded
    return rounded if rounded != x else None


def wrong_sig_figs(ctx: ItemContext) -> list[ItemContext]:
    new = _one_sig_fig_less(_value(ctx))
    return [_lie(ctx, new, consistent=False)] if new is not None else []


def wrong_sig_figs_consistent(ctx: ItemContext) -> list[ItemContext]:
    new = _one_sig_fig_less(_value(ctx))
    return [_lie(ctx, new, consistent=True)] if new is not None else []


def _lane_fault(fid: str, desc: str, fn: Any, catcher: str) -> Fault:
    return Fault(fid, desc, fn, (catcher,))


M1, WP = "verify.method_1", "wellposed.predicates"
LANE_FAULTS: tuple[Fault, ...] = (
    _lane_fault("sign_flip", "answer sign flipped, equation untouched", sign_flip, WP),
    _lane_fault(
        "sign_flip_consistent",
        "sign flipped everywhere the lane controls",
        sign_flip_consistent,
        M1,
    ),  # noqa: E501
    _lane_fault("unit_slip", "right-dimension unit label on the answer is wrong", unit_slip, M1),
    _lane_fault(
        "unit_dimension_slip", "answer unit has the wrong dimension", unit_dimension_slip, M1
    ),  # noqa: E501
    _lane_fault(
        "unit_slip_consistent", "a named unit-slip result is the key", unit_slip_consistent, M1
    ),  # noqa: E501
    _lane_fault("dropped_factor", "a named dropped-factor result is the key", dropped_factor, M1),
    _lane_fault("wrong_constant", "the lane used a wrong house constant", wrong_constant, M1),
    _lane_fault(
        "literal_constant", "a constant typed in instead of referenced", literal_constant, M1
    ),  # noqa: E501
    _lane_fault(
        "wrong_sig_figs", "answer rounded to fewer significant figures", wrong_sig_figs, WP
    ),  # noqa: E501
    _lane_fault(
        "wrong_sig_figs_consistent",
        "fewer significant figures everywhere",
        wrong_sig_figs_consistent,
        M1,
    ),  # noqa: E501
)
GENERIC_FAULTS: tuple[Fault, ...] = tuple(
    f for f in generic.FAULTS
    if f.id in ("swapped_option", "distractor_equals_key", "duplicate_distractor",
                "hint_leaks_key", "method_wrong_answer", "single_group")
)  # fmt: skip
ALL_FAULTS = LANE_FAULTS + GENERIC_FAULTS


def fault_cases(chapter: str, per_template: int = 4, seed: int = 7) -> list[ItemContext]:
    """A seeded, spread-out sample of rendered items for one chapter (a mix of forms/variants)."""
    rng = random.Random(seed)
    cases: list[ItemContext] = []
    for model in ALL_MODELS.values():
        if chapter != "all" and model.chapter != chapter:
            continue
        tpl = TEMPLATES[model.id]
        axes = box_axes(tpl["box"])
        tuples = list(itertools.product(*[v for _, v in axes]))
        rng.shuffle(tuples)
        by_variant: dict[str, int] = {}
        picked = 0
        for combo in tuples:
            params = {n: c for (n, _), c in zip(axes, combo, strict=True)}
            if LANE.well_posed(tpl, params):
                continue
            v = str(params["variant"])
            if by_variant.get(v, 0) >= max(1, per_template // 2) and len(by_variant) < len(
                model.variants
            ):  # noqa: E501
                continue
            ctx = LANE.render(tpl, params)
            ctx.reference_index = ReferenceIndex()
            cases.append(ctx)
            by_variant[v] = by_variant.get(v, 0) + 1
            picked += 1
            if picked >= per_template:
                break
    return cases


def run_chapter(chapter: str, per_template: int = 4, seed: int = 7) -> tuple[FaultReport, int]:
    cases = fault_cases(chapter, per_template, seed)
    return run_fault_injection(cases, ALL_FAULTS), len(cases)
