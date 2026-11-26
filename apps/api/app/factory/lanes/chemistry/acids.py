# ruff: noqa: E501
"""Chapter: Acids, Bases and Salts. pH with school values, neutralisation, salt formulas.

pH items use only concentrations that are exact powers of ten, so every answer is an exact
integer (no logarithm tables). Each has two independent methods: exponent bookkeeping in exact
fractions, and a Decimal base-10 logarithm of the stated concentration (exact for powers of ten).
Neutralisation volume is a genuine exact linear relation in the kernel; the mass and mole items
go to the kernel's stoichiometry verifier. Salt formulas are checked by balancing the whole
acid + base -> salt + water equation in the kernel.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal
from fractions import Fraction
from typing import Any

import sympy

from app.factory.kernel.constants import atomic_mass
from app.factory.lanes.chemistry import tables as T
from app.factory.lanes.chemistry.balance import _eq, _sides, solve_own, solve_sympy
from app.factory.lanes.chemistry.core import (
    Built,
    Family,
    FnMethod,
    IllPosed,
    balance_spec,
    difficulty,
    linear_answer,
    linear_spec,
    pick,
)
from app.factory.lanes.chemistry.formula import atoms
from app.factory.lanes.chemistry.ions import crisscross, formula_from_counts, search_smallest

PKW = 14  # pH + pOH = 14 at room temperature (school value)


def _sci(exp: int) -> str:
    return f"1 x 10^{exp} mol/L"


def _plain(exp: int) -> str:
    """The concentration 10^exp as a plain decimal string, exp <= 0."""
    return "1" if exp == 0 else "0." + "0" * (-exp - 1) + "1"


def _exp_by_zeros(text: str) -> int:
    """Exponent of ten of '0.001' by counting decimal places (no logarithm)."""
    if text == "1":
        return 0
    m = re.fullmatch(r"0\.(0*)1", text)
    if not m:
        raise ValueError(f"not a power of ten: {text}")
    return -(len(m.group(1)) + 1)


def _exp_by_log(text: str) -> int:
    value = Decimal(text).log10()
    if value != value.to_integral_value():
        raise ValueError("not a power of ten")
    return int(value)


# ---------------------------------------------------------------- pH from concentration / pOH


class PhConversion(Family):
    """pH, pOH and ion concentration conversions for solutions at 25 degrees C."""

    id = "ph_conv"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        kind, k = str(p["kind"]), int(p["k"])
        if not 1 <= k <= 13:
            raise IllPosed("out_of_range")
        w: list[tuple[str, int | None, str]]
        chem_given: dict[str, Any]
        if kind == "pH_from_H":
            given = _plain(-k)
            stem = f"The hydrogen ion concentration of a solution is {_sci(-k)}. What is the pH of the solution?"
            var, key, const, chem_given = "pH", k, k, {"kind": kind, "conc": given}
            w = [("CHEM.MC.PH.SIGN_OF_EXPONENT_KEPT", -k, str(-k)), ("CHEM.MC.PH.OH_FOR_H", PKW - k, str(PKW - k)),
                 ("CHEM.MC.PH.POWER_MISCOUNT", k + 1, str(k + 1)), ("CHEM.MC.PH.POWER_MISCOUNT", k - 1, str(k - 1)),
                 ("CHEM.MC.PH.CONCENTRATION_READ_AS_PH", 10**k, str(10**k))]  # fmt: skip
            key_text = str(k)
            hints = [
                "pH is found from the power of ten of the hydrogen ion concentration. Look at the small raised number only.",
                "The pH is a positive number for these solutions, so think about what the minus sign in the power does.",
                "Write the concentration as 1 x 10 to a power. Ignore the minus sign of the power to get the pH.",
            ]
            steps = [
                f"The concentration is 1 x 10^{-k} mol/L.",
                "pH = -log of the hydrogen ion concentration, which for a power of ten is the power with its sign changed.",
                f"So pH = {k}.",
            ]
            tokens = [key_text]
        elif kind == "H_from_pH":
            stem = f"A solution has pH {k}. What is its hydrogen ion concentration?"
            var, key, const, chem_given = "e", -k, -k, {"kind": kind, "pH": k}
            w = [("CHEM.MC.PH.SIGN_OF_EXPONENT_DROPPED", k, _sci(k)), ("CHEM.MC.PH.OH_FOR_H", -(PKW - k), _sci(-(PKW - k))),
                 ("CHEM.MC.PH.POWER_MISCOUNT", -(k + 1), _sci(-(k + 1))), ("CHEM.MC.PH.POWER_MISCOUNT", -(k - 1), _sci(-(k - 1))),
                 ("CHEM.MC.PH.PH_READ_AS_CONCENTRATION", None, f"{k} mol/L")]  # fmt: skip
            key_text = _sci(-k)
            hints = [
                "The hydrogen ion concentration is a power of ten, and the pH tells you which power.",
                "A larger pH means fewer hydrogen ions, so the concentration is a small number. Think about the sign of the power.",
                "Write 1 x 10 to a power, where the power is the pH with its sign changed.",
            ]
            steps = [
                f"pH = -log of the hydrogen ion concentration, so the concentration is 10 to the power minus {k}.",
                f"The concentration is 1 x 10^{-k} mol/L.",
            ]
            tokens = [key_text]
        elif kind == "pOH_from_pH":
            stem = f"A solution has pH {k}. What is its pOH at room temperature?"
            var, key, const, chem_given = "pOH", PKW - k, PKW - k, {"kind": kind, "pH": k}
            w = [("CHEM.MC.PH.POH_SAME_AS_PH", k, str(k)), ("CHEM.MC.PH.SEVEN_USED", 7 - k, str(7 - k)),
                 ("CHEM.MC.PH.SIGN_OF_EXPONENT_KEPT", k - PKW, str(k - PKW)), ("CHEM.MC.PH.PH_PLUS_POH_NOT_14", PKW + k, str(PKW + k)),
                 ("CHEM.MC.PH.POWER_MISCOUNT", PKW - k + 1, str(PKW - k + 1))]  # fmt: skip
            key_text = str(PKW - k)
            hints = [
                "For any water solution at room temperature, pH and pOH add up to a fixed number.",
                "Use the fixed total of pH and pOH. Do not use the neutral point instead.",
                "Take the pH away from the fixed total.",
            ]
            steps = [f"At room temperature pH + pOH = {PKW}.", f"pOH = {PKW} - {k} = {PKW - k}."]
            tokens = [key_text]
        elif kind == "pH_from_OH":
            given = _plain(-k)
            stem = f"The hydroxide ion concentration of a solution is {_sci(-k)}. What is the pH of the solution?"
            var, key, const, chem_given = "pH", PKW - k, PKW - k, {"kind": kind, "conc": given}
            w = [("CHEM.MC.PH.POH_REPORTED_AS_PH", k, str(k)), ("CHEM.MC.PH.SEVEN_USED", 7 + k if 7 + k <= 20 else 7 - k, str(7 + k if 7 + k <= 20 else 7 - k)),
                 ("CHEM.MC.PH.SIGN_OF_EXPONENT_KEPT", k - PKW, str(k - PKW)), ("CHEM.MC.PH.POWER_MISCOUNT", PKW - k + 1, str(PKW - k + 1)),
                 ("CHEM.MC.PH.PH_PLUS_POH_NOT_14", PKW + k, str(PKW + k))]  # fmt: skip
            key_text = str(PKW - k)
            hints = [
                "A hydroxide ion concentration gives pOH first, and only then the pH.",
                "Find the pOH from the power of ten, then use the fixed total of pH and pOH at room temperature.",
                "pOH comes from the power with its minus sign ignored. Subtract it from the fixed total.",
            ]
            steps = [
                f"pOH comes from the power of ten: pOH = {k}.",
                f"pH + pOH = {PKW}, so pH = {PKW} - {k} = {PKW - k}.",
            ]
            tokens = [key_text]
        elif kind == "OH_from_pH":
            stem = f"A solution has pH {k}. What is its hydroxide ion concentration at room temperature?"
            var, key, const, chem_given = "e", k - PKW, k - PKW, {"kind": kind, "pH": k}
            w = [("CHEM.MC.PH.OH_FOR_H", -k, _sci(-k)), ("CHEM.MC.PH.SIGN_OF_EXPONENT_DROPPED", PKW - k, _sci(PKW - k)),
                 ("CHEM.MC.PH.POWER_MISCOUNT", k - PKW - 1, _sci(k - PKW - 1)), ("CHEM.MC.PH.POWER_MISCOUNT", k - PKW + 1, _sci(k - PKW + 1)),
                 ("CHEM.MC.PH.PH_PLUS_POH_NOT_14", -(PKW + k), _sci(-(PKW + k)))]  # fmt: skip
            key_text = _sci(k - PKW)
            hints = [
                "First find the pOH from the pH, then turn the pOH into a power of ten.",
                "pH and pOH add up to a fixed number at room temperature. The hydroxide concentration is 1 x 10 to minus pOH.",
                "Subtract the pH from the fixed total to get the pOH, then write the concentration with that power.",
            ]
            steps = [
                f"pOH = {PKW} - {k} = {PKW - k}.",
                f"The hydroxide ion concentration is 1 x 10^{-(PKW - k)} mol/L.",
            ]
            tokens = [key_text]
        else:
            raise IllPosed("unknown_kind")
        answer = linear_answer(var, key)
        wrong = []
        for mc, val, text in w:
            if val is None:
                rec = {"values": {var: "none"}, "shown": text}
            else:
                rec = linear_answer(var, val)
            if text != key_text:
                wrong.append((mc, rec, text))
        spec = linear_spec(var, 1, const, {"family": self.id, **chem_given})
        return Built(
            spec=spec,
            answer=answer,
            witness=linear_answer(var, key),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=key_text,
            tokens=tokens,
            difficulty=difficulty(
                0.3, steps=len(steps) - 1 + (kind in ("pH_from_OH", "OH_from_pH"))
            ),
            role="procedure",
            prediction="Before you work it out, is the answer a small or a large number, and is it positive or negative?",
            methods=[
                FnMethod("chem.ph_exponent", "chem.exponent_bookkeeping", "ph_scale", _ph_m1),
                FnMethod("chem.ph_decimal_log", "chem.decimal_log10", "ph_scale", _ph_m2),
            ],
            slug=f"{kind}.{k}",
        )


def _ph_m1(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    kind = c["kind"]
    if kind == "pH_from_H":
        return linear_answer("pH", -_exp_by_zeros(c["conc"]))
    if kind == "H_from_pH":
        return linear_answer("e", -int(c["pH"]))
    if kind == "pOH_from_pH":
        return linear_answer("pOH", PKW - int(c["pH"]))
    if kind == "pH_from_OH":
        return linear_answer("pH", PKW + _exp_by_zeros(c["conc"]))
    return linear_answer("e", int(c["pH"]) - PKW)


def _ph_m2(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    kind = c["kind"]
    if kind == "pH_from_H":
        return linear_answer("pH", -_exp_by_log(c["conc"]))
    if kind == "H_from_pH":
        conc = Decimal(10) ** (-int(c["pH"]))  # exact power of ten as a Decimal
        return linear_answer("e", _exp_by_log(format(conc, "f")))
    if kind == "pOH_from_pH":
        h = Decimal(10) ** (-int(c["pH"]))
        kw = Decimal(10) ** (-PKW)
        return linear_answer("pOH", -_exp_by_log(format(kw / h, "f")))
    if kind == "pH_from_OH":
        oh = Decimal(c["conc"])
        h = Decimal(10) ** (-PKW) / oh
        return linear_answer("pH", -_exp_by_log(format(h, "f")))
    oh = Decimal(10) ** (-PKW) / (Decimal(10) ** (-int(c["pH"])))
    return linear_answer("e", _exp_by_log(format(oh, "f")))


# ---------------------------------------------------------------- strong acid / base solutions

STRONG = (
    ("HCl", "hydrochloric acid", 1, "acid"),
    ("HNO3", "nitric acid", 1, "acid"),
    ("H2SO4", "sulphuric acid", 2, "acid"),
    ("NaOH", "sodium hydroxide", 1, "base"),
    ("KOH", "potassium hydroxide", 1, "base"),
    ("Ca(OH)2", "calcium hydroxide", 2, "base"),
    ("Ba(OH)2", "barium hydroxide", 2, "base"),
)


def _power_of_ten_exp(x: Fraction) -> int | None:
    e = 0
    while x < 1:
        x *= 10
        e -= 1
    while x > 1:
        if x % 10 != 0 and x != 10:
            return None
        x /= 10
        e += 1
    return e if x == 1 else None


class PhStrong(Family):
    """pH of a fully ionised acid or base of stated concentration (ion count matters)."""

    id = "ph_strong"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        formula, name, valence, role = STRONG[int(p["sub"])]
        c = Fraction(str(p["c"]))
        ion = c * valence
        e = _power_of_ten_exp(ion)
        if e is None or not (-13 <= e <= -1):
            raise IllPosed("ion_concentration_not_a_power_of_ten_in_range")
        k = -e
        key = k if role == "acid" else PKW - k
        particle = "hydrogen" if role == "acid" else "hydroxide"
        shown = formula if "(" not in formula else None
        subject = f"{name}, {shown}," if shown else name
        stem = f"A {p['c']} mol/L solution of {subject} is fully ionised in water. What is its pH at room temperature?"
        ignore_valence = _power_of_ten_exp(c)
        w: list[tuple[str, int, str]] = []
        if ignore_valence is not None and valence > 1:
            ik = -ignore_valence
            w.append(
                (
                    "CHEM.MC.PH.IONS_PER_FORMULA_IGNORED",
                    ik if role == "acid" else PKW - ik,
                    str(ik if role == "acid" else PKW - ik),
                )
            )
        if role == "acid":
            w += [
                ("CHEM.MC.PH.OH_FOR_H", PKW - k, str(PKW - k)),
                ("CHEM.MC.PH.SIGN_OF_EXPONENT_KEPT", -k, str(-k)),
                ("CHEM.MC.PH.POWER_MISCOUNT", k + 1, str(k + 1)),
                ("CHEM.MC.PH.POWER_MISCOUNT", k - 1, str(k - 1)),
            ]
        else:
            w += [
                ("CHEM.MC.PH.POH_REPORTED_AS_PH", k, str(k)),
                ("CHEM.MC.PH.SIGN_OF_EXPONENT_KEPT", -k, str(-k)),
                ("CHEM.MC.PH.POWER_MISCOUNT", PKW - k + 1, str(PKW - k + 1)),
                ("CHEM.MC.PH.POWER_MISCOUNT", PKW - k - 1, str(PKW - k - 1)),
            ]
        w = [x for x in w if x[2] != str(key)]
        hints = [
            f"Find the concentration of {particle} ions first. Count how many {particle} ions one unit of the substance gives.",
            f"Multiply the stated concentration by the number of {particle} ions per unit to get the {particle} ion concentration.",
            "Turn that concentration into a power of ten. For a base, find the pOH first and then use the fixed total of pH and pOH.",
        ]
        steps = [
            f"One unit of {name} gives {valence} {particle} ion(s), so the {particle} ion concentration is {p['c']} x {valence} = {ion} mol/L.",
            f"That is 1 x 10^{-k} mol/L, so the {'pH' if role == 'acid' else 'pOH'} is {k}.",
        ]
        if role == "base":
            steps.append(f"pH = {PKW} - {k} = {key}.")
        else:
            steps.append(f"So pH = {key}.")
        chem = {"family": self.id, "role": role, "valence": valence, "conc": str(p["c"])}
        return Built(
            spec=linear_spec("pH", 1, key, chem),
            answer=linear_answer("pH", key),
            witness=linear_answer("pH", key),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=[(mc, linear_answer("pH", v), t) for mc, v, t in w],
            key_text=str(key),
            tokens=[str(key)],
            difficulty=difficulty(0.45, steps=2 + (role == "base") + (valence > 1)),
            role="apply",
            prediction="Before you calculate, should the pH be below 7 or above 7?",
            methods=[
                FnMethod(
                    "chem.strong_fraction", "chem.exponent_bookkeeping", "ph_scale", _strong_m1
                ),
                FnMethod("chem.strong_decimal_log", "chem.decimal_log10", "ph_scale", _strong_m2),
            ],
            slug=f"{int(p['sub'])}.{str(p['c']).replace('.', 'p')}",
        )


def _strong_m1(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    ion = Fraction(c["conc"]) * int(c["valence"])
    e = _power_of_ten_exp(ion)
    assert e is not None
    return linear_answer("pH", -e if c["role"] == "acid" else PKW + e)


def _strong_m2(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    ion = Decimal(c["conc"]) * int(c["valence"])
    x = int(ion.log10())
    if Decimal(10) ** x != ion:
        raise ValueError("not a power of ten")
    poh_or_ph = -x
    return linear_answer("pH", poh_or_ph if c["role"] == "acid" else PKW - poh_or_ph)


# ---------------------------------------------------------------- dilution


class PhDilution(Family):
    id = "ph_dilution"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        role, p0, m = str(p["role"]), int(p["p0"]), int(p["m"])
        if role == "acid" and not (1 <= p0 and p0 + m <= 6):
            raise IllPosed("acid_would_leave_the_acid_range")
        if role == "base" and not (p0 >= 8 and p0 - m >= 8 and p0 <= 13):
            raise IllPosed("base_would_leave_the_base_range")
        factor = 10**m
        key = p0 + m if role == "acid" else p0 - m
        word = "acid" if role == "acid" else "base"
        stem = pick(
            [
                f"A solution of a strong {word} has pH {p0}. Pure water is added until its volume is {factor} times larger. What is the new pH? (Assume the water itself adds no ions.)",
                f"The pH of a strong {word} is {p0}. It is diluted with pure water to {factor} times its original volume. What is the pH now? Ignore any ions from the water.",
                f"A strong {word} with pH {p0} is poured into pure water until the total volume has grown {factor} times. Find the new pH. The water adds no ions.",
            ],
            p,
        )
        w = [
            ("CHEM.MC.PH.DILUTION_DIRECTION_REVERSED", p0 - m if role == "acid" else p0 + m, None),
            ("CHEM.MC.PH.PH_SCALED_BY_FACTOR", p0 * factor, None),
            ("CHEM.MC.PH.FACTOR_ADDED_TO_PH", p0 + factor, None),
            ("CHEM.MC.PH.NO_CHANGE_ON_DILUTION", p0, None),
            ("CHEM.MC.PH.SEVEN_USED", 7, None),
            ("CHEM.MC.PH.POWER_MISCOUNT", key + 1, None),
        ]
        wrong = [(mc, linear_answer("x", v), str(v)) for mc, v, _ in w if v != key and v >= 0]
        hints = [
            "Diluting a solution lowers the concentration of the ions that make it acidic or basic. Which way does that push the pH?",
            "Each time the volume becomes ten times larger, the concentration of ions becomes ten times smaller, and the pH moves by one unit.",
            "Work out how many times the volume is multiplied by ten, then move the pH by that many units in the right direction.",
        ]
        steps = [
            f"The volume is {factor} times larger, so the ion concentration is {factor} times smaller.",
            f"A change by a factor of {factor} moves the pH by {m} unit(s).",
            f"A diluted {word} has its pH move towards 7, so the new pH is {key}.",
        ]
        chem = {"family": self.id, "role": role, "p0": p0, "factor": factor}
        return Built(
            spec=linear_spec("x", 1, key, chem),
            answer=linear_answer("x", key),
            witness=linear_answer("x", key),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=str(key),
            tokens=[str(key)],
            difficulty=difficulty(0.5, steps=2),
            role="apply",
            prediction="Before you calculate, will the pH go up or down, and will it cross 7?",
            methods=[
                FnMethod(
                    "chem.dilution_exponent", "chem.exponent_bookkeeping", "ph_scale", _dil_m1
                ),
                FnMethod("chem.dilution_decimal_log", "chem.decimal_log10", "ph_scale", _dil_m2),
            ],
            slug=f"{role}.{p0}.{m}",
        )


def _dil_m1(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    steps = len(str(c["factor"])) - 1
    return linear_answer("x", c["p0"] + steps if c["role"] == "acid" else c["p0"] - steps)


def _dil_m2(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    p0, factor = int(c["p0"]), Decimal(int(c["factor"]))
    if c["role"] == "acid":
        h = Decimal(10) ** (-p0) / factor
        return linear_answer("x", -int(h.log10()))
    oh = Decimal(10) ** (-(PKW - p0)) / factor
    return linear_answer("x", PKW + int(oh.log10()))


# ---------------------------------------------------------------- ratio of ion concentrations


class PhRatio(Family):
    id = "ph_ratio"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, b = int(p["a"]), int(p["b"])
        if not (1 <= a < b <= 13):
            raise IllPosed("need_a_less_than_b")
        d = b - a
        key = 10**d
        stem = pick(
            [
                f"Solution X has pH {a} and solution Y has pH {b}. How many times larger is the hydrogen ion concentration in X than in Y?",
                f"Solution X has a pH of {a}; solution Y has a pH of {b}. X has how many times more hydrogen ions per litre than Y?",
                f"Two solutions are tested. X reads pH {a} and Y reads pH {b}. By what factor is the hydrogen ion concentration of X greater than that of Y?",
            ],
            p,
        )
        w = [
            ("CHEM.MC.PH.DIFFERENCE_NOT_POWER", d, str(d)),
            ("CHEM.MC.PH.RATIO_OF_PH_VALUES", None, f"{b}/{a}"),
            ("CHEM.MC.PH.TIMES_TEN_PER_UNIT", 10 * d, str(10 * d)),
            ("CHEM.MC.PH.RATIO_INVERTED", None, f"1/{key}"),
            ("CHEM.MC.PH.POWER_MISCOUNT", 10 ** (d + 1), str(10 ** (d + 1))),
            ("CHEM.MC.PH.POWER_MISCOUNT", 10 ** (d - 1) if d > 1 else None, str(10 ** (d - 1))),
        ]
        wrong = [
            (mc, {"values": {"d": "none"}, "shown": t}, t)
            for mc, v, t in w
            if (v is None or v != key)
            and t != str(key)
            and not (v is None and mc == "CHEM.MC.PH.POWER_MISCOUNT")
        ]
        hints = [
            "The pH scale is a logarithm scale: each step of one pH unit changes the ion concentration by the same factor.",
            "Find the difference between the two pH values, then ask what factor that many steps make.",
            "A difference of one pH unit is a factor of 10. A bigger difference multiplies that factor again for each unit.",
        ]
        steps = [
            f"The two pH values differ by {b} - {a} = {d}.",
            f"Each pH unit is a factor of 10 in concentration, so the factor is 10^{d} = {key}.",
            "The solution with the smaller pH has the larger hydrogen ion concentration.",
        ]
        return Built(
            spec=linear_spec("d", 1, d, {"family": self.id, "a": a, "b": b}),
            answer=linear_answer("d", d),
            witness=linear_answer("d", d),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=str(key),
            tokens=[str(key)],
            difficulty=difficulty(0.55, steps=2),
            role="apply",
            prediction="Before you calculate, will the answer be small like 5 or very large?",
            methods=[
                FnMethod(
                    "chem.ratio_exponent",
                    "chem.exponent_bookkeeping",
                    "ph_scale",
                    lambda s: linear_answer("d", int(s["chem"]["b"]) - int(s["chem"]["a"])),
                ),
                FnMethod("chem.ratio_decimal", "chem.decimal_log10", "ph_scale", _ratio_m2),
            ],
            slug=f"{a}.{b}",
        )


def _ratio_m2(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    ratio = (Decimal(10) ** (-int(c["a"]))) / (Decimal(10) ** (-int(c["b"])))
    return linear_answer("d", int(ratio.log10()))


# ---------------------------------------------------------------- acidic, neutral or basic

CLASS_LABEL = {-1: "Acidic", 0: "Neutral", 1: "Basic"}
CLASS_OPTIONS = ("Acidic", "Neutral", "Basic", "It depends on the substance, not on the number")


class PhClassify(Family):
    id = "ph_classify"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        q, given = int(p["pH"]), str(p["given"])
        if not 0 <= q <= 14:
            raise IllPosed("range")
        if given != "pH" and not 1 <= q <= 13:
            raise IllPosed("concentration_form_needs_pH_1_to_13")
        sign = -1 if q < 7 else (0 if q == 7 else 1)
        key = CLASS_LABEL[sign]
        if given == "pH":
            stem = f"A solution has pH {q}. Which description fits it?"
            chem = {"family": self.id, "given": "pH", "pH": q}
        elif given == "H":
            stem = f"A solution has a hydrogen ion concentration of {_sci(-q)}. Which description fits it?"
            chem = {"family": self.id, "given": "H", "conc": _plain(-q)}
        else:
            stem = f"A solution has a hydroxide ion concentration of {_sci(-(PKW - q))}. Which description fits it?"
            chem = {"family": self.id, "given": "OH", "conc": _plain(-(PKW - q))}
        answer = linear_answer("s", sign)
        wrong = []
        for other_sign, label in CLASS_LABEL.items():
            if other_sign != sign:
                mc = (
                    "CHEM.MC.PH.SCALE_READ_BACKWARDS"
                    if {sign, other_sign} == {-1, 1}
                    else "CHEM.MC.PH.NEUTRAL_POINT_MISPLACED"
                )
                wrong.append((mc, linear_answer("s", other_sign), label))
        wrong.append(
            (
                "CHEM.MC.PH.NEEDS_NAME_OF_SUBSTANCE",
                {"values": {"s": "none"}, "shown": CLASS_OPTIONS[3]},
                CLASS_OPTIONS[3],
            )
        )
        hints = [
            "On the pH scale one particular number separates the two kinds of solution. Which number is it?",
            "Compare the hydrogen ion concentration with the hydroxide ion concentration: whichever is larger decides the character.",
            "Find the pH if it is not given directly, then compare it with the neutral point.",
        ]
        steps = [
            "Find the pH of the solution (use the concentration's power of ten if needed).",
            f"The neutral point at room temperature is pH 7; a solution with pH {q} is {key.lower()}.",
        ]
        return Built(
            spec=linear_spec("s", 1, sign, chem),
            answer=answer,
            witness=linear_answer("s", sign),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=key,
            tokens=[key, key.lower()],
            difficulty=difficulty(0.2, steps=1 + (given != "pH")),
            role="recall",
            prediction="Before you decide, is the number below, equal to or above the neutral point?",
            methods=[
                FnMethod("chem.classify_threshold", "chem.threshold_rule", "ph_scale", _cls_m1),
                FnMethod("chem.classify_ions", "chem.ion_comparison", "ph_scale", _cls_m2),
            ],
            slug=f"{given}.{q}",
        )


def _cls_m1(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    if c["given"] == "pH":
        q = int(c["pH"])
    elif c["given"] == "H":
        q = -_exp_by_zeros(c["conc"])
    else:
        q = PKW + _exp_by_zeros(c["conc"])
    return linear_answer("s", -1 if q < 7 else (0 if q == 7 else 1))


def _cls_m2(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    kw = Decimal(10) ** (-PKW)
    if c["given"] == "pH":
        h = Decimal(10) ** (-int(c["pH"]))
    elif c["given"] == "H":
        h = Decimal(c["conc"])
    else:
        h = kw / Decimal(c["conc"])
    oh = kw / h
    return linear_answer("s", -1 if h > oh else (0 if h == oh else 1))


# ---------------------------------------------------------------- neutralisation volume


class NeutralVolume(Family):
    """Volume of base that exactly neutralises an acid: basicity x moles of acid = acidity x moles of base."""

    id = "neutral_volume"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        acid = T.ACIDS[int(p["a"])]
        base = T.BASES[int(p["b"])]
        if base[3] > 2:
            raise IllPosed("base_acidity_over_two_outside_the_item")
        ca, va, cb = Fraction(str(p["ca"])), Fraction(str(p["va"])), Fraction(str(p["cb"]))
        a_n, b_n = acid[3], base[3]
        vb = a_n * ca * va / (b_n * cb)
        if vb.denominator != 1 or not 5 <= vb <= 200:
            raise IllPosed("base_volume_not_a_whole_number_of_ml")
        stem = f"{p['va']} mL of {p['ca']} mol/L {acid[1]} is exactly neutralised by a solution of {base[1]} of concentration {p['cb']} mol/L. What volume of the {base[1]} solution is needed?"
        key = int(vb)
        text = lambda v: f"{v} mL"  # noqa: E731
        alts = {
            "CHEM.MC.NEUT.ACID_BASICITY_IGNORED": ca * va / (b_n * cb),
            "CHEM.MC.NEUT.BASE_ACIDITY_IGNORED": a_n * ca * va / cb,
            "CHEM.MC.NEUT.EQUAL_VOLUMES_ASSUMED": va,
            "CHEM.MC.NEUT.CONCENTRATION_RATIO_INVERTED": a_n * cb * va / (b_n * ca),
            "CHEM.MC.NEUT.BASICITY_RATIO_INVERTED": b_n * ca * va / (a_n * cb),
            "CHEM.MC.NEUT.TOTAL_VOLUME_GIVEN": va + vb,
            "CHEM.MC.NEUT.ACID_MILLIMOLES_GIVEN": ca * va,
        }
        wrong = []
        for mc, v in alts.items():
            if v != vb and v > 0 and v.denominator == 1:
                wrong.append((mc, linear_answer("V", int(v)), text(int(v))))
        for mc, v in alts.items():
            if v != vb and v > 0 and v.denominator != 1:
                shown = f"{float(v):g}"
                wrong.append((mc, linear_answer("V", str(v)), text(shown)))
        hints = [
            "At the point of exact neutralisation, the number of moles of hydrogen ions equals the number of moles of hydroxide ions.",
            "Moles of a substance = concentration x volume. Count how many hydrogen ions one acid unit gives and how many hydroxide ions one base unit gives.",
            "Write: hydrogen ions per acid unit times acid moles equals hydroxide ions per base unit times base moles, then solve for the base volume.",
        ]
        steps = [
            f"Moles of {acid[1]} = {p['ca']} x {p['va']}/1000 mol; each unit gives {a_n} hydrogen ion(s).",
            f"Each unit of {base[1]} gives {b_n} hydroxide ion(s).",
            f"{a_n} x {p['ca']} x {p['va']} = {b_n} x {p['cb']} x V, so V = {key} mL.",
        ]
        chem = {
            "family": self.id,
            "acid_n": a_n,
            "base_n": b_n,
            "ca": str(p["ca"]),
            "va": str(p["va"]),
            "cb": str(p["cb"]),
        }
        spec = linear_spec("V", str(b_n * cb), str(a_n * ca * va), chem)
        return Built(
            spec=spec,
            answer=linear_answer("V", key),
            witness=linear_answer("V", key),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=text(key),
            tokens=[str(key), text(key)],
            difficulty=difficulty(0.55, steps=3 + (a_n > 1) + (b_n > 1)),
            role="apply",
            prediction="Before you calculate, will you need more or less base solution than the volume of acid?",
            methods=[
                FnMethod("chem.neutral_moles", "chem.mole_balance", "neutralisation", _neut_m1),
                FnMethod("chem.neutral_normality", "chem.normality", "neutralisation", _neut_m2),
            ],
            slug=f"{int(p['a'])}.{int(p['b'])}.{str(p['ca']).replace('.', 'p')}.{p['va']}.{str(p['cb']).replace('.', 'p')}",
        )


def _neut_m1(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    moles_h = int(c["acid_n"]) * Fraction(c["ca"]) * Fraction(c["va"]) / 1000
    litres = moles_h / (int(c["base_n"]) * Fraction(c["cb"]))
    return linear_answer("V", _clean(litres * 1000))


def _neut_m2(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    na = Decimal(c["ca"]) * int(c["acid_n"])  # normality of the acid (equivalents per litre)
    nb = Decimal(c["cb"]) * int(c["base_n"])
    ml = na * Decimal(c["va"]) / nb
    return linear_answer("V", _clean(Fraction(ml)))


def _clean(x: Fraction) -> str:
    return str(int(x)) if x.denominator == 1 else str(x)


# ---------------------------------------------------------------- neutralisation mass and moles


def molar_mass(formula: str) -> Fraction:
    return sum((Fraction(atomic_mass(e)) * n for e, n in atoms(formula).items()), Fraction(0))


def salt_formula(acid: tuple[str, str, str, int], base: tuple[str, str, str, int]) -> str:
    cation = next(c for c in T.CATIONS if c[0] == base[2])
    anion = next(a for a in T.ANIONS if a[0] == acid[2])
    m, n = crisscross(cation[1], anion[1])
    return formula_from_counts(cation[0], m, anion[0], n)


def reaction_for(acid_i: int, base_i: int) -> tuple[list[str], list[str], list[int]]:
    acid, base = T.ACIDS[acid_i], T.BASES[base_i]
    left = [acid[0], base[0]]
    right = [salt_formula(acid, base), "H2O"]
    return left, right, solve_own(left, right)


def _fmt(x: Fraction, unit: str) -> str:
    s = f"{float(x):.2f}".rstrip("0").rstrip(".")
    return f"{s} {unit}"


class NeutralMass(Family):
    """Mass or moles of a species in an acid + base -> salt + water reaction (kernel mass verifier)."""

    id = "neutral_mass"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        ai, bi = int(p["a"]), int(p["b"])
        left, right, coef = reaction_for(ai, bi)
        species = left + right
        gi = {"acid": 0, "base": 1}[str(p["given"])]
        ti = {"salt": 2, "water": 3, "other": 1 - gi}[str(p["target"])]
        mode = str(p["mode"])  # mass_to_mass | moles_to_mass | mass_to_moles
        n_given = Fraction(str(p["n"]))
        mm = [molar_mass(f) for f in species]
        given_is_mass = mode in ("mass_to_mass", "mass_to_moles")
        target_is_mass = mode in ("mass_to_mass", "moles_to_mass")
        given_value = n_given * mm[gi] if given_is_mass else n_given
        t_moles = n_given * Fraction(coef[ti], coef[gi])
        value = t_moles * mm[ti] if target_is_mass else t_moles
        unit = "g" if target_is_mass else "mol"
        if (value * 100).denominator != 1 or value <= 0 or value > 1000:
            raise IllPosed("answer_not_exact_to_two_decimals")
        if (given_value * 100).denominator != 1:
            raise IllPosed("given_value_not_exact_to_two_decimals")
        names = {0: T.ACIDS[ai][1], 1: T.BASES[bi][1], 2: "the salt", 3: "water"}
        gname, tname = names[gi], names[ti]
        verb = "mass" if target_is_mass else "amount in moles"
        gtext = (
            f"{_fmt(given_value, 'g')} of {gname}"
            if given_is_mass
            else f"{_fmt(given_value, 'mol')} of {gname}"
        )
        if ti > 1:
            stem = f"{T.ACIDS[ai][1].capitalize()} reacts completely with {T.BASES[bi][1]} to give a salt and water. Starting with {gtext}, what {verb} of {tname} is formed?"
        else:
            stem = f"{T.ACIDS[ai][1].capitalize()} reacts completely with {T.BASES[bi][1]} to give a salt and water. Starting with {gtext}, what {verb} of {tname} is needed to react exactly with it?"
        key_text = _fmt(value, unit)
        # wrong procedures (all must differ from the key)
        ratio = Fraction(coef[ti], coef[gi])
        cand: list[tuple[str, Fraction]] = []
        if target_is_mass:
            cand.append(("CHEM.MC.STOICH.MOLE_RATIO_IGNORED", n_given * mm[ti]))
            cand.append(("CHEM.MC.STOICH.RATIO_INVERTED", n_given / ratio * mm[ti]))
            cand.append(("CHEM.MC.STOICH.WRONG_MOLAR_MASS", n_given * ratio * mm[gi]))
            if given_is_mass:
                cand.append(("CHEM.MC.STOICH.MASS_NOT_CONVERTED", given_value * ratio))
            sf = species[ti]
            if "(" in sf:
                loose = sum(
                    (
                        Fraction(atomic_mass(e)) * n
                        for e, n in atoms(re.sub(r"\)\d*", "", sf.replace("(", ""))).items()
                    ),
                    Fraction(0),
                )
                cand.append(("CHEM.MC.STOICH.BRACKET_IN_MOLAR_MASS", n_given * ratio * loose))
        else:
            cand.append(("CHEM.MC.STOICH.MOLE_RATIO_IGNORED", n_given))
            cand.append(("CHEM.MC.STOICH.RATIO_INVERTED", n_given / ratio))
            cand.append(("CHEM.MC.STOICH.MASS_NOT_CONVERTED", given_value * ratio))
            cand.append(("CHEM.MC.STOICH.WRONG_MOLAR_MASS", given_value / mm[ti] * ratio))
        cand.append(
            ("CHEM.MC.STOICH.ONE_MOLE_ASSUMED", mm[ti] * ratio if target_is_mass else ratio)
        )
        wrong = []
        for mc, v in cand:
            if v > 0 and (v * 100).denominator == 1 and v != value:
                wrong.append((mc, {"value": str(v), "unit": unit, "dp": 2}, _fmt(v, unit)))
        for mc, v in cand:
            if v > 0 and (v * 100).denominator != 1:
                rounded = Fraction(round(v * 100), 100)
                if rounded != value:
                    wrong.append(
                        (mc, {"value": str(rounded), "unit": unit, "dp": 2}, _fmt(rounded, unit))
                    )
        eq = _eq(left, right, coef)
        steps = [
            f"Write the balanced equation: {eq}.",
            f"Convert the given quantity to moles{' using the molar mass' if given_is_mass else ''}, then use the coefficients to find the moles of {tname}.",
            f"Convert to {'mass using the molar mass' if target_is_mass else 'the amount in moles'}: the answer is {key_text}.",
        ]
        hints = [
            "Start from the balanced chemical reaction. The coefficients give the ratio of moles.",
            "Change the given mass to moles by dividing by the molar mass, unless the amount is already in moles.",
            "Multiply the moles by the ratio of coefficients, wanted over given, then change to a mass if a mass is asked.",
        ]
        spec = {
            "domain": "stoichiometry",
            "kind": "mass",
            "reaction": {
                "species": [{"formula": f, "side": "L"} for f in left]
                + [{"formula": f, "side": "R"} for f in right],
                "coefficients": coef,
            },
            "given": {
                "index": gi,
                "quantity": "mass" if given_is_mass else "moles",
                "value": str(given_value),
                "unit": "g" if given_is_mass else "mol",
            },
            "target": {"index": ti, "quantity": "mass" if target_is_mass else "moles"},
            "answer_unit": unit,
            "answer_dp": 2,
            "chem": {"family": self.id},
        }
        answer = {"value": str(value), "unit": unit, "dp": 2}
        return Built(
            spec=spec,
            answer=answer,
            witness={"molar_masses": [str(m) for m in mm]},
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=key_text,
            tokens=[str(float(value)).rstrip("0").rstrip("."), key_text],
            difficulty=difficulty(0.6, steps=3, size=2),
            role="apply",
            prediction="Before you calculate, will the answer be larger or smaller than the quantity you start with?",
            methods=[
                FnMethod("chem.mass_moles_route", "chem.mole_route", "stoichiometry", _mass_m1),
                FnMethod(
                    "chem.mass_ratio_route", "chem.mass_proportion", "stoichiometry", _mass_m2
                ),
            ],
            slug=f"{ai}.{bi}.{p['given']}.{p['target']}.{mode}.{str(p['n']).replace('.', 'p')}",
        )


def _mass_parts(
    spec: Mapping[str, Any],
) -> tuple[list[str], list[str], list[int], Mapping[str, Any]]:
    left = [s["formula"] for s in spec["reaction"]["species"] if s["side"] == "L"]
    right = [s["formula"] for s in spec["reaction"]["species"] if s["side"] == "R"]
    return left, right, [], spec


def _mass_m1(spec: Mapping[str, Any]) -> Any:
    left, right, _, _ = _mass_parts(spec)
    coef = solve_own(left, right)
    species = left + right
    g, t = spec["given"], spec["target"]
    gi, ti = int(g["index"]), int(t["index"])
    gv = Fraction(g["value"])
    moles = gv / molar_mass(species[gi]) if g["quantity"] == "mass" else gv
    tm = moles * coef[ti] / coef[gi]
    value = tm * molar_mass(species[ti]) if t["quantity"] == "mass" else tm
    return {"value": str(value), "unit": spec["answer_unit"], "dp": spec["answer_dp"]}


def _mass_m2(spec: Mapping[str, Any]) -> Any:
    left, right, _, _ = _mass_parts(spec)
    coef = solve_sympy(left, right)
    species = left + right
    g, t = spec["given"], spec["target"]
    gi, ti = int(g["index"]), int(t["index"])
    mm = [
        sum(sympy.Rational(str(atomic_mass(e))) * n for e, n in atoms(f).items()) for f in species
    ]
    gv = sympy.Rational(str(g["value"]))
    if g["quantity"] == "mass":
        # mass of target = mass given x (coef_t x M_t) / (coef_g x M_g), moles via the same ratio
        mass_t = gv * (coef[ti] * mm[ti]) / (coef[gi] * mm[gi])
        value = mass_t if t["quantity"] == "mass" else mass_t / mm[ti]
    else:
        moles_t = gv * sympy.Rational(coef[ti], coef[gi])
        value = moles_t * mm[ti] if t["quantity"] == "mass" else moles_t
    frac_value = Fraction(int(value.p), int(value.q))
    return {"value": str(frac_value), "unit": spec["answer_unit"], "dp": spec["answer_dp"]}


# ---------------------------------------------------------------- salt formula


class SaltFormula(Family):
    id = "salt_formula"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        ai, bi = int(p["a"]), int(p["b"])
        acid, base = T.ACIDS[ai], T.BASES[bi]
        left, right, coef = reaction_for(ai, bi)
        salt = right[0]
        cation = next(c for c in T.CATIONS if c[0] == base[2])
        anion = next(a for a in T.ANIONS if a[0] == acid[2])
        m, n = crisscross(cation[1], anion[1])
        stem = f"{base[1].capitalize()} reacts completely with {acid[1]} to form a salt and water. Which formula is the formula of the salt?"
        answer = {"coefficients": coef, "salt": salt}
        wrong_text: list[tuple[str, str]] = []
        wrong_text.append(
            ("CHEM.MC.SALT.CHARGES_IGNORED", formula_from_counts(cation[0], 1, anion[0], 1))
        )
        wrong_text.append(
            ("CHEM.MC.SALT.SUBSCRIPTS_SWAPPED", formula_from_counts(cation[0], n, anion[0], m))
        )
        wrong_text.append(
            (
                "CHEM.MC.SALT.NOT_REDUCED",
                formula_from_counts(
                    cation[0],
                    cation_q_over(cation[1], anion[1], "a"),
                    anion[0],
                    cation_q_over(cation[1], anion[1], "c"),
                )
                if m * 2 <= 6
                else "",
            )
        )
        if anion[0] in T.POLYATOMIC and n > 1:
            wrong_text.append(
                ("CHEM.MC.SALT.BRACKET_MISSING", group_plain(cation[0], m) + anion[0] + str(n))
            )
        wrong_text.append(
            (
                "CHEM.MC.SALT.CHARGE_AS_OWN_SUBSCRIPT",
                formula_from_counts(cation[0], cation[1], anion[0], anion[1]),
            )
        )
        wrong_text.append(("CHEM.MC.SALT.ACID_FORMULA_GIVEN", acid[0]))
        wrong_text.append(("CHEM.MC.SALT.BASE_FORMULA_GIVEN", base[0]))
        wrong = [
            (mc, {"coefficients": coef, "salt": t}, t) for mc, t in wrong_text if t and t != salt
        ]
        hints = [
            "A salt is made from the positive ion of the base and the negative ion of the acid. Name both ions.",
            "Write the charge of each ion. The compound must have zero total charge, so use as many of each ion as needed to cancel.",
            "Use the smallest numbers of each ion that make the charges cancel, and write a bracket round a group of atoms if it appears more than once.",
        ]
        steps = [
            f"The positive ion comes from the base ({cation[2]}, charge {cation[1]}+) and the negative ion from the acid ({anion[2]}, charge {anion[1]}-).",
            f"Swap the charge numbers and reduce: {m} of the positive ion and {n} of the negative ion.",
            f"The salt is {salt}, and the balanced equation is {_eq(left, right, coef)}.",
        ]
        spec = balance_spec(
            left,
            right,
            {"family": self.id, "cation": [cation[0], cation[1]], "anion": [anion[0], anion[1]]},
        )
        return Built(
            spec=spec,
            answer=answer,
            witness={"atom_counts": [atoms(f) for f in left + right]},
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=salt,
            tokens=[salt],
            difficulty=difficulty(0.4, steps=2 + (m > 1) + (n > 1)),
            role="procedure",
            prediction="Before you write it, which ion comes from the acid and which from the base?",
            methods=[
                FnMethod("chem.salt_crisscross", "chem.crisscross", "salt_formulas", _salt_m1),
                FnMethod("chem.salt_search", "chem.charge_search", "salt_formulas", _salt_m2),
            ],
            slug=f"{ai}.{bi}",
        )


def cation_q_over(qc: int, qa: int, which: str) -> int:
    """A not-reduced pair: both counts doubled."""
    m, n = crisscross(qc, qa)
    return 2 * m if which == "a" else 2 * n


def group_plain(sym: str, count: int) -> str:
    return sym if count == 1 else f"{sym}{count}"


def _salt_m1(spec: Mapping[str, Any]) -> Any:
    left, right = _sides(spec)
    (cs, cq), (as_, aq) = spec["chem"]["cation"], spec["chem"]["anion"]
    m, n = crisscross(int(cq), int(aq))
    return {"coefficients": solve_own(left, right), "salt": formula_from_counts(cs, m, as_, n)}


def _salt_m2(spec: Mapping[str, Any]) -> Any:
    left, right = _sides(spec)
    (cs, cq), (as_, aq) = spec["chem"]["cation"], spec["chem"]["anion"]
    m, n = search_smallest(int(cq), int(aq))
    return {"coefficients": solve_sympy(left, right), "salt": formula_from_counts(cs, m, as_, n)}


ACID_FAMILIES: dict[str, Family] = {
    f.id: f
    for f in (
        PhConversion(),
        PhStrong(),
        PhDilution(),
        PhRatio(),
        PhClassify(),
        NeutralVolume(),
        NeutralMass(),
        SaltFormula(),
    )
}
