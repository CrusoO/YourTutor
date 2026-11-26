# ruff: noqa: E501
"""Life Processes models that a closed rule decides: equation bookkeeping and rates of a process.

EQUATIONS is the whole table the lane trusts: three standard balanced word-and-formula equations
(photosynthesis, aerobic respiration, anaerobic respiration in yeast). The table is not taken on
trust, because Method B balances each equation again from the formulas alone, by atom counts, and
refuses the item if the stated coefficients differ. Every stem prints the equation, so the
learner needs the bookkeeping only, not recall. Facts that need a source (counts of ATP, organ
sizes, enzyme names, normal ranges) are deliberately not here.
"""

from __future__ import annotations

import itertools
import math
import re
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.lanes.biology.common import CHAPTERS, Model, number_answer, numeric_draft, plural

CH = CHAPTERS["LIFE"]

MISC: dict[str, tuple[str, str]] = {
    "COEFFICIENT_AS_COUNT": (
        "Gives the coefficient from the equation as the number of molecules",
        "You may have read the coefficient as the answer. Scale it by the number of molecules given.",
    ),
    "RATIO_INVERTED": (
        "Turns the ratio of coefficients upside down",
        "You may have used the coefficients the wrong way round. Put the wanted substance on top.",
    ),
    "ONE_TO_ONE_ASSUMED": (
        "Assumes one molecule for every molecule given",
        "You may have assumed the numbers match. The coefficients show how the numbers compare.",
    ),
    "ATOMS_FOR_MOLECULES": (
        "Counts atoms instead of molecules",
        "You may have counted the atoms in the molecules. The question asks for molecules.",
    ),
    "ADDED_NOT_MULTIPLIED": (
        "Adds the coefficient to the number of molecules",
        "You may have added the coefficient. Scale the number of molecules by the ratio of coefficients.",
    ),
    "UNIT_NOT_CONVERTED": (
        "Leaves out the change between hours and minutes",
        "You may have used the time without changing its unit. The rate is given per minute.",
    ),
    "DIVIDED_NOT_MULTIPLIED": (
        "Divides where the rate is multiplied by the time",
        "You may have divided the rate by the time. The total is the rate times the time.",
    ),
    "MULTIPLIED_NOT_DIVIDED": (
        "Multiplies where a division is needed",
        "You may have multiplied the two numbers. Here one number is shared out over the other.",
    ),
    "TIME_FORGOTTEN": (
        "Gives the rate as the total",
        "You may have stopped at the rate. The total needs the time as well.",
    ),
    "RATE_INVERTED": (
        "Turns the rate upside down",
        "You may have divided the wrong way round. Check what is shared out over what.",
    ),
    "PER_HOUR_FOR_PER_MINUTE": (
        "Gives the rate per hour where the rate per minute is asked",
        "You may have left the time in hours. The question asks for each minute.",
    ),
    "COUNT_AS_TIME": (
        "Gives the count as the time",
        "You may have given the number counted. The question asks for how long it took.",
    ),
}

# name -> (reactants, products): each a list of (formula, coefficient)
EQUATIONS: dict[str, tuple[str, list[tuple[str, int]], list[tuple[str, int]]]] = {
    "photosynthesis": ("Photosynthesis", [("CO2", 6), ("H2O", 6)], [("C6H12O6", 1), ("O2", 6)]),
    "respiration": ("Aerobic respiration", [("C6H12O6", 1), ("O2", 6)], [("CO2", 6), ("H2O", 6)]),
    "fermentation": (
        "Anaerobic respiration in yeast",
        [("C6H12O6", 1)],
        [("C2H5OH", 2), ("CO2", 2)],
    ),
}
NAMES = {
    "CO2": "carbon dioxide",
    "H2O": "water",
    "C6H12O6": "glucose",
    "O2": "oxygen",
    "C2H5OH": "ethanol",
}
_ATOM = re.compile(r"([A-Z][a-z]?)(\d*)")


