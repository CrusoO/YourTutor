# ruff: noqa: E501
"""Backward construction of one item from a parameter tuple.

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

from app.factory.kernel.constants import constant
from app.factory.kernel.exact import frac
from app.factory.lanes.physics.methods import answer_dict, nature_label
from app.factory.lanes.physics.model import MARKS, Model, Variant
from app.factory.lanes.physics.models import ALL_MODELS
from app.factory.lanes.physics.quantities import (
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
CONST_PHRASE = {
    "c_light": "the speed of light in vacuum is {v}",
    "e_charge": "the charge of one electron is {v}",
}
SIGN_PHRASES = {
    ("mirror", "object_distance"): "An object is placed {d} in front of a {dev}.",
    (
        "lens",
        "object_distance",
    ): "An object is placed {d} from a {dev}, on the side the light comes from.",  # noqa: E501
    ("mirror", "focal"): "A {dev} has a focal length of magnitude {d}.",
    ("lens", "focal"): "A {dev} has a focal length of magnitude {d}.",
    ("mirror", "image_real"): "A real image forms {d} in front of a {dev}.",
    ("lens", "image_real"): "A real image forms {d} from a {dev}, on the side opposite the object.",
    ("mirror", "image_virtual"): "A virtual image forms {d} behind a {dev}.",
    (
        "lens",
        "image_virtual",
    ): "A virtual image forms {d} from a {dev}, on the same side as the object.",  # noqa: E501
}
SIGN_SYMBOL = {"object_distance": "u", "focal": "f", "image_real": "v", "image_virtual": "v"}
BASE_DIFFICULTY = {"mcq1": 0.25, "num2": 0.4, "num3": 0.55, "case4": 0.7}
ROLE = {"mcq1": "procedure", "num2": "apply", "num3": "apply", "case4": "transfer"}
MAX_SF = 3
_OPENERS = (
    "List what the question gives you and what it asks for.",
    "Name each quantity in the question before you calculate.",
    "Separate the known quantities from the unknown one.",
    "Read the question once more and mark what you must find.",
)
_NO_SYMBOL = {"kL", "kA", "kV", "kI", "kR", "kt", "F", "FV", "FR", "FI", "FVR", "FH", "s", "x", "si", "sr"}  # fmt: skip


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


def _device_ok(model: Model, params: Mapping[str, Any], variant: Variant) -> str | None:
    mid = model.id
    if mid == "LIGHT.LENS_COMB":
        ok = all(str(params[k]).endswith("lens") for k in ("d1", "d2"))
        return None if ok else "needs_two_lenses"
    if model.device is None:
        return None
    dev = model.device(params)
    want = None
    if mid.startswith("LIGHT.MIRROR") and mid != "LIGHT.MIRROR_NATURE":
        want = "mirror"
    elif mid.startswith("LIGHT.LENS"):
        want = "lens"
    elif variant.nature:
        want = variant.nature
    if want and not str(dev).endswith(want):
        return "device_does_not_match_the_model"
    return None


def _sub_numbers(expr: str, env: Mapping[str, Fraction]) -> str:
    def rep(m: re.Match[str]) -> str:
        name = m.group(0)
        if name in ("sqrt", "abs") or name not in env:
            return name
        text = disp(env[name])
        return f"({text})" if (env[name] < 0 or " x 10^" in text) else text

    return re.sub(r"[A-Za-z_][A-Za-z_0-9]*", rep, expr)


def _pretty_expr(expr: str) -> str:
    text = expr.replace("*", " x ").replace("/", " / ")
    return re.sub(
        r"(?<=[A-Za-z0-9)])\s*([+-])\s*(?=[A-Za-z0-9(])", lambda m: " " + m.group(1) + " ", text
    )


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
    reason = _device_ok(model, params, variant)
    if reason:
        return reason
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
    if not model.signed and any(env[s] <= 0 for s in (*variant.needs, find)):
        return "non_positive_quantity"
    for sym in (*variant.needs, find):
        lo_hi = model.sizes.get(sym)
        if lo_hi and not (lo_hi[0] <= abs(env[sym]) <= lo_hi[1]):
            return f"implausible_size:{sym}"
        if env[sym] == 0:
            return "zero_quantity"

    if "rset" in params:
        n_syms = len({x for x in (*variant.needs, find) if re.fullmatch(r"R\d", x)})
        if len(str(params["rset"]).split(",")) != n_syms:
            return "rset_size_does_not_match_variant"
    roles = model.roles(params, env) if model.roles else {}
    device = model.device(params) if model.device else None
    given: dict[str, dict[str, Any]] = {}
    shown: dict[str, str] = {}
    raw: dict[str, Fraction] = {}
    numbers: list[str] = []
    conversions: list[str] = []
    signs: list[str] = []
    for sym in variant.needs:
        unit = units[sym]
        value = from_si(env[sym], unit)
        role = roles.get(sym)
        if role:
            value = abs(value)
        if not model.rule_derived and not _clean(value):
            return f"given_not_clean:{sym}"
        entry: dict[str, Any] = {"value": fstr(value), "unit": unit}
        if role:
            entry["role"] = role[0]
            if role[1] and role[1] != device:
                entry["device"] = role[1]
        given[sym] = entry
        raw[sym] = value
        shown[sym] = quantity_text(value, unit)
        numbers.append(disp(value))
        si_unit = model.syms[sym]
        if unit_si(unit)[0] != unit_si(si_unit)[0]:
            conversions.append(f"{shown[sym]} = {quantity_text(env[sym], si_unit)}")
        if role:
            signs.append(f"{sym} = {quantity_text(env[sym], si_unit)}")
    for sym, cid in model.consts.items():
        given[sym] = {"const": cid}
        shown[sym] = quantity_text(env[sym], model.syms[sym])
    find_role = None
    if model.id == "LIGHT.SIGN":
        find_role = str(params["case"]).split(":")[1]

    # the answer
    key_unit = units[find]
    key_val = from_si(env[find], key_unit)
    if not _clean(key_val):
        return "answer_not_clean"
    if disp(key_val) in numbers:
        return "answer_equals_a_given"
    fa = unit_si(key_unit)[0]
    nature = None
    if variant.nature:
        m_val = env["m"]
        try:
            nature = nature_label(variant.nature, env["v"], m_val)
        except ValueError:
            return "same_size_image_excluded"
    answer = answer_dict(find, key_val, key_unit, nature)
    witness = {"values": {find: fstr(key_val)}}

    # kernel equation: coeff * x_si = const, x_si = fa * x
    try:
        kenv = {k: env[k] for k in (*variant.needs, *model.consts)}
        if model.id == "LIGHT.SIGN":
            kenv["s"] = env["s"]
        kc = evaluate(variant.keq[0], kenv) * fa
        kk = evaluate(variant.keq[1], kenv)
    except ExprError:
        return "degenerate_kernel_equation"
    if kc == 0:
        return "kernel_equation_is_singular"
    phys: dict[str, Any] = {
        "model": model.id,
        "variant": variant.id,
        "find": find,
        "answer_unit": key_unit,
        "given": given,
    }
    if device:
        phys["device"] = device
    if find_role:
        phys["find_role"] = find_role
    spec = {
        "domain": "algebra",
        "kind": "linear_system",
        "variables": [find],
        "equations": [{"coeffs": [fstr(kc)], "const": fstr(kk)}],
        "physics": phys,
    }

    # options
    if variant.nature:
        wrongs = _nature_wrongs(answer, nature or "", env["v"], variant.nature)
        key_text = nature or ""
        options = [{"id": "key", "value": answer, "text": key_text, "procedure": "correct"}]
        for i, (mc, label) in enumerate(wrongs, start=1):
            options.append(
                {"id": f"d{i}", "value": answer_dict(find, key_val, key_unit, label),
                 "text": label, "procedure": mc}
            )  # fmt: skip
    else:
        picks = _pick_wrongs(model, variant, params, env, raw, key_val, key_unit, fa)
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
    custom = _scale_stem(model, variant, params)
    if isinstance(custom, str) and custom.startswith("!"):
        return custom[1:]
    if custom:
        stem_core = f"{custom} {variant.ask}"
    elif model.id == "LIGHT.SIGN":
        fam = "mirror" if str(device).endswith("mirror") else "lens"
        d_text = quantity_text(raw["d"], units["d"])
        dev_name = str(device).replace("_", " ")
        given_sentence = SIGN_PHRASES[(fam, str(find_role))].format(d=d_text, dev=dev_name)
        ask = (f"Using the Cartesian sign convention, what is the value of "
               f"{SIGN_SYMBOL[str(find_role)]} in cm?")  # fmt: skip
        stem_core = f"{given_sentence} {ask}"
    else:
        for sym in variant.needs:
            phrase = model.labels[sym][1]
            if " is {v}" in phrase and sym not in _NO_SYMBOL:
                phrase = phrase.replace(" is {v}", f", {sym}, is " + "{v}", 1)
            kind = orient = ""
            if model.roles and sym == "v":
                kind = "real" if roles["v"][0] == "image_real" else "virtual"
                phrase = "the image, which is {kind}, is {v} from the {dev}"
            elif model.roles and sym == "hi":
                orient = "erect" if roles["hi"][0] == "height_image_erect" else "inverted"
                phrase = "the image is {v} tall and {orient}"
            clauses.append(
                phrase.format(
                    v=shown[sym],
                    dev=str((roles.get(sym, (None, None))[1] or device) or "").replace("_", " "),
                    kind=kind,
                    orient=orient,
                )
            )
        for sym, cid in model.consts.items():
            if sym in expr_names(variant.expr):
                clauses.append(CONST_PHRASE[cid].format(v=shown[sym]))
        ask = variant.ask
        stem_core = f"{_sentence(clauses)} {ask}"
    lead = LEAD[form].format(topic=model.topic)
    if model.id in ("ELEC.RESIST_SCALE", "ELEC.POWER_SCALE") and not custom:
        return "scale_stem_missing"
    stem = f"{lead} {stem_core}".strip()

    hints, steps = _hints_and_steps(
        model, variant, noun, env, shown, conversions, signs, key_unit, key_val, nature, fa, params
    )
    for h in hints:
        for token in (disp(key_val), fstr(key_val)):
            if re.search(rf"(?<![\d.]){re.escape(token)}(?![\d.])", h):
                return "hint_contains_the_answer"
    feats = []
    if conversions or fa != 1:
        feats.append("unit_conversion")
    if model.signed:
        feats.append("sign_convention")
    if variant.rearr:
        feats.append("rearrangement")
    if len(variant.needs) >= 3:
        feats.append("three_or_more_givens")
    if variant.kind == "rule":
        feats.append("rule_derived")
    difficulty = BASE_DIFFICULTY[form] + 0.05 * min(2, len(feats))
    digest = hashlib.sha1(
        json.dumps(sorted((k, str(v)) for k, v in params.items())).encode()
    ).hexdigest()[:8]
    item_id = f"ITM.{model.skill}.{variant.id}.{form}.{digest}"
    prediction = (
        "Think first: which quantities does the answer depend on, and does it grow or shrink?"
        if variant.kind == "rule"
        else (
            f"Before you calculate, roughly how large should the {noun} be?"
            if model.syms[find] == "unit"
            else f"Before you calculate, what unit should the {noun} have, and roughly how large is it?"  # noqa: E501
        )
    )
    tokens = [disp(key_val)]
    return Built(
        model=model, variant=variant, form=form, spec=spec, answer=answer, witness=witness,
        stem=stem, hints=hints, steps=steps, prediction=prediction, options=options,
        key_text=key_text, answer_tokens=tokens, difficulty=round(min(0.9, difficulty), 2),
        role="explain" if variant.kind == "rule" else ROLE[form], item_id=item_id,
        features=feats, key_si=env[find], key_unit=key_unit, key_value=key_val,
    )  # fmt: skip


def _times(k: str) -> str:
    return {"2": "doubled", "3": "tripled", "1/2": "halved"}.get(k, f"multiplied by {k}")


def _scale_stem(model: Model, variant: Variant, p: Mapping[str, Any]) -> str | None:
    """Stems for the two rule-derived scaling models (their givens are factors, not quantities)."""
    if model.id == "ELEC.RESIST_SCALE":
        k = str(p["k"])
        if p["case"] == "stretch":
            if Fraction(k) <= 1:
                return "!stretch_factor_must_exceed_one"
            return (f"A uniform wire is stretched evenly to {k} times its original length, "
                    "so its volume stays the same.")  # fmt: skip
        return (
            f"The diameter of a uniform wire is {_times(k)}; its length and material stay the same."
        )
    if model.id == "ELEC.POWER_SCALE":
        k, k2 = str(p["k"]), str(p["k2"])
        return {
            "P_V_scaled": f"The potential difference across a fixed resistor is {_times(k)}.",
            "P_R_scaled": "A fixed potential difference is applied across a resistor "
            f"whose resistance is {_times(k2)}.",
            "P_I_scaled": f"The current through a fixed resistor is {_times(k)}.",
            "P_VR_scaled": f"The potential difference across a resistor is {_times(k)} "
            f"and its resistance is {_times(k2)}.",
            "H_It_scaled": f"The current through a fixed resistor is {_times(k)} "
            f"and the time it flows is {_times(k2)}.",
        }[variant.id]
    return None


def _nature_wrongs(
    answer: dict[str, Any], label: str, v: Fraction, family: str
) -> list[tuple[str, str]]:
    real, orient, size = (x.strip() for x in label.split(","))
    swap = {"real": "virtual", "virtual": "real", "inverted": "erect", "erect": "inverted",
            "magnified": "diminished", "diminished": "magnified"}  # fmt: skip
    return [
        (_NAT_IDS[0], f"{swap[real]}, {orient}, {size}"),
        (_NAT_IDS[1], f"{real}, {swap[orient]}, {size}"),
        (_NAT_IDS[2], f"{real}, {orient}, {swap[size]}"),
    ]


_NAT_IDS = (
    "PHY.MC.LIGHT.V_SIGN_MEANING_REVERSED",
    "PHY.MC.LIGHT.MAG_SIGN_MEANING_REVERSED",
    "PHY.MC.LIGHT.SIZE_MEANING_REVERSED",
)


def _pick_wrongs(
    model: Model,
    variant: Variant,
    params: Mapping[str, Any],
    env: Mapping[str, Fraction],
    raw: Mapping[str, Fraction],
    key_val: Fraction,
    key_unit: str,
    fa: Fraction,
) -> list[tuple[str, Fraction]] | str:
    wenv: dict[str, Fraction] = {n: env[n] for n in (*variant.needs, *model.consts)}
    if model.id == "LIGHT.SIGN":
        wenv["s"] = env["s"]
    for n, v in raw.items():
        wenv[f"{n}_r"] = v
    wenv["K"], wenv["FA"] = key_val, fa
    candidates = list(variant.wrongs)
    if model.extra_wrongs:
        candidates += list(model.extra_wrongs(params, variant))
    factor = fa if fa > 1 else 1 / fa
    if model.auto_slips and factor in (10, 100, 1000, 10**6):
        candidates += [
            (f"{model.mc_prefix}.UNIT_PREFIX_SLIP", f"@K*{factor}"),
            (f"{model.mc_prefix}.UNIT_PREFIX_SLIP", f"@K/{factor}"),
        ]
    scored: list[tuple[str, Fraction]] = []
    for mc, expr in candidates:
        try:
            val = evaluate(expr[1:], wenv) if expr.startswith("@") else evaluate(expr, wenv) / fa
        except ExprError:
            continue
        if val == key_val or val == 0:
            continue
        if not model.signed and val < 0:
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


_SIGN_RULES = {
    "object_distance": "A real object is on the side the light comes from, against the direction of the light, so its distance is negative.",  # noqa: E501
    (
        "mirror",
        "image_real",
    ): "A real image forms in front of a mirror, against the direction of the incident light, so its distance is negative.",  # noqa: E501
    (
        "mirror",
        "image_virtual",
    ): "A virtual image forms behind a mirror, along the direction of the incident light, so its distance is positive.",  # noqa: E501
    (
        "lens",
        "image_real",
    ): "A real image forms on the far side of a lens, along the direction of the light, so its distance is positive.",  # noqa: E501
    (
        "lens",
        "image_virtual",
    ): "A virtual image forms on the same side of a lens as the object, so its distance is negative.",  # noqa: E501
}


def _sign_rule(device: str, role: str) -> str:
    fam = "mirror" if device.endswith("mirror") else "lens"
    if role == "focal":
        sign = "positive" if device.startswith("convex") else "negative"
        return f"A {device.replace('_', ' ')} has a {sign} focal length."
    return _SIGN_RULES.get(role) or _SIGN_RULES[(fam, role)]  # type: ignore[return-value]


def _hints_and_steps(
    model: Model,
    variant: Variant,
    noun: str,
    env: Mapping[str, Fraction],
    shown: Mapping[str, str],
    conversions: list[str],
    signs: list[str],
    key_unit: str,
    key_val: Fraction,
    nature: str | None,
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
    elif nature:
        h2 = "Work out v first, then m, and only then read what their signs say."
    elif plan:
        h2 = "Work through the plan one step at a time."
    else:
        h2 = f"The relation already gives the {noun} directly, so decide what to substitute."
    if conversions or fa != 1:
        h2 += " Change every quantity to SI units first, and change back at the end if asked."
    if model.signed and model.id != "LIGHT.SIGN":
        h2 += " Give each distance its sign by the Cartesian convention before you substitute."
    lead = ""
    if conversions:
        lead = "Write " + _words_list([c.replace(" = ", " as ") for c in conversions]) + ", then "
    h3 = (
        f"First step: {lead}write {find} = {_pretty_expr(variant.expr)}, where {find} is the {noun}, "
        "with the values in place, one quantity at a time."
    )
    steps = [f"{'Plan' if plan else 'Write the relation'}: {variant.formula}."]
    if conversions or signs:
        parts = conversions if not signs else signs
        steps.append("Put each quantity in SI units" + (" with its sign" if signs else "")
                     + ": " + "; ".join(parts) + ".")  # fmt: skip
    if variant.rearr:
        steps.append(f"Get the {noun} alone: {variant.rearr}.")
    si_unit = model.syms[find]
    si_text = quantity_text(env[find], si_unit)
    sub = _pretty_expr(_sub_numbers(variant.expr, env))
    if model.id == "LIGHT.SIGN":
        device, role = str(params["case"]).split(":")
        h1 = "Plan the steps: decide which side of the pole or centre the quantity is on, then give the magnitude the matching sign."  # noqa: E501
        h2 = "Distances measured against the direction of the incident light are negative, and those along it are positive. Focal length follows the type of mirror or lens."  # noqa: E501
        h3 = "First step: say whether this quantity is on the side the light comes from or on the other side, or what type of mirror or lens it is."  # noqa: E501
        steps = [_sign_rule(device, role)]
    elif model.id in ("ELEC.RESIST_SCALE", "ELEC.POWER_SCALE"):
        h3 = ("First step: write down the number each quantity is multiplied by, using 2 for doubled "
              "and 1/2 for halved, then combine them using the relation.")  # fmt: skip
        steps.append(f"Combine the numbers: {sub} = {quantity_text(env[find], si_unit)}.")
    else:
        steps.append(f"Substitute: {find} = {sub}.")
        steps.append(f"Calculate: {find} = {si_text}.")
    if (fa != 1 or key_unit != si_unit) and model.id not in (
        "ELEC.RESIST_SCALE",
        "ELEC.POWER_SCALE",
    ):  # noqa: E501
        steps.append(
            f"Give it in {unit_text(key_unit) or key_unit}: {quantity_text(key_val, key_unit)}."
        )  # noqa: E501
    if nature:
        steps.append(
            "Read the sign of v and of m = "
            + ("-v / u" if variant.nature == "mirror" else "v / u")
            + f": the image is {nature}."
        )
        steps.append(f"So the image is {nature}.")
    else:
        steps.append(f"So the {noun} is {quantity_text(key_val, key_unit)}.")
    return [h1, h2, h3], steps


def parse_value(text: str) -> tuple[Fraction, str] | None:
    """A student's response as (number, unit text). None when no number can be read."""
    cleaned = text.strip().replace("−", "-").replace(",", "")
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*(?:x\s*10\^(-?\d+))?\s*([A-Za-zΩ/^*0-9 ]*)$", cleaned)
    if not m:
        return None
    value = frac(m.group(1))
    if m.group(2):
        value *= Fraction(10) ** int(m.group(2))
    return value, m.group(3).strip().replace("Ω", "ohm")


__all__ = ["MARKS", "Built", "build", "parse_value"]
