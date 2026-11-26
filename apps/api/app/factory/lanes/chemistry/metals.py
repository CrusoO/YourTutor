# ruff: noqa: E501
"""Chapter: Metals and Non-metals. Displacement and acid reactions from the reactivity series,
the order of reactivity, and ionic formulas.

Rule-decidable only. Method A reads the position of each metal in the school reactivity series.
Method B reads the sign of the difference of standard electrode potentials (a cited cross-check
table). A pair on which the two disagree (sodium and calcium, mercury and silver) is never used,
and the disagreement is recorded as data, not hidden. Equations behind each item are balanced by
the kernel's integer-matrix verifier.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping
from typing import Any

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
)
from app.factory.lanes.chemistry.formula import atoms
from app.factory.lanes.chemistry.ions import (
    crisscross,
    exists,
    formula_from_counts,
    group,
    search_smallest,
)

SERIES_INDEX = {m: i for i, m in enumerate(T.SCHOOL_SERIES)}


def series_says_reacts(metal: str, other: str) -> bool:
    """`metal` displaces `other` from its salt: it sits higher in the school series."""
    return SERIES_INDEX[metal] < SERIES_INDEX[other]


def potentials_say_reacts(metal: str, other: str) -> bool:
    return T.E0[metal] < T.E0[other]


def orders_agree(a: str, b: str) -> bool:
    return series_says_reacts(a, b) == potentials_say_reacts(a, b)


# ---------------------------------------------------------------- displacement from solutions

SOLUBLE = {
    "nitrate": ("NO3", set(T.SOLUTION_METALS)),
    "sulphate": ("SO4", {"Mg", "Al", "Zn", "Fe", "Cu"}),
    "chloride": ("Cl", {"Mg", "Al", "Zn", "Fe", "Cu"}),
}
_CAT = {c[0]: c for c in (*T.CATIONS, T.FE3)}
SOL_NAME = {
    "Mg": "magnesium",
    "Al": "aluminium",
    "Zn": "zinc",
    "Fe": "iron",
    "Pb": "lead",
    "Cu": "copper",
    "Ag": "silver",
}
SALT_NAME = {
    "Mg": "magnesium",
    "Al": "aluminium",
    "Zn": "zinc",
    "Fe": "iron(II)",
    "Pb": "lead(II)",
    "Cu": "copper(II)",
    "Ag": "silver",
}
_ANION = {a[0]: a for a in T.ANIONS}


def salt_of(metal: str, anion: str) -> str:
    q = T.SOLUTION_METALS[metal]
    m, n = crisscross(q, _ANION[anion][1])
    return formula_from_counts(metal, m, anion, n)


def pair_equation(metal: str, other: str, anion: str) -> tuple[list[str], list[str]]:
    return [metal, salt_of(other, anion)], [salt_of(metal, anion), other]


def _statements(metal: str, other: str, anion: str) -> dict[str, str]:
    m, o = SOL_NAME[metal], SOL_NAME[other]
    return {
        "displaces": f"{m.capitalize()} displaces {o}, and {o} metal is formed",
        "none": "No reaction takes place",
        "reversed": f"{o.capitalize()} displaces {m}, and {m} metal is formed",
        "hydrogen": "Hydrogen gas is released",
    }


class DisplacementPairs(Family):
    """A metal is added to the salt solution of another metal: does it displace it?"""

    id = "displace_pairs"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        anion_name = str(p["anion"])
        metal, other = str(p["metal"]), str(p["other"])
        sym, ok = SOLUBLE[anion_name]
        if metal not in ok or other not in ok or metal == other:
            raise IllPosed("pair_not_available_for_this_anion")
        if not orders_agree(metal, other):
            raise IllPosed("series_and_potentials_disagree")
        reacts = series_says_reacts(metal, other)
        left, right = pair_equation(metal, other, sym)
        coef = solve_own(left, right)
        text = _statements(metal, other, anion_name)
        key_id = "displaces" if reacts else "none"
        stem = f"{SOL_NAME[metal].capitalize()} metal is added to {SOL_NAME[other]} {anion_name} solution. Which statement is correct?"
        answer = {"coefficients": coef, "outcome": key_id}
        if reacts:
            wrong = [
                ("CHEM.MC.METAL.MORE_REACTIVE_DOES_NOT_DISPLACE", "none"),
                ("CHEM.MC.METAL.ROLES_REVERSED", "reversed"),
                ("CHEM.MC.METAL.HYDROGEN_ALWAYS_RELEASED", "hydrogen"),
            ]
        else:
            wrong = [
                ("CHEM.MC.METAL.LESS_REACTIVE_DISPLACES", "displaces"),
                ("CHEM.MC.METAL.ROLES_REVERSED", "reversed"),
                ("CHEM.MC.METAL.HYDROGEN_ALWAYS_RELEASED", "hydrogen"),
            ]
        wrong_opts = [(mc, {"coefficients": coef, "outcome": oid}, text[oid]) for mc, oid in wrong]
        hints = [
            "A more reactive metal can push a less reactive metal out of its salt solution. Look at the order of reactivity.",
            "Find the metal that is added and the metal that is already in the solution, and compare their places in the reactivity series.",
            "The metal that is added must be higher in the series than the metal in the solution for a reaction to happen.",
        ]
        steps = [
            "Place both metals in the reactivity series.",
            "A displacement reaction happens only if the metal added is more reactive than the metal in the salt solution.",
            f"So the correct statement is: {text[key_id]}.",
        ]
        spec = balance_spec(
            left, right, {"family": self.id, "anion": anion_name, "metal": metal, "other": other}
        )
        return Built(
            spec=spec,
            answer=answer,
            witness={"atom_counts": [atoms(f) for f in left + right]},
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong_opts,
            key_text=text[key_id],
            tokens=["No reaction takes place"]
            if not reacts
            else [f"{SOL_NAME[metal]} displaces {SOL_NAME[other]}"],
            difficulty=difficulty(0.35, steps=2),
            role="apply",
            prediction="Before you decide, which of the two metals do you think is more reactive?",
            methods=[
                FnMethod(
                    "chem.displace_series",
                    "chem.reactivity_series",
                    "reactivity_series",
                    lambda s: _displace(s, True),
                ),
                FnMethod(
                    "chem.displace_potentials",
                    "chem.electrode_potentials",
                    "reactivity_series",
                    lambda s: _displace(s, False),
                ),
            ],
            slug=f"{anion_name}.{metal}.{other}",
        )


def _displace(spec: Mapping[str, Any], by_series: bool) -> Any:
    c = spec["chem"]
    rule = series_says_reacts if by_series else potentials_say_reacts
    metal, other = c["metal"], c["other"]
    sym = SOLUBLE[c["anion"]][0]
    left, right = pair_equation(metal, other, sym)
    if [s["formula"] for s in spec["species"]] != left + right:
        raise ValueError("the equation in the spec is not the one of the pair")
    coef = solve_own(left, right) if by_series else solve_sympy(left, right)
    return {"coefficients": coef, "outcome": "displaces" if rule(metal, other) else "none"}


# ---------------------------------------------------------------- metal and dilute acid

ACID_USED = {"HCl": ("dilute hydrochloric acid", "Cl"), "H2SO4": ("dilute sulphuric acid", "SO4")}


def acid_equation(metal: str, acid: str) -> tuple[list[str], list[str]]:
    sym = ACID_USED[acid][1]
    q = {"Mg": 2, "Al": 3, "Zn": 2, "Fe": 2, "Cu": 2, "Ag": 1, "Au": 3}[metal]
    m, n = crisscross(q, _ANION[sym][1])
    return [metal, acid], [formula_from_counts(metal, m, sym, n), "H2"]


class AcidReaction(Family):
    """A metal is added to a dilute acid: does it give hydrogen?"""

    id = "acid_reaction"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        acid, metal = str(p["acid"]), str(p["metal"])
        active = metal in T.ACID_ACTIVE
        left, right = acid_equation(metal, acid)
        coef = solve_own(left, right)
        name = ACID_USED[acid][0]
        stem = f"{T.METAL_NAME[metal].capitalize()} metal is added to {name}. Which statement is correct?"
        text = {
            "hydrogen": "Hydrogen gas is released and a salt forms",
            "none": "No reaction takes place",
            "oxygen": "Oxygen gas is released",
            "water": "Only a salt and water form, as in neutralisation",
        }
        key_id = "hydrogen" if active else "none"
        answer = {"coefficients": coef, "outcome": key_id}
        first = (
            ("CHEM.MC.METAL.ABOVE_HYDROGEN_INERT", "none")
            if active
            else ("CHEM.MC.METAL.BELOW_HYDROGEN_REACTS", "hydrogen")
        )
        wrong = [
            (first[0], {"coefficients": coef, "outcome": first[1]}, text[first[1]]),
            (
                "CHEM.MC.METAL.WRONG_GAS_NAMED",
                {"coefficients": coef, "outcome": "oxygen"},
                text["oxygen"],
            ),
            (
                "CHEM.MC.METAL.METAL_TREATED_AS_BASE",
                {"coefficients": coef, "outcome": "water"},
                text["water"],
            ),
        ]
        hints = [
            "A dilute acid contains hydrogen ions. A metal can push hydrogen out of the acid only if it is more reactive than hydrogen.",
            "Find where hydrogen sits in the reactivity series and compare it with the place of the metal.",
            "Metals above hydrogen in the series release hydrogen gas from a dilute acid. Metals below hydrogen do not.",
        ]
        steps = [
            "Locate the metal and hydrogen in the reactivity series.",
            "A metal reacts with a dilute acid to give hydrogen only if it is above hydrogen in the series.",
            f"So the correct statement is: {text[key_id]}.",
        ]
        spec = balance_spec(left, right, {"family": self.id, "acid": acid, "metal": metal})
        return Built(
            spec=spec,
            answer=answer,
            witness={"atom_counts": [atoms(f) for f in left + right]},
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=text[key_id],
            tokens=["No reaction takes place"] if not active else ["Hydrogen gas is released"],
            difficulty=difficulty(0.3, steps=1),
            role="recall",
            prediction="Before you decide, is this metal near the top of the reactivity series or near the bottom?",
            methods=[
                FnMethod(
                    "chem.acid_series",
                    "chem.reactivity_series",
                    "reactivity_series",
                    lambda s: _acid(s, True),
                ),
                FnMethod(
                    "chem.acid_potentials",
                    "chem.electrode_potentials",
                    "reactivity_series",
                    lambda s: _acid(s, False),
                ),
            ],
            slug=f"{acid}.{metal}",
        )


def _acid(spec: Mapping[str, Any], by_series: bool) -> Any:
    c = spec["chem"]
    metal = c["metal"]
    gives = SERIES_INDEX[metal] < SERIES_INDEX["H"] if by_series else T.E0[metal] < T.E0["H"]
    left, right = acid_equation(metal, c["acid"])
    if [s["formula"] for s in spec["species"]] != left + right:
        raise ValueError("the equation in the spec is not the one of the metal")
    coef = solve_own(left, right) if by_series else solve_sympy(left, right)
    return {"coefficients": coef, "outcome": "hydrogen" if gives else "none"}


# ---------------------------------------------------------------- order of reactivity

ORDER_METALS = ("K", "Na", "Ca", "Mg", "Al", "Zn", "Fe", "Pb", "Cu", "Ag", "Au")
ORDER_COMBOS: tuple[tuple[str, ...], ...] = tuple(
    c for c in itertools.combinations(ORDER_METALS, 4) if not ({"Na", "Ca"} <= set(c))
)
ORDER_NAME = {**T.METAL_NAME}


class ReactivityOrder(Family):
    id = "reactivity_order"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        combo = ORDER_COMBOS[int(p["combo"])]
        ask = str(p["ask"])
        by_series = sorted(combo, key=lambda m: SERIES_INDEX[m])
        by_potential = sorted(combo, key=lambda m: T.E0[m])
        if by_series != by_potential:
            raise IllPosed("series_and_potentials_disagree")
        key = by_series[0] if ask == "most" else by_series[-1]
        opp = by_series[-1] if ask == "most" else by_series[0]
        stem = f"Which of these metals is {'the most' if ask == 'most' else 'the least'} reactive: {', '.join(ORDER_NAME[m] for m in sorted(combo))}?"
        answer = {**linear_answer("r", SERIES_INDEX[key]), "metal": key}
        wrong = []
        for m in combo:
            if m == key:
                continue
            mc = (
                "CHEM.MC.METAL.ORDER_REVERSED"
                if m == opp
                else "CHEM.MC.METAL.MIDDLE_OF_SERIES_PICKED"
            )
            wrong.append(
                (
                    mc,
                    {**linear_answer("r", SERIES_INDEX[m]), "metal": m},
                    ORDER_NAME[m].capitalize(),
                )
            )
        wrong.sort(key=lambda w: w[0] != "CHEM.MC.METAL.ORDER_REVERSED")
        hints = [
            "Use the reactivity series, which lists metals from the most reactive at the top to the least reactive at the bottom.",
            "Find each metal from the options in the series and note its position.",
            f"The {'most' if ask == 'most' else 'least'} reactive metal of the four is the one that sits {'highest' if ask == 'most' else 'lowest'} in the series.",
        ]
        steps = [
            "Write the four metals in the order of the reactivity series.",
            f"The {'first' if ask == 'most' else 'last'} one in that order is {'the most' if ask == 'most' else 'the least'} reactive.",
            f"That metal is {ORDER_NAME[key]}.",
        ]
        spec = {
            "domain": "algebra",
            "kind": "linear_system",
            "variables": ["r"],
            "equations": [{"coeffs": ["1"], "const": str(SERIES_INDEX[key])}],
            "chem": {"family": self.id, "metals": list(combo), "ask": ask},
        }
        return Built(
            spec=spec,
            answer=answer,
            witness=linear_answer("r", SERIES_INDEX[key]),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=ORDER_NAME[key].capitalize(),
            tokens=[ORDER_NAME[key], key],
            difficulty=difficulty(0.25),
            role="recall",
            prediction="Before you check, which metal do you expect to be the most reactive of all?",
            methods=[
                FnMethod(
                    "chem.order_series",
                    "chem.reactivity_series",
                    "reactivity_series",
                    lambda s: _order(s, True),
                ),
                FnMethod(
                    "chem.order_potentials",
                    "chem.electrode_potentials",
                    "reactivity_series",
                    lambda s: _order(s, False),
                ),
            ],
            slug=f"{int(p['combo'])}.{ask}",
        )


def _order(spec: Mapping[str, Any], by_series: bool) -> Any:
    c = spec["chem"]
    metals = list(c["metals"])
    ordered = sorted(metals, key=(lambda m: SERIES_INDEX[m]) if by_series else (lambda m: T.E0[m]))
    pick = ordered[0] if c["ask"] == "most" else ordered[-1]
    return {**linear_answer("r", SERIES_INDEX[pick]), "metal": pick}


# ---------------------------------------------------------------- ionic formulas

ION_CATIONS = (*T.CATIONS, T.FE3)


class IonicFormula(Family):
    id = "ionic_formula"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        cat = ION_CATIONS[int(p["c"])]
        an = T.ANIONS[int(p["a"])]
        if not exists(cat[0], cat[1], an[0]):
            raise IllPosed("compound_outside_the_school_examples")
        m, n = crisscross(cat[1], an[1])
        formula = formula_from_counts(cat[0], m, an[0], n)
        stem = f"What is the correct formula of {cat[2]} {an[2]}?"
        qc, qa = cat[1], an[1]
        texts: list[tuple[str, tuple[int, int], str]] = [
            ("CHEM.MC.IONIC.SUBSCRIPTS_SWAPPED", (n, m), formula_from_counts(cat[0], n, an[0], m)),
            ("CHEM.MC.IONIC.CHARGES_IGNORED", (1, 1), formula_from_counts(cat[0], 1, an[0], 1)),
            (
                "CHEM.MC.IONIC.NOT_REDUCED",
                (2 * m, 2 * n),
                formula_from_counts(cat[0], 2 * m, an[0], 2 * n),
            ),
            (
                "CHEM.MC.IONIC.CHARGE_AS_OWN_SUBSCRIPT",
                (qc, qa),
                formula_from_counts(cat[0], qc, an[0], qa),
            ),
        ]
        extra: list[tuple[str, tuple[int, int], str]] = []
        if an[0] in T.POLYATOMIC and n > 1:
            extra.append(
                (
                    "CHEM.MC.IONIC.BRACKET_MISSING",
                    (m, n),
                    (cat[0] if m == 1 else group(cat[0], m)) + an[0] + str(n),
                )
            )
        if cat[0] in T.POLYATOMIC and m > 1:
            extra.append(
                ("CHEM.MC.IONIC.BRACKET_MISSING", (m, n), cat[0] + str(m) + group(an[0], n))
            )
        extra.append(
            ("CHEM.MC.IONIC.ANION_WRITTEN_FIRST", (m, n), formula_from_counts(an[0], n, cat[0], m))
        )
        extra.append(
            ("CHEM.MC.IONIC.CHARGES_WRITTEN_IN_FORMULA", (m, n), f"{cat[0]}{qc}+{an[0]}{qa}-")
        )
        answer = {**{"values": {"m": str(m), "n": str(n)}}, "formula": formula}
        wrong = [
            (mc, {"values": {"m": str(a), "n": str(b)}, "formula": t}, t)
            for mc, (a, b), t in texts + extra
            if t != formula
        ]
        hints = [
            "An ionic compound has no overall charge, so the positive and negative charges must cancel.",
            "Write the charge of each ion. Use as many of each ion as it takes for the total positive charge to equal the total negative charge.",
            "Swap the charge numbers to find the counts, then divide both by their common factor. Use a bracket round a group of atoms that appears more than once.",
        ]
        steps = [
            f"The {cat[2]} ion has charge {qc}+ and the {an[2]} ion has charge {qa}-.",
            f"To cancel the charges, take {m} of the first ion and {n} of the second: {m} x {qc} = {n} x {qa}.",
            f"The formula is {formula}.",
        ]
        spec = {
            "domain": "algebra",
            "kind": "linear_system",
            "variables": ["m", "n"],
            "equations": [
                {"coeffs": [str(qc), str(-qa)], "const": "0"},
                {"coeffs": ["1", "1"], "const": str(m + n)},
            ],
            "chem": {"family": self.id, "cation": [cat[0], qc], "anion": [an[0], qa]},
        }
        return Built(
            spec=spec,
            answer=answer,
            witness={"values": {"m": str(m), "n": str(n)}},
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=formula,
            tokens=[formula],
            difficulty=difficulty(0.35, steps=2 + (m > 1) + (n > 1)),
            role="procedure",
            prediction="Before you write it, will the formula need a subscript on either ion?",
            methods=[
                FnMethod("chem.ionic_crisscross", "chem.crisscross", "ionic_formulas", _ion_m1),
                FnMethod("chem.ionic_search", "chem.charge_search", "ionic_formulas", _ion_m2),
            ],
            slug=f"{int(p['c'])}.{int(p['a'])}",
        )


def _ion_m1(spec: Mapping[str, Any]) -> Any:
    (cs, qc), (as_, qa) = spec["chem"]["cation"], spec["chem"]["anion"]
    m, n = crisscross(int(qc), int(qa))
    return {"values": {"m": str(m), "n": str(n)}, "formula": formula_from_counts(cs, m, as_, n)}


def _ion_m2(spec: Mapping[str, Any]) -> Any:
    (cs, qc), (as_, qa) = spec["chem"]["cation"], spec["chem"]["anion"]
    m, n = search_smallest(int(qc), int(qa))
    return {"values": {"m": str(m), "n": str(n)}, "formula": formula_from_counts(cs, m, as_, n)}


METAL_FAMILIES: dict[str, Family] = {
    f.id: f for f in (DisplacementPairs(), AcidReaction(), ReactivityOrder(), IonicFormula())
}
_ = (_eq, _sides)  # re-exported helpers used by tests
