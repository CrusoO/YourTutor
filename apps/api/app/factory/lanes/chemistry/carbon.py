# ruff: noqa: E501
"""Chapter: Carbon and its Compounds. Homologous series, series identification, isomer counts,
and naming of small chains. All computable or rule-decidable; no diagrams, no free text.

Each family has two independent methods. Series formulas: the general formula versus building the
chain atom by atom and filling every carbon to four bonds. Isomers: growing every skeleton versus
Polya counting with Otter's formula. Names: a naming algorithm over the parsed structure versus a
hand-written reviewed lookup table. The kernel checks the exact linear relation each item encodes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.factory.kernel.constants import atomic_mass
from app.factory.lanes.chemistry import structure as S
from app.factory.lanes.chemistry import tables as T
from app.factory.lanes.chemistry.core import (
    Built,
    Family,
    FnMethod,
    IllPosed,
    difficulty,
    linear_answer,
    linear_spec,
    name_tokens,
    pick,
)

SERIES = {
    "alkane": ("alkane", "single bonds only", 2),
    "alkene": ("alkene", "one double bond", 0),
    "alkyne": ("alkyne", "one triple bond", -2),
}
D_OF = {"alkane": 2, "alkene": 0, "alkyne": -2}
GENERAL = {2: "CnH2n+2", 0: "CnH2n", -2: "CnH2n-2"}


def hydrogens(family: str, n: int) -> int:
    return 2 * n + D_OF[family]


def formula_text(family: str, n: int) -> str:
    h = hydrogens(family, n)
    c = "C" if n == 1 else f"C{n}"
    return f"{c}H{h}"


# ---------------------------------------------------------------- method B: build the chain


def build_chain(family: str, n: int) -> tuple[int, int, int]:
    """(hydrogens, bonds, atoms) from a chain of n carbons, each filled to four bonds."""
    orders = [1] * (n - 1)
    if family == "alkene":
        orders[0] = 2
    if family == "alkyne":
        orders[0] = 3
    used = [0] * n
    for i, o in enumerate(orders):
        used[i] += o
        used[i + 1] += o
    h = sum(4 - u for u in used)
    return h, sum(orders) + h, n + h


class HomologousSeries(Family):
    id = "series_formula"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        family, n, ask = str(p["family"]), int(p["n"]), str(p["ask"])
        if family != "alkane" and n < 2:
            raise IllPosed("unsaturated_needs_two_carbons")
        h = hydrogens(family, n)
        _, bonds, total_atoms = build_chain(family, n)
        mass = 12 * n + h
        desc = {
            "alkane": "a straight-chain alkane",
            "alkene": "a straight-chain alkene with one double bond",
            "alkyne": "a straight-chain alkyne with one triple bond",
        }[family]
        d = D_OF[family]
        other = [f for f in D_OF if f != family]
        if ask == "H":
            stem = f"A molecule of {desc} has {n} carbon {'atom' if n == 1 else 'atoms'}. How many hydrogen atoms does it have?"
            var, key, coeff, const = "x", h, 1, h
            cands = [("CHEM.MC.SERIES.WRONG_SERIES_FORMULA", hydrogens(o, n)) for o in other] + [
                ("CHEM.MC.SERIES.RADICAL_FORMULA_USED", 2 * n + 1),
                ("CHEM.MC.SERIES.TWICE_N_ONLY", 2 * n)
                if d != 0
                else ("CHEM.MC.SERIES.N_PLUS_TWO", n + 2),
                ("CHEM.MC.SERIES.CARBON_COUNT_COPIED", n),
            ]
            hints = [
                "Each carbon atom forms four bonds in total. In a chain, some of those bonds join carbon to carbon.",
                "A family of compounds follows one general formula for the number of hydrogen atoms in terms of the number of carbon atoms.",
                f"Use the general formula of the {family} series with n equal to the number of carbon atoms.",
            ]
            steps = [
                f"The general formula of the {family} series is {GENERAL[d]}.",
                f"For n = {n}, the number of hydrogen atoms is 2 x {n} {'+' if d >= 0 else '-'} {abs(d)}."
                if d != 0
                else f"For n = {n}, the number of hydrogen atoms is 2 x {n}.",
                f"There are {h} hydrogen atoms.",
            ]
        elif ask == "bonds":
            stem = f"How many covalent bonds are there in one molecule of {formula_text(family, n)}, {desc}? Count a double bond as two bonds and a triple bond as three."
            var, key, coeff, const = "x", bonds, 1, bonds
            cands = [
                ("CHEM.MC.SERIES.ATOMS_COUNTED_AS_BONDS", total_atoms),
                ("CHEM.MC.SERIES.ONLY_C_H_BONDS_COUNTED", h),
                (
                    "CHEM.MC.SERIES.MULTIPLE_BOND_COUNTED_ONCE",
                    bonds - (0 if family == "alkane" else (1 if family == "alkene" else 2)),
                ),
                ("CHEM.MC.SERIES.ONLY_C_C_BONDS_COUNTED", bonds - h),
                ("CHEM.MC.SERIES.ONE_BOND_OFF", bonds + 1),
                ("CHEM.MC.SERIES.ONE_BOND_OFF", bonds - 1),
            ]
            hints = [
                "Count the bonds between carbon atoms and the bonds between carbon and hydrogen atoms separately, then add them.",
                "Every hydrogen atom makes exactly one bond. A double bond counts as two and a triple bond counts as three.",
                "Find the number of hydrogen atoms from the general formula, then add the carbon-carbon bonds along the chain.",
            ]
            steps = [
                f"The formula is {formula_text(family, n)}, so there are {h} hydrogen atoms and {h} carbon-hydrogen bonds.",
                f"The carbon-carbon bonds along the chain add up to {bonds - h}, counting multiple bonds as several.",
                f"The total is {bonds} bonds.",
            ]
        elif ask == "mass":
            stem = f"What is the molar mass, in g/mol, of {formula_text(family, n)}? (Take C = 12 and H = 1.)"
            var, key, coeff, const = "x", mass, 1, mass
            cands = [
                ("CHEM.MC.SERIES.ATOMS_COUNTED_AS_MASS", total_atoms),
                ("CHEM.MC.SERIES.CARBON_MASS_ONLY", 12 * n),
                ("CHEM.MC.SERIES.WRONG_SERIES_FORMULA", 12 * n + hydrogens(other[0], n)),
                ("CHEM.MC.SERIES.WRONG_SERIES_FORMULA", 12 * n + hydrogens(other[1], n)),
                ("CHEM.MC.SERIES.HYDROGEN_MASS_FORGOTTEN_FACTOR", 12 + h),
            ]
            hints = [
                "Molar mass is the sum of the masses of all the atoms in one molecule.",
                "Multiply the number of atoms of each element by that element's atomic mass, then add.",
                "Count the carbon atoms and the hydrogen atoms in the formula, and use the given atomic masses.",
            ]
            steps = [
                f"Carbon: {n} x 12 = {12 * n}. Hydrogen: {h} x 1 = {h}.",
                f"Add them: {mass} g/mol.",
            ]
        elif ask == "n_from_H":
            stem = f"A molecule from the {family} series has {h} hydrogen atoms. How many carbon atoms does it have?"
            var, key = "x", n
            coeff, const = 2, h - d
            cands = [
                ("CHEM.MC.SERIES.WRONG_SERIES_FORMULA", (h - hydrogens_other_offset(o)) // 2)
                for o in other
            ] + [
                ("CHEM.MC.SERIES.HYDROGEN_COUNT_COPIED", h),
                ("CHEM.MC.SERIES.HALF_ONLY", h // 2),
                ("CHEM.MC.SERIES.ONE_BOND_OFF", n + 1),
                ("CHEM.MC.SERIES.ONE_BOND_OFF", n - 1),
            ]
            hints = [
                "Use the general formula of the series, which links the number of hydrogen atoms to the number of carbon atoms.",
                "Write the general formula with the known number of hydrogen atoms on one side, then find n by doing the same operation to each side.",
                f"The general formula of the {family} series is {GENERAL[d]}: put the hydrogen number in and solve for n.",
            ]
            steps = [
                f"The general formula is {GENERAL[d]}.",
                f"Set it equal to {h}: 2n {'+' if d >= 0 else '-'} {abs(d)} = {h}."
                if d != 0
                else f"Set it equal to {h}: 2n = {h}.",
                f"Do the same operation to each side to get n = {n}.",
            ]
        else:
            raise IllPosed("unknown_ask")
        answer = linear_answer(var, key)
        chem: dict[str, Any] = {"family": self.id, "series": family, "ask": ask}
        chem.update({"h": h} if ask == "n_from_H" else {"n": n})
        wrong = []
        for mc, v in cands:
            if v != key and v >= 1:
                wrong.append((mc, linear_answer(var, v), str(v)))
        return Built(
            spec=linear_spec(var, coeff, const, chem),
            answer=answer,
            witness=linear_answer(var, key),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=str(key),
            tokens=[str(key)],
            difficulty=difficulty(
                {"H": 0.3, "bonds": 0.5, "mass": 0.45, "n_from_H": 0.5}[ask],
                steps=len(steps) - 1,
                size=n // 3,
            ),
            role="apply",
            prediction="Before you calculate, will the number be larger or smaller than the number of carbon atoms?",
            methods=[
                FnMethod(
                    "chem.series_general_formula",
                    "chem.general_formula",
                    "homologous_series",
                    _series_m1,
                ),
                FnMethod(
                    "chem.series_chain_build",
                    "chem.chain_construction",
                    "homologous_series",
                    _series_m2,
                ),
            ],
            slug=f"{family}.{n}.{ask}",
        )


def hydrogens_other_offset(family: str) -> int:
    return D_OF[family]


def _ask_value(ask: str, n: int, h: int, bonds: int) -> int:
    return {"H": h, "bonds": bonds, "mass": 12 * n + h, "n_from_H": n}[ask]


def _series_m1(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    fam, ask = c["series"], c["ask"]
    if ask == "n_from_H":
        twice = int(c["h"]) - D_OF[fam]
        if twice % 2:
            raise ValueError("no whole number of carbons")
        return linear_answer("x", twice // 2)
    n = int(c["n"])
    h = 2 * n + D_OF[fam]
    bonds = {"alkane": 3 * n + 1, "alkene": 3 * n, "alkyne": 3 * n - 1}[fam]
    return linear_answer("x", _ask_value(ask, n, h, bonds))


def _series_m2(spec: Mapping[str, Any]) -> Any:
    c = spec["chem"]
    fam, ask = c["series"], c["ask"]
    if ask == "n_from_H":
        for m in range(1, 60):  # grow the chain until its built hydrogen count matches
            if fam != "alkane" and m < 2:
                continue
            if build_chain(fam, m)[0] == int(c["h"]):
                return linear_answer("x", m)
        raise ValueError("no chain matches")
    n = int(c["n"])
    h, bonds, _ = build_chain(fam, n)
    mass = int(atomic_mass("C")) * n + int(atomic_mass("H")) * h
    return linear_answer("x", {"H": h, "bonds": bonds, "mass": mass}[ask])


# ---------------------------------------------------------------- series identification


class SeriesIdentify(Family):
    id = "series_identify"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        x, y = int(p["x"]), int(p["y"])
        if x < 2:
            raise IllPosed("one_carbon_hydrocarbon_has_one_formula")
        if y < 2 or y % 2:
            raise IllPosed("hydrogen_count_must_be_even_and_at_least_two")
        d = y - 2 * x
        if d not in GENERAL:
            raise IllPosed("fits_none_of_the_three_series")
        if y > 2 * x + 2:
            raise IllPosed("too_many_hydrogens")
        formula = f"C{x}H{y}" if x > 1 else f"CH{y}"
        stem = pick(
            [
                f"Which general formula does the hydrocarbon {formula} fit, where n is the number of carbon atoms?",
                f"A hydrocarbon has the molecular formula {formula}. Which general formula, with n carbon atoms, does it follow?",
                f"Which of these general formulas describes {formula}? Here n stands for the number of carbon atoms.",
            ],
            p,
        )
        opts = {2: "CnH2n+2", 0: "CnH2n", -2: "CnH2n-2"}
        key = opts[d]
        wrong = []
        for other, text in opts.items():
            if other != d:
                mc = "CHEM.MC.SERIES.WRONG_SERIES_FORMULA"
                wrong.append((mc, linear_answer("d", other), text))
        wrong.append(
            (
                "CHEM.MC.SERIES.RADICAL_FORMULA_USED",
                {"values": {"d": "none"}, "shown": "CnH2n+1"},
                "CnH2n+1",
            )
        )
        hints = [
            "Compare the number of hydrogen atoms with twice the number of carbon atoms.",
            "Find how many more or fewer hydrogen atoms there are than twice the carbon atoms.",
            "A difference of plus two, zero or minus two matches one of the three general formulas.",
        ]
        steps = [
            f"Twice the number of carbon atoms is {2 * x}.",
            f"The hydrogen count is {y}, which is {d:+d} from that."
            if d
            else f"The hydrogen count is {y}, the same as that.",
            f"That matches {key}.",
        ]
        return Built(
            spec=linear_spec("d", 1, d, {"family": self.id, "x": x, "y": y}),
            answer=linear_answer("d", d),
            witness=linear_answer("d", d),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=key,
            tokens=[key],
            difficulty=difficulty(0.3, steps=1),
            role="recall",
            prediction="Before you decide, will there be more hydrogen atoms than twice the carbon atoms?",
            methods=[
                FnMethod(
                    "chem.identify_difference",
                    "chem.difference_rule",
                    "homologous_series",
                    lambda s: linear_answer("d", int(s["chem"]["y"]) - 2 * int(s["chem"]["x"])),
                ),
                FnMethod(
                    "chem.identify_fit", "chem.formula_fitting", "homologous_series", _identify_m2
                ),
            ],
            slug=f"{x}.{y}",
        )


def _identify_m2(spec: Mapping[str, Any]) -> Any:
    x, y = int(spec["chem"]["x"]), int(spec["chem"]["y"])
    fits = [d for d in (2, 0, -2) if 2 * x + d == y]
    if len(fits) != 1:
        raise ValueError("must fit exactly one formula")
    return linear_answer("d", fits[0])


# ---------------------------------------------------------------- isomer counting


class IsomerCount(Family):
    id = "isomer_count"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        n = int(p["n"])
        if n not in (4, 5, 6, 7, 8):
            raise IllPosed("outside_the_taught_range")
        count = len(S.enumerate_alkanes(n))
        if S.otter_count(n) != count or T.ALKANE_ISOMERS_OEIS[n] != count:
            raise IllPosed("counts_disagree")
        formula = formula_text("alkane", n)
        stem = [
            f"How many different structural isomers (different arrangements of the carbon atoms, with single bonds only) does {formula} have?",
            f"A hydrocarbon has the formula {formula} and only single bonds. How many different carbon skeletons can it have?",
            f"Count the structural isomers of {formula}: in how many different ways can its carbon atoms be joined with single bonds only?",
        ][n % 3]
        known = {k: T.ALKANE_ISOMERS_OEIS[k] for k in (3, 4, 5, 6, 7, 8, 9)}
        cands = [
            ("CHEM.MC.ISO.ONLY_STRAIGHT_CHAIN_COUNTED", 1),
            ("CHEM.MC.ISO.NEIGHBOUR_FORMULA_COUNT", known[n - 1]),
            ("CHEM.MC.ISO.NEIGHBOUR_FORMULA_COUNT", known[n + 1]),
            ("CHEM.MC.ISO.POSITIONS_COUNTED_AS_ISOMERS", n),
            ("CHEM.MC.ISO.ONE_ISOMER_MISSED", count - 1),
            ("CHEM.MC.ISO.ONE_ISOMER_MISSED", count + 1),
        ]
        wrong = [(mc, linear_answer("x", v), str(v)) for mc, v in cands if v != count and v >= 1]
        hints = [
            "Isomers have the same molecular formula but the carbon atoms are joined in a different order.",
            "Start with the longest straight chain, then shorten the main chain by one carbon and place that carbon as a branch in every different position.",
            "A branch at the very end of the chain only lengthens the chain, so it does not give a new isomer. Check that you do not count the same structure twice.",
        ]
        steps = [
            "Write the straight chain of all the carbon atoms: that is one isomer.",
            "Shorten the main chain by one carbon and attach that carbon as a branch at each different position; then shorten again and so on, never counting a copy of one already found.",
            f"Counting every different carbon skeleton gives {count} isomers.",
        ]
        return Built(
            spec=linear_spec("x", 1, count, {"family": self.id, "n": n}),
            answer=linear_answer("x", count),
            witness=linear_answer("x", count),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=str(count),
            tokens=[str(count)],
            difficulty=difficulty(0.55, steps=3, size=n),
            role="apply",
            prediction="Before you count, will there be more or fewer isomers than carbon atoms?",
            methods=[
                FnMethod(
                    "chem.isomers_enumerate",
                    "chem.skeleton_enumeration",
                    "isomerism",
                    lambda s: linear_answer("x", len(S.enumerate_alkanes(int(s["chem"]["n"])))),
                ),
                FnMethod(
                    "chem.isomers_otter",
                    "chem.polya_otter",
                    "isomerism",
                    lambda s: linear_answer("x", S.otter_count(int(s["chem"]["n"]))),
                ),
            ],
            slug=f"{n}",
        )


# ---------------------------------------------------------------- naming


def _name_options(correct: str, wrongs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [(mc, t) for mc, t in wrongs if t and t != correct]


class NameAlkane(Family):
    """IUPAC name of a saturated chain from its condensed formula."""

    id = "name_alkane"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        keys = sorted(T.ALKANE_NAMES)
        formula = keys[int(p["i"])] if int(p["i"]) < len(keys) else None
        if formula is None:
            raise IllPosed("index_out_of_range")
        tree = S.parse_condensed(formula)
        name = S.name_alkane(tree)
        if name != T.ALKANE_NAMES[formula]:
            raise IllPosed("namer_and_table_disagree")
        if re.search(r"\d,\d", name):
            raise IllPosed("locant_list_not_readable_by_the_content_validator")
        carbons = S.carbon_count(tree)
        total = {
            n: [v for k, v in T.ALKANE_NAMES.items() if S.carbon_count(S.parse_condensed(k)) == n]
            for n in range(1, 8)
        }
        same_c = sorted({v for v in total[carbons] if v != name})
        stem = f"What is the IUPAC name of the compound with the condensed formula {formula}?"
        wrongs: list[tuple[str, str]] = []
        alt = S.alternative_numbering(tree)
        if alt:
            wrongs.append(("CHEM.MC.NAME.NUMBERED_FROM_WRONG_END", alt))
        straight = T.ROOTS[carbons] + "ane"
        if straight != name:
            wrongs.append(("CHEM.MC.NAME.BRANCH_COUNTED_IN_CHAIN", straight))
        for other in same_c[:2]:
            wrongs.append(("CHEM.MC.NAME.WRONG_ISOMER", other))
        for off in (carbons - 1, carbons + 1):
            if off in T.ROOTS and off >= 1:
                wrongs.append(("CHEM.MC.NAME.CARBON_MISCOUNT", T.ROOTS[off] + "ane"))
        for mult in ("di", "tri", "tetra"):
            if mult + "methyl" in name or mult + "ethyl" in name:
                wrongs.append(("CHEM.MC.NAME.MULTIPLIER_DROPPED", name.replace(mult, "", 1)))
                break
        wrong = [
            (mc, {**linear_answer("c", carbons), "name": t}, t)
            for mc, t in _name_options(name, wrongs)
        ]
        hints = [
            "Find the longest unbroken chain of carbon atoms. Its length gives the name of the parent alkane.",
            "Anything attached to the longest chain is a side group. Number the chain from the end that gives the side groups the lowest numbers.",
            "Write the side group numbers and names in front of the parent name, using di, tri when a group appears more than once.",
        ]
        steps = [
            "Find the longest chain of carbon atoms; its length sets the parent name.",
            "Number the chain from the end that gives the lowest numbers to the side groups.",
            f"Put the side groups in front of the parent name: {name}.",
        ]
        return Built(
            spec=linear_spec("c", 1, carbons, {"family": self.id, "formula": formula}),
            answer={**linear_answer("c", carbons), "name": name},
            witness=linear_answer("c", carbons),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=name,
            tokens=name_tokens(name),
            difficulty=difficulty(
                0.35 + 0.05 * (name != straight), steps=2 + ("-" in name), size=carbons
            ),
            role="procedure",
            prediction="Before you name it, how many carbon atoms are in the longest chain?",
            methods=[
                FnMethod("chem.name_algorithm", "chem.naming_algorithm", "iupac_naming", _name_m1),
                FnMethod("chem.name_table", "chem.reviewed_table", "iupac_naming", _name_m2),
            ],
            slug=f"{int(p['i'])}",
        )


def _name_m1(spec: Mapping[str, Any]) -> Any:
    tree = S.parse_condensed(spec["chem"]["formula"])
    return {**linear_answer("c", S.carbon_count(tree)), "name": S.name_alkane(tree)}


def _name_m2(spec: Mapping[str, Any]) -> Any:
    formula = spec["chem"]["formula"]
    return {**linear_answer("c", _carbons_by_text(formula)), "name": T.ALKANE_NAMES[formula]}


def _carbons_by_text(formula: str) -> int:
    """Count carbons from the text alone: repeat each bracketed branch by its multiplier first."""
    text = formula
    while True:
        m = re.search(r"\(([^()]*)\)(\d+)", text)
        if not m:
            break
        text = text[: m.start()] + ("(" + m.group(1) + ")") * int(m.group(2)) + text[m.end() :]
    return text.count("C")


class NameUnsaturated(Family):
    id = "name_unsaturated"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        table = {**T.ALKENE_NAMES, **T.ALKYNE_NAMES}
        keys = sorted(table)
        if int(p["i"]) >= len(keys):
            raise IllPosed("index_out_of_range")
        formula = keys[int(p["i"])]
        tree = S.parse_condensed(formula)
        name = S.name_unsaturated(tree)
        if name != table[formula]:
            raise IllPosed("namer_and_table_disagree")
        n = S.carbon_count(tree)
        kind = "ene" if "ene" in name else "yne"
        other_kind = "yne" if kind == "ene" else "ene"
        root = T.ROOTS[n]

        def nm(length: int, loc: int | None, suffix: str) -> str:
            if length <= 3:
                return T.ROOTS[length] + suffix
            return f"{T.ROOTS[length]}-{loc}-{suffix}"

        wrongs: list[tuple[str, str]] = []
        loc = int(name.split("-")[1]) if name.count("-") == 2 else None
        if loc is not None:
            far = n - loc
            wrongs.append(("CHEM.MC.NAME.NUMBERED_FROM_WRONG_END", nm(n, n - loc, kind)))
            wrongs.append(("CHEM.MC.NAME.POSITION_OF_BOND_NOT_GIVEN", root + kind))
            _ = far
        wrongs.append(
            ("CHEM.MC.NAME.SUFFIX_MIXED", nm(n, loc, "ane") if loc is not None else root + "ane")
        )
        wrongs.append(("CHEM.MC.NAME.SUFFIX_MIXED", nm(n, loc, other_kind) if n > 1 else ""))
        for off in (n - 1, n + 1):
            if 2 <= off <= 6:
                wrongs.append(("CHEM.MC.NAME.CARBON_MISCOUNT", nm(off, 1, kind)))
        wrong = [
            (mc, {**linear_answer("c", n), "name": t}, t) for mc, t in _name_options(name, wrongs)
        ]
        stem = f"What is the IUPAC name of the compound with the condensed formula {formula}?"
        hints = [
            "Count the carbon atoms in the unbroken chain to find the parent name, then look at the bond between carbon atoms that is not single.",
            "A double bond changes the ending to -ene and a triple bond changes it to -yne.",
            "Number the chain from the end nearest the multiple bond, and write the number of its first carbon before the ending when more than one position is possible.",
        ]
        steps = [
            f"The chain has {n} carbon atoms, so the parent is '{root}'.",
            f"The multiple bond decides the ending: {'-ene (double bond)' if kind == 'ene' else '-yne (triple bond)'}.",
            f"Number from the end nearest the multiple bond: the name is {name}.",
        ]
        return Built(
            spec=linear_spec("c", 1, n, {"family": self.id, "formula": formula}),
            answer={**linear_answer("c", n), "name": name},
            witness=linear_answer("c", n),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=name,
            tokens=name_tokens(name),
            difficulty=difficulty(0.4, steps=3, size=n),
            role="procedure",
            prediction="Before you name it, does the ending change from -ane?",
            methods=[
                FnMethod(
                    "chem.unsat_algorithm", "chem.naming_algorithm", "iupac_naming", _unsat_m1
                ),
                FnMethod("chem.unsat_table", "chem.reviewed_table", "iupac_naming", _unsat_m2),
            ],
            slug=f"{int(p['i'])}",
        )


def _unsat_m1(spec: Mapping[str, Any]) -> Any:
    tree = S.parse_condensed(spec["chem"]["formula"])
    return {**linear_answer("c", S.carbon_count(tree)), "name": S.name_unsaturated(tree)}


def _unsat_m2(spec: Mapping[str, Any]) -> Any:
    formula = spec["chem"]["formula"]
    return {
        **linear_answer("c", _carbons_by_text(formula)),
        "name": {**T.ALKENE_NAMES, **T.ALKYNE_NAMES}[formula],
    }


class NameFunctional(Family):
    id = "name_functional"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        group, n = str(p["group"]), int(p["n"])
        if group not in T.FUNCTIONAL or n not in T.FUNCTIONAL[group]:
            raise IllPosed("not_in_table")
        formula = S.functional_formula(group, n)
        name, carbons = S.name_functional(formula)
        if name != T.FUNCTIONAL[group][n] or carbons != n:
            raise IllPosed("namer_and_table_disagree")
        wrongs: list[tuple[str, str]] = []
        for other in T.FUNCTIONAL:
            if other != group and n in T.FUNCTIONAL[other]:
                wrongs.append(("CHEM.MC.NAME.GROUP_SUFFIX_MIXED", T.FUNCTIONAL[other][n]))
        if group in ("aldehyde", "carboxylic acid") and n - 1 in T.FUNCTIONAL[group]:
            wrongs.append(("CHEM.MC.NAME.GROUP_CARBON_NOT_COUNTED", T.FUNCTIONAL[group][n - 1]))
        if n + 1 in T.FUNCTIONAL[group]:
            wrongs.append(("CHEM.MC.NAME.CARBON_MISCOUNT", T.FUNCTIONAL[group][n + 1]))
        if n - 1 in T.FUNCTIONAL[group]:
            wrongs.append(("CHEM.MC.NAME.CARBON_MISCOUNT", T.FUNCTIONAL[group][n - 1]))
        wrong = [
            (mc, {**linear_answer("c", carbons), "name": t}, t)
            for mc, t in _name_options(name, wrongs)
        ]
        stem = f"What is the IUPAC name of the compound with the condensed formula {formula}?"
        hints = [
            "Count all the carbon atoms in the chain, including the carbon inside a group such as CHO or COOH, to get the parent name.",
            "The group at the end of the chain decides the ending of the name, or a prefix such as chloro.",
            "Put the parent name and the ending or prefix together, and add the number one where the position of the group at the end of a longer chain must be stated.",
        ]
        steps = [
            f"The chain has {n} carbon atoms, so the parent is '{T.ROOTS[n]}an-'.",
            f"The end group is the {group} group, which sets the ending or prefix.",
            f"The name is {name}.",
        ]
        return Built(
            spec=linear_spec("c", 1, n, {"family": self.id, "formula": formula}),
            answer={**linear_answer("c", n), "name": name},
            witness=linear_answer("c", n),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=name,
            tokens=[name],
            difficulty=difficulty(0.4, steps=3, size=n),
            role="procedure",
            prediction="Before you name it, which group at the end of the chain gives the ending?",
            methods=[
                FnMethod(
                    "chem.functional_algorithm", "chem.naming_algorithm", "iupac_naming", _func_m1
                ),
                FnMethod("chem.functional_table", "chem.reviewed_table", "iupac_naming", _func_m2),
            ],
            slug=f"{group.replace(' ', '_')}.{n}",
        )


def _func_m1(spec: Mapping[str, Any]) -> Any:
    name, carbons = S.name_functional(spec["chem"]["formula"])
    return {**linear_answer("c", carbons), "name": name}


def _func_m2(spec: Mapping[str, Any]) -> Any:
    formula = spec["chem"]["formula"]
    end = formula.split("-")[-1]
    group = {"OH": "alcohol", "Cl": "haloalkane", "CHO": "aldehyde", "COOH": "carboxylic acid"}[end]
    body = [piece for piece in formula.split("-")[:-1] if piece != "H"]
    carbons = len(body) + (1 if group in ("aldehyde", "carboxylic acid") else 0)
    return {**linear_answer("c", carbons), "name": T.FUNCTIONAL[group][carbons]}


CARBON_FAMILIES: dict[str, Family] = {
    f.id: f
    for f in (
        HomologousSeries(),
        SeriesIdentify(),
        IsomerCount(),
        NameAlkane(),
        NameUnsaturated(),
        NameFunctional(),
    )
}
