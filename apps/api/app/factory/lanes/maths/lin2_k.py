# ruff: noqa: E501
"""Pair of Linear Equations: finding k so the pair has no, infinitely many, or not exactly one solution.

The second line is a multiple of the first line, with one number replaced by k. The kernel certifies
the one-unknown condition on k (a determinant, or the proportion of constants) and three lane methods
find k by different routes: the ratio rule, SymPy minors, and a grid search with row reduction.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import sympy

from app.factory.lanes.maths.core import Built, Family, IllPosed, clamp_difficulty, fstr, pick
from app.factory.lanes.maths.lin2_core import F, coef_text, make, method, nice, slug
from app.factory.lanes.maths.reference import lin2 as ref

K = "k"
_NEED = {
    "none": "no solution",
    "infinite": "infinitely many solutions",
    "not_unique": "not exactly one solution",
}
_WORDS = {
    "none": ["have no solution", "be inconsistent", "have no common point"],
    "infinite": ["have infinitely many solutions", "have every point in common"],
    "not_unique": ["fail to have exactly one solution", "have no unique solution"],
}


def _entry(v: Any, var: str, first: bool) -> str:
    if v == K:
        return ("" if first else " + ") + K + var
    return coef_text(v, var, first)


def k_text(row: list[Any]) -> str:
    """a x + b y = c with one of the numbers written as k."""
    a, b, c = row
    out = ""
    for v, var in ((a, "x"), (b, "y")):
        if v != 0:
            out += _entry(v, var, not out)
    return f"{out} = {c if c == K else fstr(c)}"


def _fill(rows: list[list[Any]], k: Fraction) -> list[tuple[Fraction, Fraction, Fraction]]:
    return ref.eqs([[k if v == K else v for v in row] for row in rows])


def _grid_k(rows: list[list[Any]], need: str) -> Fraction:
    hits = []
    for k in ref.GRID:
        pair = _fill(rows, k)
        kind = ref.kind_gauss(pair)
        if (need == "not_unique" and kind != "one") or kind == need:
            hits.append(k)
    if len(hits) != 1:
        raise ValueError(f"{len(hits)} grid values of k")
    return hits[0]


def _sympy_k(rows: list[list[Any]], need: str) -> Fraction:
    k = sympy.Symbol("k")
    mat = [
        [k if v == K else sympy.Rational(F(v).numerator, F(v).denominator) for v in row]
        for row in rows
    ]
    if any(
        row[2] == K for row in rows
    ):  # k sits in a constant: every 2x2 minor of the augmented matrix vanishes
        eq = sympy.Matrix([[mat[0][0], mat[0][2]], [mat[1][0], mat[1][2]]]).det()
    else:
        eq = sympy.Matrix([[mat[0][0], mat[0][1]], [mat[1][0], mat[1][1]]]).det()
    sols = sympy.solve(eq, k)
    if len(sols) != 1:
        raise ValueError("not one value of k")
    val = ref._rat(sols[0])
    kind = ref.kind_sympy(_fill(rows, val))
    if (need == "not_unique" and kind == "one") or (need != "not_unique" and kind != need):
        raise ValueError("condition does not give the wanted kind")
    return val


def _ratio_k(rows: list[list[Any]], need: str) -> Fraction:
    (a1, b1, c1), (a2, b2, c2) = rows
    if a2 == K:
        val = F(a1) * F(b2) / F(b1)
    elif b2 == K:
        val = F(b1) * F(a2) / F(a1)
    else:
        val = F(c1) * F(a2) / F(a1)
    kind = ref.kind_ratios(_fill(rows, val))
    if (need == "not_unique" and kind == "one") or (need != "not_unique" and kind != need):
        raise ValueError("condition does not give the wanted kind")
    return val


class KFamily(Family):
    id = ""
    need = ""

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        pb, qb, s1, s2, cc, pos = p["p"], p["q"], p["s1"], p["s2"], p["cc"], p["pos"]
        extra = p.get("d", p.get("cu", 0))
        if (
            s1 == s2
            or 0 in (pb, qb, s1, s2, cc)
            or abs(pb) == abs(qb)
            or (self.need != "infinite" and extra == 0)
        ):
            raise IllPosed("base_numbers_unusable")
        a1, b1, c1 = s1 * pb, s1 * qb, s1 * cc
        a2, b2 = s2 * pb, s2 * qb
        if self.need == "none":
            c2 = s2 * cc + extra
        elif self.need == "infinite":
            c2 = s2 * cc
        else:
            c2 = extra
        if c2 == 0:
            raise IllPosed("constant_zero")
        row2: list[Any] = [a2, b2, c2]
        k_true = {"a": a2, "b": b2, "c": c2}[pos]
        row2[{"a": 0, "b": 1, "c": 2}[pos]] = K
        rows = [[a1, b1, c1], row2]
        k_val = F(k_true)
        # condition polynomial in k: the determinant (k in a coefficient) or a proportion of constants
        if pos == "c":
            lhs = [fstr(-F(a2) * F(c1)), fstr(F(a1))]
            lead = F(a1)
        else:
            d0 = _det_at(rows, F(0))
            d1 = _det_at(rows, F(1)) - d0
            if d1 == 0:
                raise IllPosed("k_does_not_appear")
            lhs, lead = [fstr(d0), fstr(d1)], d1
        part = {"roots": [fstr(k_val)], "count": 1}
        witness = {"split": {"lead": fstr(lead), "roots": [[fstr(k_val), 1]]}}
        model = {"family": self.id, "rows": rows, "need": self.need}
        key = {**part, "value": fstr(k_val)}

        def wrap(fn: Any) -> Any:
            def run(spec: Mapping[str, Any]) -> Any:
                m = spec["model"]
                val = fn(m["rows"], m["need"])
                return {"roots": [fstr(val)], "count": 1, "value": fstr(val)}

            return run

        methods = [
            method("maths.lin2.k_ratio", "closed_form", "consistency_conditions", wrap(_ratio_k)),
            method("maths.lin2.k_minors", "sympy.solve", "", wrap(_sympy_k)),
            method("maths.lin2.k_grid", "grid_search", "", wrap(_grid_k)),
        ]
        # named slips, in priority order
        if pos == "a":
            cands = [
                ("MC.PAIR.K_RATIO_UPSIDE_DOWN", F(a1) * b1 / b2),
                ("MC.PAIR.K_WRONG_RATIO_USED", F(a1) * c2 / c1),
                ("MC.PAIR.K_ADDITIVE_INSTEAD_OF_RATIO", F(a1 + (b2 - b1))),
                ("MC.PAIR.K_SIGN_SLIP", -k_val),
                ("MC.PAIR.K_EQUAL_TO_OTHER_CONSTANT", F(a1)),
            ]
        elif pos == "b":
            cands = [
                ("MC.PAIR.K_RATIO_UPSIDE_DOWN", F(b1) * a1 / a2),
                ("MC.PAIR.K_WRONG_RATIO_USED", F(b1) * c2 / c1),
                ("MC.PAIR.K_ADDITIVE_INSTEAD_OF_RATIO", F(b1 + (a2 - a1))),
                ("MC.PAIR.K_SIGN_SLIP", -k_val),
                ("MC.PAIR.K_EQUAL_TO_OTHER_CONSTANT", F(b1)),
            ]
        else:
            cands = [
                ("MC.PAIR.K_RATIO_UPSIDE_DOWN", F(c1) * a1 / a2),
                ("MC.PAIR.K_ADDITIVE_INSTEAD_OF_RATIO", F(c1 + (a2 - a1))),
                ("MC.PAIR.K_SIGN_SLIP", -k_val),
                ("MC.PAIR.K_EQUAL_TO_OTHER_CONSTANT", F(c1)),
            ]
        wrong = [
            (mc, {"roots": [fstr(w)], "count": 1, "value": fstr(w)}, fstr(w))
            for mc, w in cands
            if nice(w)
        ]
        e1, e2 = k_text(rows[0]), k_text(rows[1])
        stem = pick(
            [
                f"For which value of k does the pair {e1} and {e2} {_WORDS[self.need][0]}?"
                if self.need != "not_unique"
                else f"The pair {e1} and {e2} has exactly one solution for every k except one value. Find that value of k.",
                f"Find k so that {e1} and {e2} {pick(_WORDS[self.need], {'p': p['p'], 's1': s1})}."
                if self.need != "not_unique"
                else f"Find the value of k for which {e1} and {e2} {_WORDS[self.need][0]}.",
            ],
            {"p": pb, "q": qb, "s": s2, "pos": pos},
        )
        cond = {
            "a": f"{a1}/k = {b1}/{b2}",
            "b": f"{a1}/{a2} = {b1}/k",
            "c": f"{a1}/{a2} = {c1}/k",
        }[pos]
        steps = [
            {
                "none": "No solution needs equal ratios of the x and y coefficients, and a different ratio for the constants.",
                "infinite": "Infinitely many solutions need all three ratios equal: the x coefficients, the y coefficients and the constants.",
                "not_unique": "A pair fails to have exactly one solution when the ratio of the x coefficients equals the ratio of the y coefficients.",
            }[self.need],
            f"Use the ratios that contain k: {cond}, so k = {fstr(k_val)}.",
            {
                "none": f"Check the constants: {c1}/{c2 if pos != 'c' else 'k'} differs from the coefficient ratio, so there really is no solution.",
                "infinite": "Check the third ratio with this value of k: it matches, so the lines coincide.",
                "not_unique": f"At k = {fstr(k_val)} the two coefficient ratios are equal, so the pair has no unique solution.",
            }[self.need],
        ]
        pool = {
            "none": [
                "Write the ratio of the x coefficients and the ratio of the y coefficients.",
                "Parallel lines have equal coefficient ratios, while the ratio of the constants differs.",
                "No solution means the lines are parallel. Compare the ratios of matching numbers.",
                "Make the ratios of the coefficients equal and use the one that contains k.",
            ],
            "infinite": [
                "Infinitely many solutions mean the two equations describe the same line.",
                "All three ratios of matching numbers must be equal.",
                "Write every ratio of matching numbers and find the one that holds k.",
                "The second equation must be proportional to the first. Use that to find k.",
            ],
            "not_unique": [
                "A pair has one solution exactly when the lines are not parallel and not identical.",
                "Find the value of k that makes the lines parallel or identical. All other values give one solution.",
                "Set the ratio of the x coefficients equal to the ratio of the y coefficients.",
                "The pair loses its single solution when the two coefficient ratios become equal.",
            ],
        }[self.need]
        hints = [
            pick(pool, p),
            "Set the right ratios equal, multiply out, and solve the small equation for k.",
            "Full method: write the ratios of matching numbers, put equal the ones the situation requires, solve for k, then check that the remaining ratio behaves as needed.",
        ]
        return make(
            tpl,
            spec={"domain": "algebra", "kind": "polynomial", "lhs": lhs, "model": model},
            key=key,
            witness=witness,
            key_text=fstr(k_val),
            wrong=wrong,
            stem=stem,
            steps=steps,
            hints=hints,
            methods=methods,
            difficulty=clamp_difficulty(0.45, a1, b1, c1, steps=3),
            role="apply",
            prediction="Is k going to be positive or negative?",
            slug_text=slug(pb, qb, s1, s2, cc, extra, pos),
            nsteps=3,
        )


def _det_at(rows: list[list[Any]], k: Fraction) -> Fraction:
    (a1, b1, _), (a2, b2, _) = _fill(rows, k)
    return a1 * b2 - a2 * b1


class KNone(KFamily):
    id = "lin_k_none"
    need = "none"


class KInfinite(KFamily):
    id = "lin_k_infinite"
    need = "infinite"


class KNotUnique(KFamily):
    id = "lin_k_unique"
    need = "not_unique"


K_FAMILIES: dict[str, Family] = {f.id: f for f in (KNone(), KInfinite(), KNotUnique())}
