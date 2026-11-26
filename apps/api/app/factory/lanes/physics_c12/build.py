# ruff: noqa: E501
"""Backward construction of one Class 12 item from a parameter tuple.

Nice base values go in; every other quantity follows exactly; the question hides one of them.
The result is a `Built` bundle (spec, answer, options, words) or a plain-text reason why the
tuple makes a poor item (the lane counts those as ill-posed, never hides them).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from app.factory.lanes.physics.build import parse_value  # noqa: F401  (re-exported for the lane)
from app.factory.lanes.physics.model import MARKS, Model, Variant
from app.factory.lanes.physics_c12.consts import PHRASE, constant
from app.factory.lanes.physics_c12.methods import answer_dict
from app.factory.lanes.physics_c12.models import ALL_MODELS
from app.factory.lanes.physics_c12.quantities import (
    ExprError,
    dec,
    disp,
    evaluate,
    expr_names,
    from_si,
    fstr,
    quantity_text,
    sig_figs,
    to_si,
    unit_si,
    unit_text,
)

LEAD = {
    "mcq1": "",
    "num2": "This question is about {topic}.",
    "num3": "A student is studying {topic}.",
    "case4": "Case: a student investigates {topic} and records the following.",
}
BASE_DIFFICULTY = {"mcq1": 0.25, "num2": 0.4, "num3": 0.55, "case4": 0.7}
ROLE = {"mcq1": "procedure", "num2": "apply", "num3": "apply", "case4": "transfer"}
MAX_SF = 4
_OPENERS = (
    "List what the question gives you and what it asks for.",
    "Name each quantity in the question before you calculate.",
    "Separate the known quantities from the unknown one.",
    "Read the question once more and mark what you must find.",
)


@dataclass
class Built:
    model: Model
    variant: Variant
    form: str
    spec: dict[str, Any]
    answer: dict[str, Any]
    witness: dict[str, Any]
    stem: str
    hints: list[str]
    steps: list[str]
    prediction: str
    options: list[dict[str, Any]]
    key_text: str
    answer_tokens: list[str]
    difficulty: float
    role: str
    item_id: str
    features: list[str] = field(default_factory=list)
    key_si: Fraction = Fraction(0)
    key_unit: str = ""
    key_value: Fraction = Fraction(0)


def _clean(value: Fraction) -> bool:
    sf = sig_figs(value)
    return dec(value) is not None and sf is not None and sf <= MAX_SF


def _sub_numbers(expr: str, env: Mapping[str, Fraction]) -> str:
    def rep(m: re.Match[str]) -> str:
        name = m.group(0)
        if name in ("sqrt", "cbrt", "abs") or name not in env:
            return name
        text = disp(env[name])
        return f"({text})" if (env[name] < 0 or " x 10^" in text) else text

    return re.sub(r"[A-Za-z_][A-Za-z_0-9]*", rep, expr)


def _pretty_expr(expr: str) -> str:
    text = expr.replace("*", " x ").replace("/", " / ")
    return re.sub(
        r"(?<=[A-Za-z0-9)])\s*([+-])\s*(?=[A-Za-z0-9(])", lambda m: " " + m.group(1) + " ", text
    )


_PAREN_WORDS = re.compile(r"\(([A-Za-z]+(?:\s+[A-Za-z]+)*)\)")


def _brk(text: str) -> str:
    """Square brackets for a group made only of letters (the language lint reads (word) as a leftover)."""
    return _PAREN_WORDS.sub(lambda m: "[" + m.group(1) + "]", text)


def _words_list(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _sentence(clauses: list[str]) -> str:
    text = _words_list(clauses)
    return text[0].upper() + text[1:] + "."


def build(template: Mapping[str, Any], params: Mapping[str, Any]) -> Built | str:  # noqa: PLR0911, PLR0912, PLR0915
    model = ALL_MODELS[str(template["model"])]
    variant = model.variants.get(str(params.get("variant")))
    if variant is None:
        return "unknown_variant"
    form = str(params.get("form"))
    if form not in variant.forms:
        return "form_not_offered_for_this_variant"
    try:
        base_si, units = model.base(params)
    except (ValueError, KeyError, ZeroDivisionError, ArithmeticError):
        return "bad_parameters"
    env: dict[str, Fraction] = dict(base_si)
    for sym, cid in model.consts.items():
        c = constant(cid)
        env[sym] = to_si(c.value, c.unit)
    try:
        for sym, expr in model.derived(params):
            env[sym] = evaluate(expr, env)
    except ExprError:
        return "degenerate_geometry"
    for sym, unit in model.dunits.items():
        units.setdefault(sym, unit)
    find = variant.find
    if find not in env or find not in units:
        return "unknown_quantity"
    if any(n not in env for n in variant.needs):
        return "variant_needs_missing_quantity"
    if any(env[s] <= 0 for s in (*variant.needs, find)):
        return "non_positive_quantity"
    for sym in (*variant.needs, find):
        lo_hi = model.sizes.get(sym)
        if lo_hi and not (lo_hi[0] <= abs(env[sym]) <= lo_hi[1]):
            return f"implausible_size:{sym}"

    given: dict[str, dict[str, Any]] = {}
    shown: dict[str, str] = {}
    raw: dict[str, Fraction] = {}
    numbers: list[str] = []
    conversions: list[str] = []
    for sym in variant.needs:
        unit = units[sym]
        value = from_si(env[sym], unit)
        if not _clean(value):
            return f"given_not_clean:{sym}"
        given[sym] = {"value": fstr(value), "unit": unit}
        raw[sym] = value
        shown[sym] = quantity_text(value, unit)
        numbers.append(disp(value))
        si_unit = model.syms[sym]
        if unit_si(unit)[0] != unit_si(si_unit)[0]:
            conversions.append(f"{shown[sym]} = {quantity_text(env[sym], si_unit)}")
    for sym, cid in model.consts.items():
        given[sym] = {"const": cid}
        c = constant(cid)
        shown[sym] = quantity_text(from_si(env[sym], c.unit), c.unit)

    key_unit = units[find]
    key_val = from_si(env[find], key_unit)
    if not _clean(key_val):
        return "answer_not_clean"
    if disp(key_val) in numbers:
        return "answer_equals_a_given"
    fa = unit_si(key_unit)[0]
    answer = answer_dict(find, key_val, key_unit)
    witness = {"values": {find: fstr(key_val)}}

    # kernel equation: coeff * x_si = const, x_si = fa * x
    try:
        kenv = {k: env[k] for k in (*variant.needs, *model.consts)}
        kc = evaluate(variant.keq[0], kenv) * fa
        kk = evaluate(variant.keq[1], kenv)
    except ExprError:
        return "degenerate_kernel_equation"
    if kc == 0:
        return "kernel_equation_is_singular"
    spec = {
        "domain": "algebra",
        "kind": "linear_system",
        "variables": [find],
        "equations": [{"coeffs": [fstr(kc)], "const": fstr(kk)}],
        "physics": {
            "model": model.id,
            "variant": variant.id,
            "find": find,
            "answer_unit": key_unit,
            "given": given,
        },
    }

    picks = _pick_wrongs(model, variant, env, raw, key_val, fa)
    if isinstance(picks, str):
        return picks
    key_text = quantity_text(key_val, key_unit)
    options = [{"id": "key", "value": answer, "text": key_text, "procedure": "correct"}]
    for i, (mc, val) in enumerate(picks, start=1):
        options.append(
            {"id": f"d{i}", "value": answer_dict(find, val, key_unit), "text":
             quantity_text(val, key_unit), "procedure": mc}
        )  # fmt: skip

    # words
    noun = model.labels.get(find, (find, ""))[0]
    clauses: list[str] = []
    for sym in variant.needs:
        phrase = model.labels[sym][1]
        if " is {v}" in phrase:
            phrase = phrase.replace(" is {v}", f", {sym}, is " + "{v}", 1)
        clauses.append(phrase.format(v=shown[sym]))
    used = expr_names(variant.expr)
    stated = [
        PHRASE[cid].format(v=shown[sym], sym=sym)
        for sym, cid in model.consts.items()
        if sym in used
    ]
    stem_core = f"{_sentence(clauses)} {variant.ask}"
    if stated:
        stem_core = f"{_sentence(clauses)} {variant.ask} Take {_words_list(stated)}."
    lead = LEAD[form].format(topic=model.topic)
    stem = _brk(f"{lead} {stem_core}".strip())

    hints, steps = _hints_and_steps(
        model, variant, noun, env, conversions, key_unit, key_val, fa, params
    )
    for h in hints:
        for token in (disp(key_val), fstr(key_val)):
            if re.search(rf"(?<![\d.]){re.escape(token)}(?![\d.])", h):
                return "hint_contains_the_answer"
    feats = []
    if conversions or fa != 1:
        feats.append("unit_conversion")
    if variant.rearr:
        feats.append("rearrangement")
    if len(variant.needs) >= 3:
        feats.append("three_or_more_givens")
    if stated:
        feats.append("constant_from_table")
    difficulty = BASE_DIFFICULTY[form] + 0.05 * min(2, len(feats))
    digest = hashlib.sha1(
        json.dumps(sorted((k, str(v)) for k, v in params.items())).encode()
    ).hexdigest()[:8]
    item_id = f"ITM.{model.skill}.{variant.id}.{form}.{digest}"
    prediction = (
        f"Before you calculate, roughly how large should the {noun} be?"
        if model.syms[find] in ("unit",)
        else f"Before you calculate, what unit should the {noun} have, and roughly how large is it?"
    )
    return Built(
        model=model, variant=variant, form=form, spec=spec, answer=answer, witness=witness,
        stem=stem, hints=hints, steps=steps, prediction=prediction, options=options,
        key_text=key_text, answer_tokens=[disp(key_val)], difficulty=round(min(0.9, difficulty), 2),
        role=ROLE[form], item_id=item_id, features=feats, key_si=env[find], key_unit=key_unit,
        key_value=key_val,
    )  # fmt: skip


def _pick_wrongs(
    model: Model,
    variant: Variant,
    env: Mapping[str, Fraction],
    raw: Mapping[str, Fraction],
    key_val: Fraction,
    fa: Fraction,
) -> list[tuple[str, Fraction]] | str:
    wenv: dict[str, Fraction] = {n: env[n] for n in (*variant.needs, *model.consts)}
    for n, v in raw.items():
        wenv[f"{n}_r"] = v
    wenv["K"], wenv["FA"] = key_val, fa
    candidates = list(variant.wrongs)
    factor = fa if fa > 1 else 1 / fa
    if model.auto_slips and factor in (10, 100, 1000, 10**6):
        candidates += [
            (f"{model.mc_prefix}.UNIT_PREFIX_SLIP", f"@K*{factor}"),
            (f"{model.mc_prefix}.UNIT_PREFIX_SLIP", f"@K/{factor}"),
        ]
    # last resort, used only when the named wrong procedures give fewer than three options
    spare = [(f"{model.mc_prefix}.POWER_OF_TEN_SLIP", f"@K*{x}") for x in ("10", "100", "1000")]
    spare += [(f"{model.mc_prefix}.POWER_OF_TEN_SLIP", f"@K/{x}") for x in ("10", "100", "1000")]
    scored: list[tuple[str, Fraction]] = []
    for mc, expr in candidates + spare:
        try:
            val = evaluate(expr[1:], wenv) if expr.startswith("@") else evaluate(expr, wenv) / fa
        except ExprError:
            continue
        if val == key_val or val <= 0 or not (_SPAN[0] < val / key_val < _SPAN[1]):
            continue
        scored.append((mc, val))
    chosen: list[tuple[str, Fraction]] = []
    for allow_repeat in (False, True):
        for mc, val in scored:
            texts = {disp(v) for _, v in chosen} | {disp(key_val)}
            if (mc, val) in chosen or disp(val) in texts:
                continue
            if not allow_repeat and mc in {m for m, _ in chosen}:
                continue
            chosen.append((mc, val))
            if len(chosen) == 3:
                return chosen
    return "fewer_than_three_distinct_named_wrongs"


_SPAN = (Fraction(1, 10**7), Fraction(10**7))  # a distractor within seven orders of the key


def _hints_and_steps(
    model: Model,
    variant: Variant,
    noun: str,
    env: Mapping[str, Fraction],
    conversions: list[str],
    key_unit: str,
    key_val: Fraction,
    fa: Fraction,
    params: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    find = variant.find
    plan = "=" not in variant.formula
    conversions = list(dict.fromkeys(conversions))
    opener = _OPENERS[int(hashlib.sha1(repr(sorted(params.items())).encode()).hexdigest(), 16) % 4]
    h1 = (
        f"{opener} Plan the steps: {variant.formula}."
        if plan
        else f"{opener} Pick the relation that links them: {variant.formula}."
    )
    if variant.rearr:
        h2 = (
            f"Get the {noun} on its own before you put numbers in: {variant.rearr}. "
            "Do the same operation to each side of the formula."
        )
    elif plan:
        h2 = "Work through the plan one step at a time."
    else:
        h2 = f"The relation already gives the {noun} directly, so decide what to substitute."
    if conversions or fa != 1:
        h2 += " Change every quantity to SI units first, and change back at the end if asked."
    lead = ""
    if conversions:
        lead = "Write " + _words_list([c.replace(" = ", " as ") for c in conversions]) + ", then "
    h3 = (
        f"First step: {lead}write {find} = {_pretty_expr(variant.expr)}, where {find} is the {noun}, "
        "with the values in place, one quantity at a time."
    )
    steps = [f"{'Plan' if plan else 'Write the relation'}: {variant.formula}."]
    if conversions:
        steps.append("Put each quantity in SI units: " + "; ".join(conversions) + ".")
    if variant.rearr:
        steps.append(f"Get the {noun} alone: {variant.rearr}.")
    si_unit = model.syms[find]
    si_text = quantity_text(env[find], si_unit)
    sub = _pretty_expr(_sub_numbers(variant.expr, env))
    steps.append(f"Substitute: {find} = {sub}.")
    steps.append(f"Calculate: {find} = {si_text}.")
    if fa != 1 or key_unit != si_unit:
        steps.append(
            f"Give it in {unit_text(key_unit) or key_unit}: {quantity_text(key_val, key_unit)}."
        )
    steps.append(f"So the {noun} is {quantity_text(key_val, key_unit)}.")
    return [_brk(h) for h in (h1, h2, h3)], [_brk(x) for x in steps]


__all__ = ["MARKS", "Built", "build", "parse_value"]