def _atoms(formula: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for sym, num in _ATOM.findall(formula):
        out[sym] = out.get(sym, 0) + int(num or 1)
    return out


def equation_text(key: str) -> str:
    _, left, right = EQUATIONS[key]

    def side(terms: list[tuple[str, int]]) -> str:
        return " + ".join(f"{c} {f}" if c > 1 else f for f, c in terms)

    return f"{side(left)} → {side(right)}"


def _pairs() -> tuple[str, ...]:
    out = []
    for key, (_, left, right) in EQUATIONS.items():
        species = [f for f, _ in left + right]
        out += [f"{key}:{a}>{b}" for a in species for b in species if a != b]
    return tuple(out)


def _equation(params: Mapping[str, str]) -> Any:
    key, rest = params["q"].split(":")
    given, ask = rest.split(">")
    name, left, right = EQUATIONS[key]
    coeffs = {f: c for f, c in left + right}
    count = int(params["g"])
    value = Fraction(count * coeffs[ask], coeffs[given])
    if value.denominator != 1:
        return "answer_is_not_a_whole_number_of_molecules"
    verb_given = "used up" if any(f == given for f, _ in left) else "made"
    verb_ask = "used up" if any(f == ask for f, _ in left) else "made"
    stem = (
        f"{name} can be written as {equation_text(key)}. In one experiment, {plural(count, 'molecule')} of {NAMES[given]} {'is' if count == 1 else 'are'} {verb_given}. "
        f"How many molecules of {NAMES[ask]} are {verb_ask} in the same experiment?"
    )
    atoms_ask = sum(_atoms(ask).values())
    wrongs = [
        ("COEFFICIENT_AS_COUNT", Fraction(coeffs[ask])), ("ONE_TO_ONE_ASSUMED", Fraction(count)),
        ("RATIO_INVERTED", Fraction(count * coeffs[given], coeffs[ask])), ("ATOMS_FOR_MOLECULES", value * atoms_ask),
        ("ADDED_NOT_MULTIPLIED", Fraction(count + coeffs[ask])),
    ]  # fmt: skip
    bio = {
        "model": "LIFE.EQUATION", "variant": key, "reactants": [f for f, _ in left], "products": [f for f, _ in right],
        "coeffs": coeffs, "given": given, "ask": ask, "count": count,
    }  # fmt: skip
    hints = [
        "The numbers written in front of the formulas show how many molecules take part, in proportion.",
        "Find the number in front of each of the two substances in the question, and use their ratio to scale the number of molecules given.",
        "Write the number of molecules wanted as the number given multiplied by the ratio of the two numbers in front of the formulas.",
    ]
    steps = [
        f"In the equation, the number in front of {NAMES[given]} is {coeffs[given]} and the number in front of {NAMES[ask]} is {coeffs[ask]}.",
        f"The ratio of {NAMES[ask]} to {NAMES[given]} is {coeffs[ask]} to {coeffs[given]}.",
        f"Scale up: {count} x {coeffs[ask]} divided by {coeffs[given]} = {int(value)} molecules.",
    ]
    return numeric_draft(
        variant=key, bio=bio, coeff=Fraction(coeffs[given]), const=Fraction(count * coeffs[ask]), value=value,
        unit="molecules", stem=stem, hints=hints, steps=steps,
        wrongs=[(n, v) for n, v in wrongs if Fraction(v).denominator == 1], difficulty=0.45, role="apply",
        prediction="Before you calculate, will there be more or fewer molecules of the second substance than of the first?",
        features=["equation_ratio"],
    )  # fmt: skip


def solve_eq_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    c = bio["coeffs"]
    return number_answer(Fraction(int(bio["count"]) * c[bio["ask"]], c[bio["given"]]), "molecules")


def balance(reactants: list[str], products: list[str]) -> dict[str, int]:
    """The one primitive whole-number balancing, found by trying every small coefficient set."""
    species = reactants + products
    found = []
    for combo in itertools.product(range(1, 9), repeat=len(species)):
        if math.gcd(*combo) != 1:
            continue
        totals: dict[str, int] = {}
        for i, formula in enumerate(species):
            sign = 1 if i < len(reactants) else -1
            for sym, n in _atoms(formula).items():
                totals[sym] = totals.get(sym, 0) + sign * combo[i] * n
        if all(v == 0 for v in totals.values()):
            found.append(dict(zip(species, combo, strict=True)))
    if len(found) != 1:
        raise ValueError("the equation has no single primitive balancing")
    return found[0]


def solve_eq_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    coeffs = balance(list(bio["reactants"]), list(bio["products"]))
    if coeffs != {k: int(v) for k, v in bio["coeffs"].items()}:
        raise ValueError("stated coefficients are not the balanced ones")
    return number_answer(
        Fraction(int(bio["count"]) * coeffs[bio["ask"]], coeffs[bio["given"]]), "molecules"
    )


# ---------------------------------------------------------------- RATES

RATE_CONTEXTS: dict[str, tuple[str, str, str, str]] = {
    # key: (rate sentence, count noun, the thing counted per question, unit text)
    "heart": (
        "A resting person's heart beats {r} times each minute.",
        "beats",
        "the heart",
        "beats",
    ),
    "breath": (
        "A student at rest breathes in {r} times each minute.",
        "breaths",
        "the student",
        "breaths",
    ),
    "bubbles": (
        "A water plant in bright light gives off {r} bubbles of gas each minute.",
        "bubbles",
        "the plant",
        "bubbles",
    ),
}
RATES = {
    "heart": ("60", "70", "72", "75", "80", "90"),
    "breath": ("12", "15", "16", "18", "20"),
    "bubbles": ("4", "5", "6", "8", "10", "12"),
}


def _time_text(t: int, tu: str) -> str:
    return f"{t} minute{'s' if t > 1 else ''}" if tu == "min" else f"{t} hour{'s' if t > 1 else ''}"


def _rates(params: Mapping[str, str]) -> Any:
    ctx, variant, tu = params["ctx"], params["variant"], params["tu"]
    r, t = int(params["r"]), int(params["t"])
    if str(r) not in RATES[ctx]:
        return "rate_does_not_belong_to_this_context"
    if tu == "h" and t > 3:
        return "too_many_hours"
    if tu == "min" and t < 2:
        return "too_few_minutes"
    sentence, noun, _, unit = RATE_CONTEXTS[ctx]
    minutes = t if tu == "min" else 60 * t
    count = r * minutes
    bio: dict[str, Any] = {
        "model": "LIFE.RATES",
        "variant": variant,
        "r": r,
        "t": t,
        "tu": tu,
        "c": count,
        "unit": unit,
    }
    rate_s = sentence.format(r=r)
    wrongs: list[tuple[str, Any]]
    if variant == "total":
        stem = f"{rate_s} How many {noun} is that in {_time_text(t, tu)}?"
        value, out_unit = Fraction(count), unit
        wrongs = [
            ("UNIT_NOT_CONVERTED", r * t),
            ("DIVIDED_NOT_MULTIPLIED", Fraction(r, t)),
            ("TIME_FORGOTTEN", r),
            ("ADDED_NOT_MULTIPLIED", r + t),
        ]
        hints = [
            "The total is the rate for one minute multiplied by the number of minutes.",
            "Change the time into minutes first if it is not given in minutes.",
            "Multiply the number of minutes by the number counted each minute.",
        ]
        steps = [
            f"The time is {minutes} minutes." if tu == "h" else f"The time is {t} minutes.",
            f"The total is {r} x {minutes} = {count} {noun}.",
        ]
        coeff, const = Fraction(1), value
    elif variant == "rate":
        stem = f"In {_time_text(t, tu)}, a count of {count} {noun} is recorded. How many {noun} is that each minute?"
        value, out_unit = Fraction(r), f"{unit} per minute"
        wrongs = [
            ("MULTIPLIED_NOT_DIVIDED", count * minutes),
            ("PER_HOUR_FOR_PER_MINUTE", Fraction(count, t)),
            ("RATE_INVERTED", Fraction(minutes, count)),
            ("TIME_FORGOTTEN", count),
        ]
        hints = [
            "A rate for one minute is the total shared out over the minutes.",
            "Change the time into minutes first if it is not given in minutes.",
            "Divide the total by the number of minutes.",
        ]
        steps = [
            f"The time is {minutes} minutes.",
            f"The rate is {count} divided by {minutes} = {r} {noun} each minute.",
        ]
        coeff, const = Fraction(minutes), Fraction(count)
    else:  # time
        stem = f"{rate_s} How long does it take to count {count} {noun}? Give the answer in {'minutes' if tu == 'min' else 'hours'}."
        value, out_unit = Fraction(t), "minutes" if tu == "min" else "hours"
        wrongs = [
            ("MULTIPLIED_NOT_DIVIDED", count * r),
            ("RATE_INVERTED", Fraction(r, count)),
            ("COUNT_AS_TIME", count),
            ("UNIT_NOT_CONVERTED", Fraction(minutes) if tu == "h" else Fraction(count, 60)),
        ]
        hints = [
            "The time is the total divided by the number counted each minute.",
            "The answer from the division is in minutes, so change it if the question asks for another unit.",
            "Divide the total by the rate.",
        ]
        steps = [
            f"The time in minutes is {count} divided by {r} = {minutes}.",
            (f"In hours that is {t}." if tu == "h" else f"So it takes {t} minutes."),
        ]
        coeff, const = Fraction(r), Fraction(count, 60 if tu == "h" else 1)
    return numeric_draft(
        variant=variant, bio=bio, coeff=coeff, const=const, value=value, unit=out_unit, stem=stem,
        hints=hints, steps=steps, wrongs=wrongs, difficulty=0.35 if tu == "min" else 0.5, role="apply",
        prediction="Before you calculate, should the answer be larger or smaller than the rate given?",
        features=["rate", "unit_conversion"] if tu == "h" else ["rate"],
    )  # fmt: skip


def solve_rates_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    r, t, tu, c, v = int(bio["r"]), int(bio["t"]), bio["tu"], int(bio["c"]), bio["variant"]
    minutes = t if tu == "min" else 60 * t
    if v == "total":
        return number_answer(Fraction(r * minutes), bio["unit"])
    if v == "rate":
        return number_answer(Fraction(c, minutes), f"{bio['unit']} per minute")
    return number_answer(
        Fraction(c, r) if tu == "min" else Fraction(c, r * 60),
        "minutes" if tu == "min" else "hours",
    )


def solve_rates_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    r, t, tu, c, v = int(bio["r"]), int(bio["t"]), bio["tu"], int(bio["c"]), bio["variant"]
    per_second = Fraction(r, 60)
    seconds = t * (60 if tu == "min" else 3600)
    if v == "total":
        return number_answer(per_second * seconds, bio["unit"])
    if v == "rate":
        return number_answer(Fraction(c) / seconds * 60, f"{bio['unit']} per minute")
    secs = Fraction(c) / per_second
    return number_answer(
        secs / 60 if tu == "min" else secs / 3600, "minutes" if tu == "min" else "hours"
    )


LIFE_MODELS: dict[str, Model] = {
    m.id: m
    for m in (
        Model(
            "LIFE.EQUATION", "BIO.LIFE.EQUATION", CH,
            "Use the numbers in a printed equation to compare molecules used and made",
            "equation_ratio", "atom_balance_search", "bio.equation_ratio", "bio.atom_balance",
            {"q": _pairs(), "g": ("1", "2", "3", "4", "5", "10", "20", "50")},
            _equation, solve_eq_a, solve_eq_b,
        ),
        Model(
            "LIFE.RATES", "BIO.LIFE.RATES", CH,
            "Use a rate per minute to find a total, a rate or a time",
            "rate_closed_form", "per_second_conversion", "bio.rate_closed_form", "bio.rate_per_second",
            {"ctx": tuple(RATE_CONTEXTS), "variant": ("total", "rate", "time"), "r": ("4", "5", "6", "8", "10", "12", "15", "16", "18", "20", "60", "70", "72", "75", "80", "90"),
             "t": ("1", "2", "3", "5", "10", "30"), "tu": ("min", "h")},
            _rates, solve_rates_a, solve_rates_b,
        ),
    )
}  # fmt: skip
