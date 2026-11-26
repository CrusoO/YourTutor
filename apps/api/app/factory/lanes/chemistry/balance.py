# ruff: noqa: E501
"""Chapter: Chemical Reactions and Equations. Balancing, coefficients, types, combustion, atoms.

Balance families are checked by the kernel's integer-matrix verifier (every atom balances, the
coefficients are whole, smallest and unique). Two independent Methods recompute the coefficients
from the spec alone: an exact Gauss-Jordan over Fractions written in this lane, and a SymPy
nullspace. The reaction-type family also has a rule method (structure of the formulas) and a
lookup method (the reviewed table). Misconception-tagged wrong options are built here and each
is proved wrong (unbalanced, or not smallest) before it is offered.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import sympy

from app.factory.lanes.chemistry import tables as T
from app.factory.lanes.chemistry.core import (
    Built,
    Family,
    FnMethod,
    IllPosed,
    balance_spec,
    difficulty,
    linear_answer,
    linear_spec,
)
from app.factory.lanes.chemistry.formula import atoms, atoms_expanded, equation_text, is_element

# ---------------------------------------------------------------- independent solvers


def _matrix(left: list[str], right: list[str]) -> list[list[int]]:
    counts = [atoms(f) for f in left + right]
    sign = [1] * len(left) + [-1] * len(right)
    elements = sorted({e for c in counts for e in c})
    return [[s * c.get(e, 0) for s, c in zip(sign, counts, strict=True)] for e in elements]


def solve_own(left: list[str], right: list[str]) -> list[int]:
    """Gauss-Jordan over Fractions; the null space must have dimension one."""
    rows = [[Fraction(x) for x in r] for r in _matrix(left, right)]
    n = len(left) + len(right)
    pivots: list[int] = []
    r = 0
    for col in range(n):
        pivot = next((i for i in range(r, len(rows)) if rows[i][col] != 0), None)
        if pivot is None:
            continue
        rows[r], rows[pivot] = rows[pivot], rows[r]
        lead = rows[r][col]
        rows[r] = [x / lead for x in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][col] != 0:
                f = rows[i][col]
                rows[i] = [a - f * b for a, b in zip(rows[i], rows[r], strict=True)]
        pivots.append(col)
        r += 1
    free = [c for c in range(n) if c not in pivots]
    if len(free) != 1:
        raise ValueError("balance is not unique")
    vec = [Fraction(0)] * n
    vec[free[0]] = Fraction(1)
    for row, p in zip(rows, pivots, strict=False):
        vec[p] = -row[free[0]]
    den = math.lcm(*[x.denominator for x in vec])
    ints = [int(x * den) for x in vec]
    g = math.gcd(*ints)
    ints = [i // g for i in ints]
    if all(i < 0 for i in ints):
        ints = [-i for i in ints]
    if any(i <= 0 for i in ints):
        raise ValueError("no positive solution")
    return ints


def solve_sympy(left: list[str], right: list[str]) -> list[int]:
    ns = sympy.Matrix(_matrix(left, right)).nullspace()
    if len(ns) != 1:
        raise ValueError("balance is not unique")
    vec = list(ns[0])
    den = sympy.ilcm(*[sympy.fraction(x)[1] for x in vec])
    ints = [int(x * den) for x in vec]
    g = math.gcd(*ints)
    ints = [i // g for i in ints]
    if all(i < 0 for i in ints):
        ints = [-i for i in ints]
    if any(i <= 0 for i in ints):
        raise ValueError("no positive solution")
    return ints


def _sides(spec: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    left = [s["formula"] for s in spec["species"] if s["side"] == "L"]
    right = [s["formula"] for s in spec["species"] if s["side"] == "R"]
    return left, right


def is_balanced(left: list[str], right: list[str], coeffs: list[int]) -> bool:
    total: Counter[str] = Counter()
    for f, c, s in zip(left + right, coeffs, [1] * len(left) + [-1] * len(right), strict=True):
        for e, n in atoms(f).items():
            total[e] += s * c * n
    return not any(total.values())


# ---------------------------------------------------------------- reaction type: rule and lookup


def classify_by_rule(left: list[str], right: list[str]) -> str:
    """Structure of the formulas decides the type; no table is read."""
    elem_l = [is_element(f) for f in left]
    elem_r = [is_element(f) for f in right]
    if len(left) == 1 and len(right) >= 2:
        return T.DECOMPOSITION
    if len(left) >= 2 and len(right) == 1:
        return T.COMBINATION
    if len(left) == 2 and len(right) == 2:
        if sum(elem_l) == 1 and sum(elem_r) == 1:
            free = left[elem_l.index(True)]
            comp = left[elem_l.index(False)]
            out = right[elem_r.index(True)]
            prod = right[elem_r.index(False)]
            freed = set(atoms(out))
            if freed <= set(atoms(comp)) and set(atoms(free)) <= set(atoms(prod)):
                return T.DISPLACEMENT
        if not any(elem_l) and not any(elem_r):
            parts_l = [set(atoms(f)) for f in left]
            parts_r = [set(atoms(f)) for f in right]
            if all(pr & pl for pr in parts_r for pl in parts_l) and set().union(
                *parts_l
            ) == set().union(*parts_r):
                return T.DOUBLE
    raise ValueError("type is outside the closed rule set")


def classify_by_table(rid: str) -> str:
    return T.REACTION_BY_ID[rid][1]


# ---------------------------------------------------------------- wrong-option makers


def _eq(left: list[str], right: list[str], coeffs: list[int]) -> str:
    return equation_text(left, right, coeffs)


def _subscript_variant(left: list[str], right: list[str]) -> tuple[list[str], list[str]] | None:
    """All coefficients 1, one subscript changed so the atoms balance (the classic shortcut)."""
    species = left + right
    for i, f in enumerate(species):
        if "(" in f:
            continue
        for e, n in atoms(f).items():
            for new in range(1, 5):
                if new == n:
                    continue
                if n == 1 and new == 1:
                    continue
                # rebuild this formula with element e having subscript `new`
                import re

                def sub(m: Any, e: str = e, new: int = new) -> str:
                    return (
                        m.group(1) + (str(new) if new > 1 else "")
                        if m.group(1) == e
                        else m.group(0)
                    )

                alt = re.sub(r"([A-Z][a-z]?)(\d*)", sub, f)
                if alt == f:
                    continue
                trial = species[:i] + [alt] + species[i + 1 :]
                try:
                    if is_balanced(trial[: len(left)], trial[len(left) :], [1] * len(trial)):
                        return trial[: len(left)], trial[len(left) :]
                except ValueError:
                    continue
    return None


def wrong_equations(
    left: list[str], right: list[str], key: list[int]
) -> list[tuple[str, dict[str, Any], str]]:
    """(misconception, record, text) candidates for 'which is the balanced equation'."""
    out: list[tuple[str, dict[str, Any], str]] = []
    sub = _subscript_variant(left, right)
    if sub is not None:
        ones = [1] * (len(left) + len(right))
        out.append(
            (
                "CHEM.MC.BAL.SUBSCRIPT_CHANGED",
                {"formulas": sub[0] + sub[1], "coefficients": ones},
                _eq(sub[0], sub[1], ones),
            )
        )
    doubled = [2 * c for c in key]
    out.append(("CHEM.MC.BAL.NOT_SMALLEST", {"coefficients": doubled}, _eq(left, right, doubled)))
    for i in range(len(key) - 1, -1, -1):
        for delta in (1, -1):
            bumped = list(key)
            bumped[i] += delta
            if bumped[i] >= 1 and not is_balanced(left, right, bumped):
                out.append(
                    (
                        "CHEM.MC.BAL.ONE_COEFFICIENT_OFF",
                        {"coefficients": bumped},
                        _eq(left, right, bumped),
                    )
                )
                break
    ones = [1] * len(key)
    if not is_balanced(left, right, ones):
        out.append(("CHEM.MC.BAL.NOTHING_CHANGED", {"coefficients": ones}, _eq(left, right, ones)))
    for i in range(len(key)):
        for j in range(i + 1, len(key)):
            if key[i] != key[j]:
                swapped = list(key)
                swapped[i], swapped[j] = swapped[j], swapped[i]
                if not is_balanced(left, right, swapped):
                    out.append(
                        (
                            "CHEM.MC.BAL.COEFFICIENTS_SWAPPED",
                            {"coefficients": swapped},
                            _eq(left, right, swapped),
                        )
                    )
    return out


def _first_unbalanced(left: list[str], right: list[str]) -> tuple[str, int, int]:
    cl: Counter[str] = Counter()
    cr: Counter[str] = Counter()
    for f in left:
        cl.update(atoms(f))
    for f in right:
        cr.update(atoms(f))
    for e in sorted(set(cl) | set(cr)):
        if cl[e] != cr[e]:
            return e, cl[e], cr[e]
    raise IllPosed("already_balanced_skeleton")


def _methods_balance(extra: list[FnMethod] | None = None) -> list[Any]:
    def own(spec: Mapping[str, Any]) -> Any:
        left, right = _sides(spec)
        return {"coefficients": solve_own(left, right)}

    def sym(spec: Mapping[str, Any]) -> Any:
        left, right = _sides(spec)
        return {"coefficients": solve_sympy(left, right)}

    return [
        FnMethod("chem.nullspace_fraction", "chem.fraction_elimination", "atom_counting", own),
        FnMethod("chem.nullspace_sympy", "chem.sympy_nullspace", "atom_counting", sym),
        *(extra or []),
    ]


def _skeleton(rid: str) -> tuple[list[str], list[str], list[int]]:
    _, _, left, right, coef = T.REACTION_BY_ID[rid]
    return list(left), list(right), list(coef)


# ---------------------------------------------------------------- families


class BalanceEquation(Family):
    """Choose the balanced equation for a skeleton from the closed reaction table."""

    id = "bal_eq"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        rid = str(p["rid"])
        if rid not in T.REACTION_BY_ID:
            raise IllPosed("unknown_reaction")
        left, right, coef = _skeleton(rid)
        solved = solve_own(left, right)
        if solved != coef:
            raise IllPosed("table_and_solver_disagree")
        if any("(" in f and f.split("(")[1].split(")")[0].isalpha() for f in left + right):
            raise IllPosed("stem_would_show_bracketed_letters")
        skeleton = equation_text(left, right)
        wording = str(p["wording"])
        stem = (
            f"A student writes this unbalanced chemical equation: {skeleton}. Which option shows the correct balanced equation?"
            if wording == "student"
            else f"Balance the chemical equation {skeleton}. Which option gives the smallest whole-number coefficients?"
        )
        element, nl, nr = _first_unbalanced(left, right)
        key_text = _eq(left, right, coef)
        spec = balance_spec(left, right, {"family": self.id, "rid": rid})
        answer = {"coefficients": coef}
        wrong = wrong_equations(left, right, coef)
        steps = [
            f"Count the atoms of each element in {skeleton}: for {element} there are {nl} on the left and {nr} on the right, so the equation is not balanced.",
            "Choose whole-number coefficients (the numbers written in front of the formulas) so that every element has the same count on both sides. Do not change the small numbers inside a formula.",
            f"Check each element again with the balanced equation {key_text}.",
        ]
        hints = [
            "Count the atoms of every element on the left side and on the right side. Which element has a different count on the two sides?",
            "Only the numbers written in front of the formulas may change. The small numbers inside a formula stay as they are.",
            f"Start with {element}: it is {nl} on the left and {nr} on the right in the unbalanced skeleton. Choose a front number that makes them equal, then recount the other elements.",
        ]
        return Built(
            spec=spec,
            answer=answer,
            witness={"atom_counts": [atoms(f) for f in left + right]},
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=key_text,
            tokens=[key_text],
            difficulty=difficulty(0.35, steps=len(left + right) - 2, size=sum(coef) // 4),
            role="procedure",
            prediction="Before you balance it, which element do you expect to be out of balance first?",
            methods=_methods_balance(),
            slug=f"{rid}.{wording}",
        )


def _coef_wrongs(
    left: list[str], right: list[str], key: list[int], index: int
) -> list[tuple[str, int]]:
    """(misconception, wrong number) for 'the coefficient of species i'."""
    species = left + right
    out: list[tuple[str, int]] = []
    sub = list(atoms(species[index]).values())[0]
    out.append(("CHEM.MC.BAL.SUBSCRIPT_AS_COEFFICIENT", sub))
    out.append(("CHEM.MC.BAL.NOT_SMALLEST", 2 * key[index]))
    other = key[(index + 1) % len(key)]
    out.append(("CHEM.MC.BAL.WRONG_SPECIES_READ", other))
    out.append(("CHEM.MC.BAL.ONE_COEFFICIENT_OFF", key[index] + 1))
    out.append(("CHEM.MC.BAL.ONE_COEFFICIENT_OFF", key[index] + 2))
    if key[index] > 1:
        out.append(("CHEM.MC.BAL.ONE_COEFFICIENT_OFF", key[index] - 1))
    return out


class BalanceCoefficient(Family):
    """One number from the balanced equation: a named coefficient, or the total."""

    id = "bal_coef"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        rid, ask = str(p["rid"]), str(p["ask"])
        left, right, coef = _skeleton(rid)
        if solve_own(left, right) != coef:
            raise IllPosed("table_and_solver_disagree")
        if any("(" in f and f.split("(")[1].split(")")[0].isalpha() for f in left + right):
            raise IllPosed("stem_would_show_bracketed_letters")
        species = left + right
        skeleton = equation_text(left, right)
        if ask == "total":
            value = sum(coef)
            stem = f"The equation {skeleton} is balanced using the smallest whole-number coefficients. What is the sum of all the coefficients?"
            what = "total"
            cands = [
                ("CHEM.MC.BAL.NOT_SMALLEST", 2 * value),
                ("CHEM.MC.BAL.COEFFICIENTS_NOT_ADDED", len(species)),
                ("CHEM.MC.BAL.ONE_SIDE_ONLY", sum(coef[: len(left)])),
                ("CHEM.MC.BAL.ONE_SIDE_ONLY", sum(coef[len(left) :])),
                ("CHEM.MC.BAL.ONE_COEFFICIENT_OFF", value + 1),
                ("CHEM.MC.BAL.ONE_COEFFICIENT_OFF", value - 1),
            ]
            index = -1
            hint3 = "Balance the reaction first, then add the numbers in front of every formula. A formula with no number in front counts as 1."
        else:
            index = int(ask.split(":")[1])
            if index >= len(species):
                raise IllPosed("species_index_out_of_range")
            value = coef[index]
            stem = f"When {skeleton} is balanced with the smallest whole-number coefficients, what is the coefficient of {species[index]}?"
            what = species[index]
            cands = _coef_wrongs(left, right, coef, index)
            hint3 = f"After balancing, read the number written in front of {species[index]}. A formula with no number in front has coefficient 1."
        element, nl, nr = _first_unbalanced(left, right)
        answer = {"coefficients": coef, "ask": ask, "value": value}
        wrong: list[tuple[str, dict[str, Any], str]] = []
        for mc, num in cands:
            if num >= 1 and num != value:
                wrong.append((mc, {**answer, "value": num}, str(num)))
        steps = [
            f"Count atoms in {skeleton}: for {element} there are {nl} on the left and {nr} on the right, so it needs balancing.",
            "Choose whole-number coefficients that give every element the same count on both sides, using the smallest numbers possible.",
            f"The balanced equation is {_eq(left, right, coef)}.",
            f"Read the {'sum of all coefficients' if ask == 'total' else 'coefficient of ' + what}.",
        ]
        hints = [
            "Balance the whole reaction first by counting the atoms of every element on the left and on the right.",
            "Only the numbers in front of formulas may change. The small numbers inside a formula stay as they are.",
            hint3,
        ]
        return Built(
            spec=balance_spec(left, right, {"family": self.id, "rid": rid, "ask": ask}),
            answer=answer,
            witness={"atom_counts": [atoms(f) for f in species]},
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=str(value),
            tokens=[str(value)],
            difficulty=difficulty(0.4, steps=len(species) - 2, size=sum(coef) // 4),
            role="procedure",
            prediction="Before you balance it, is the number you want more likely to be 1 or bigger than 1?",
            methods=_coef_methods(),
            slug=f"{rid}.{ask.replace(':', '_')}",
        )


def _coef_methods() -> list[Any]:
    def own(spec: Mapping[str, Any]) -> Any:
        left, right = _sides(spec)
        return _coef_record(spec, solve_own(left, right))

    def sym(spec: Mapping[str, Any]) -> Any:
        left, right = _sides(spec)
        return _coef_record(spec, solve_sympy(left, right))

    return [
        FnMethod("chem.nullspace_fraction", "chem.fraction_elimination", "atom_counting", own),
        FnMethod("chem.nullspace_sympy", "chem.sympy_nullspace", "atom_counting", sym),
    ]


def _coef_record(spec: Mapping[str, Any], coef: list[int]) -> dict[str, Any]:
    ask = str(spec["chem"]["ask"])
    value = sum(coef) if ask == "total" else coef[int(ask.split(":")[1])]
    return {"coefficients": coef, "ask": ask, "value": value}


_TYPE_KEY = {
    T.COMBINATION: "COMBINATION",
    T.DECOMPOSITION: "DECOMPOSITION",
    T.DISPLACEMENT: "DISPLACEMENT",
    T.DOUBLE: "DOUBLE",
}
TYPE_RULE = {
    T.COMBINATION: "two or more substances join to make one product",
    T.DECOMPOSITION: "one substance breaks into two or more simpler substances",
    T.DISPLACEMENT: "a more reactive element takes the place of an element in a compound",
    T.DOUBLE: "two compounds swap partners to make two new compounds",
}
TYPE_LABEL = {
    T.COMBINATION: "Combination reaction",
    T.DECOMPOSITION: "Decomposition reaction",
    T.DISPLACEMENT: "Displacement reaction",
    T.DOUBLE: "Double displacement reaction",
}


def type_mc(key: str, chosen: str) -> str:
    return f"CHEM.MC.TYPE.{_TYPE_KEY[key]}_AS_{_TYPE_KEY[chosen]}"


class ReactionType(Family):
    """Classify a balanced reaction into one of four types, by structure and by the table."""

    id = "rxn_type"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        rid = str(p["rid"])
        left, right, coef = _skeleton(rid)
        if solve_own(left, right) != coef:
            raise IllPosed("table_and_solver_disagree")
        if any("(" in f and f.split("(")[1].split(")")[0].isalpha() for f in left + right):
            raise IllPosed("stem_would_show_bracketed_letters")
        kind = classify_by_rule(left, right)
        if kind != classify_by_table(rid):
            raise IllPosed("rule_and_table_disagree")
        eq = _eq(left, right, coef)
        stem = f"Look at the balanced equation {eq}. Which type of reaction is this?"
        answer = {"coefficients": coef, "type": kind}
        wrong = [
            (type_mc(kind, other), {**answer, "type": other}, TYPE_LABEL[other])
            for other in T.TYPES
            if other != kind
        ]
        hints = [
            "Count how many substances are on the left of the arrow and how many are on the right.",
            "Check whether each substance is a single element or a compound made of more than one element.",
            "Ask what happens to the partners: do substances join, split, or does one element replace another?",
        ]
        steps = [
            f"The left side has {len(left)} substance(s) and the right side has {len(right)}.",
            "Look at whether each formula is one element or a compound, and at how the elements are rearranged.",
            f"Here {TYPE_RULE[kind]}, so it is a {kind} reaction.",
        ]

        def rule(spec: Mapping[str, Any]) -> Any:
            lf, rt = _sides(spec)
            return {"coefficients": solve_own(lf, rt), "type": classify_by_rule(lf, rt)}

        def lookup(spec: Mapping[str, Any]) -> Any:
            lf, rt = _sides(spec)
            return {
                "coefficients": solve_sympy(lf, rt),
                "type": classify_by_table(str(spec["chem"]["rid"])),
            }

        return Built(
            spec=balance_spec(left, right, {"family": self.id, "rid": rid}),
            answer=answer,
            witness={"atom_counts": [atoms(f) for f in left + right]},
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=TYPE_LABEL[kind],
            tokens=[kind, TYPE_LABEL[kind], kind.split()[0]],
            difficulty=difficulty(0.3, steps=1),
            role="recall",
            prediction="Before you decide, how many substances join or split in this reaction?",
            methods=[
                FnMethod("chem.type_rule", "chem.structure_rule", "reaction_types", rule),
                FnMethod("chem.type_table", "chem.reviewed_table", "reaction_types", lookup),
            ],
            slug=f"{rid}",
        )


FAMILY_LABEL = {
    "alkane": ("CnH2n+2", 2, 2),
    "alkene": ("CnH2n", 2, 0),
    "alkyne": ("CnH2n-2", 2, -2),
}


def hydrocarbon(family: str, n: int) -> str:
    h = {"alkane": 2 * n + 2, "alkene": 2 * n, "alkyne": 2 * n - 2}[family]
    return f"C{n}H{h}" if n > 1 else f"CH{h}"


class Combustion(Family):
    """Balance the complete burning of a hydrocarbon and read one number."""

    id = "combustion"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        fam, n, ask = str(p["family"]), int(p["n"]), str(p["ask"])
        if fam != "alkane" and n < 2:
            raise IllPosed("unsaturated_needs_two_carbons")
        formula = hydrocarbon(fam, n)
        left, right = [formula, "O2"], ["CO2", "H2O"]
        coef = solve_own(left, right)
        species = left + right
        idx = {"O2": 1, "CO2": 2, "H2O": 3, "total": -1}[ask]
        value = sum(coef) if idx < 0 else coef[idx]
        skeleton = equation_text(left, right)
        name = {"alkane": "an alkane", "alkene": "an alkene", "alkyne": "an alkyne"}[fam]
        if idx < 0:
            stem = f"{formula}, {name}, burns completely in oxygen: {skeleton}. After balancing with the smallest whole numbers, what is the sum of all the coefficients?"
            hint3 = "Balance carbon first, then hydrogen, then oxygen last. Then add all four numbers in front of the formulas."
            cands = [("CHEM.MC.BAL.NOT_SMALLEST", 2 * value), ("CHEM.MC.BAL.COEFFICIENTS_NOT_ADDED", 4),
                     ("CHEM.MC.BAL.ONE_COEFFICIENT_OFF", value + 1), ("CHEM.MC.BAL.ONE_COEFFICIENT_OFF", value - 1),
                     ("CHEM.MC.BAL.ONE_COEFFICIENT_OFF", value + 2)]  # fmt: skip
        else:
            stem = f"{formula}, {name}, burns completely in oxygen: {skeleton}. After balancing with the smallest whole numbers, what is the coefficient of {species[idx]}?"
            hint3 = f"Balance carbon first, then hydrogen, then oxygen last. Then read the number in front of {species[idx]}."
            cands = [("CHEM.MC.BAL.NOT_SMALLEST", 2 * value), ("CHEM.MC.BAL.WRONG_SPECIES_READ", coef[(idx + 1) % 4]),
                     ("CHEM.MC.BAL.WRONG_SPECIES_READ", coef[(idx + 2) % 4]),
                     ("CHEM.MC.BAL.OXYGEN_ATOMS_ONLY_ON_ONE_SIDE", coef[2] + coef[3]),
                     ("CHEM.MC.BAL.ONE_COEFFICIENT_OFF", value + 1), ("CHEM.MC.BAL.ONE_COEFFICIENT_OFF", value + 2)]  # fmt: skip
        answer = {"coefficients": coef, "ask": ask, "value": value}
        wrong = [(mc, {**answer, "value": v}, str(v)) for mc, v in cands if v >= 1 and v != value]
        steps = [
            f"Balance carbon first: {formula} has {atoms(formula)['C']} carbon atom(s), so CO2 gets the matching number in front.",
            "Balance hydrogen next using H2O, then count all the oxygen atoms on the right to find the number of O2.",
            "If a half-number is needed, double every coefficient so that all are whole numbers.",
            f"The balanced equation is {_eq(left, right, coef)}.",
        ]
        hints = [
            "Burning a hydrocarbon in plenty of oxygen gives carbon dioxide and water. Count carbon atoms first.",
            "Balance carbon, then hydrogen, and leave oxygen for last because oxygen gas appears on one side only.",
            hint3,
        ]

        def closed(spec: Mapping[str, Any]) -> Any:
            f = spec["chem"]
            c = atoms(f["formula"])
            x, y = c["C"], c.get("H", 0)
            base = [Fraction(1), Fraction(x) + Fraction(y, 4), Fraction(x), Fraction(y, 2)]
            den = math.lcm(*[b.denominator for b in base])
            ints = [int(b * den) for b in base]
            g = math.gcd(*ints)
            ints = [i // g for i in ints]
            return _combust_record(f["ask"], ints)

        def sym(spec: Mapping[str, Any]) -> Any:
            lf, rt = _sides(spec)
            return _combust_record(spec["chem"]["ask"], solve_sympy(lf, rt))

        return Built(
            spec=balance_spec(left, right, {"family": self.id, "formula": formula, "ask": ask}),
            answer=answer,
            witness={"atom_counts": [atoms(f) for f in species]},
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=str(value),
            tokens=[str(value)],
            difficulty=difficulty(0.5, steps=3, size=n),
            role="apply",
            prediction="Before you balance it, which substance needs the largest coefficient?",
            methods=[
                FnMethod(
                    "chem.combustion_closed_form", "chem.closed_form", "atom_counting", closed
                ),
                FnMethod("chem.nullspace_sympy", "chem.sympy_nullspace", "atom_counting", sym),
            ],
            slug=f"{fam}.{n}.{ask}",
        )


def _combust_record(ask: str, coef: list[int]) -> dict[str, Any]:
    idx = {"O2": 1, "CO2": 2, "H2O": 3, "total": -1}[ask]
    return {"coefficients": coef, "ask": ask, "value": sum(coef) if idx < 0 else coef[idx]}


ATOM_FORMULAS = (
    "Al2(SO4)3", "Fe(NO3)3", "Mg(NO3)2", "(NH4)2SO4", "(NH4)3PO4", "Ca3(PO4)2", "Al(NO3)3",
    "Cu(NO3)2", "K2CO3", "Na2SO4", "H2SO4", "C6H12O6", "Fe2O3", "NH4Cl", "Ca(HCO3)2",
    "Mg(HCO3)2", "Zn(NO3)2", "Ba(NO3)2", "Fe2(SO4)3", "(NH4)2CO3",
)  # fmt: skip


def _strip_brackets(formula: str) -> str:
    import re

    return re.sub(r"\)\d*", "", formula.replace("(", ""))


class AtomCount(Family):
    """Total atoms of one element shown by a coefficient and a formula with brackets."""

    id = "atom_count"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        formula = ATOM_FORMULAS[int(p["f"])]
        coef = int(p["coef"])
        elements = sorted(atoms(formula))
        if int(p["el"]) >= len(elements):
            raise IllPosed("element_index_out_of_range")
        el = elements[int(p["el"])]
        names = {"H": "hydrogen", "C": "carbon", "N": "nitrogen", "O": "oxygen", "Na": "sodium", "Mg": "magnesium",
                 "Al": "aluminium", "S": "sulphur", "P": "phosphorus", "Cl": "chlorine", "K": "potassium",
                 "Ca": "calcium", "Fe": "iron", "Cu": "copper", "Zn": "zinc", "Ba": "barium"}  # fmt: skip
        per = atoms(formula)[el]
        total = coef * per
        if "(" not in formula and coef == 1:
            raise IllPosed("nothing_to_expand")
        phrase = f"{coef} {formula}" if coef > 1 else formula
        stem = f"How many atoms of {names[el]} are shown by {phrase}?"
        loose = atoms(_strip_brackets(formula))[el]
        wrong = [
            ("CHEM.MC.ATOM.COEFFICIENT_IGNORED", linear_answer("n", per), str(per)),
            ("CHEM.MC.ATOM.BRACKET_IGNORED", linear_answer("n", coef * loose), str(coef * loose)),
            ("CHEM.MC.ATOM.COEFFICIENT_ADDED", linear_answer("n", coef + per), str(coef + per)),
            ("CHEM.MC.ATOM.BRACKET_AND_COEFFICIENT_IGNORED", linear_answer("n", loose), str(loose)),
            ("CHEM.MC.ATOM.COEFFICIENT_ADDED", linear_answer("n", total + coef), str(total + coef)),
        ]
        inner = f"{coef} x {per}" if coef > 1 else str(per)
        steps = [
            f"Count the {names[el]} atoms in one unit of {formula}: a number outside a bracket multiplies every atom inside it, so one unit has {per}.",
            f"The number in front, {coef}, multiplies the whole formula: {inner} = {total}."
            if coef > 1
            else "There is no number in front, so the count is for one unit.",
            f"The answer is {total} atoms of {names[el]}.",
        ]
        hints = [
            "A small number just after a bracket multiplies every atom inside that bracket.",
            "Count the atoms in one unit of the formula first. The big number in front of the formula multiplies that whole count.",
            f"Look only at {names[el]}: find how many sit in one unit, then use the number in front of the formula.",
        ]
        spec = linear_spec(
            "n", 1, total, {"family": self.id, "formula": formula, "coef": coef, "element": el}
        )

        def m1(s: Mapping[str, Any]) -> Any:
            c = s["chem"]
            return linear_answer("n", c["coef"] * atoms(c["formula"])[c["element"]])

        def m2(s: Mapping[str, Any]) -> Any:
            c = s["chem"]
            return linear_answer("n", c["coef"] * atoms_expanded(c["formula"])[c["element"]])

        return Built(
            spec=spec,
            answer=linear_answer("n", total),
            witness=linear_answer("n", total),
            stem=stem,
            steps=steps,
            hints=hints,
            wrong=wrong,
            key_text=str(total),
            tokens=[str(total)],
            difficulty=difficulty(0.25, steps=1 + (coef > 1), size=total // 6),
            role="procedure",
            prediction="Before you count, will the total be bigger than the number in the formula's small subscript?",
            methods=[
                FnMethod("chem.atoms_stack", "chem.bracket_stack", "atom_counting", m1),
                FnMethod("chem.atoms_expanded", "chem.text_expansion", "atom_counting", m2),
            ],
            slug=f"{int(p['f'])}.{coef}.{el}",
        )


BALANCE_FAMILIES: dict[str, Family] = {
    f.id: f
    for f in (BalanceEquation(), BalanceCoefficient(), ReactionType(), Combustion(), AtomCount())
}
