# ruff: noqa: E501
"""Pair of Linear Equations (graph reading, solution type, substitution, elimination, ratios).

Original wording and original numbers. Each family picks the solution first, builds the pair from
it, and offers wrong options that come from named slips (see misconceptions_pair.py). Hints carry
no digits and no bare option-letter words: the lane lint refuses them otherwise.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import sympy

from app.factory.lanes.maths.ap import scalar
from app.factory.lanes.maths.core import Built, Family, IllPosed, clamp_difficulty, fstr, pick
from app.factory.lanes.maths.lin2_core import (
    F,
    coef_text,
    lin_text,
    make,
    method,
    nice,
    pair_rec,
    pt,
    slope_text,
    slug,
    std_zero_text,
    system_spec,
)
from app.factory.lanes.maths.reference import lin2 as ref

# ---------------------------------------------------------------- shared answer shapes


def _fmt_ask(ask: str, x: Fraction, y: Fraction) -> tuple[dict[str, Any], str]:
    """The record and the option text for the thing asked: both values, or x + y."""
    if ask == "sum":
        text = fstr(x + y)
        return pair_rec(x, y, text), text
    return pair_rec(x, y), f"x = {fstr(x)}, y = {fstr(y)}"


def _wrong_from_pairs(
    ask: str, cands: list[tuple[str, tuple[Fraction, Fraction] | None]]
) -> list[tuple[str, dict[str, Any], str]]:
    out = []
    for mc, val in cands:
        if val is None or not (nice(val[0]) and nice(val[1])):
            continue
        rec, text = _fmt_ask(ask, *val)
        out.append((mc, rec, text))
    return out


def _one_var(ask: str, x: Fraction) -> tuple[str, dict[str, Any], str]:
    if ask == "sum":
        return "MC.PAIR.ONE_VARIABLE_ONLY", {"values": {"x": fstr(x)}, "value": fstr(x)}, fstr(x)
    return "MC.PAIR.ONE_VARIABLE_ONLY", {"values": {"x": fstr(x)}, "value": f"x = {fstr(x)}"}, f"x = {fstr(x)}"


def _safe(fn: Any) -> Any:
    try:
        return fn()
    except (ZeroDivisionError, ValueError):
        return None


def _row_methods(tech: str, ask_key: str = "ask") -> list[Any]:
    """The technique under test, SymPy's solver, and an independent third formulation."""

    def mk(solver: str) -> Any:
        def run(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            x, y = ref.SOLVERS[solver](ref.eqs(m["rows"]))
            return _fmt_ask(m[ask_key], x, y)[0]

        return run

    third = {"substitution": "gauss", "elimination": "cramer", "cross_multiplication": "gauss"}[tech]
    groups = {"substitution": "substitution", "elimination": "elimination", "cross_multiplication": "cramer"}
    return [
        method(f"maths.lin2.{tech}", groups[tech], tech, mk(tech if tech != "cross_multiplication" else "cramer")),
        method("maths.lin2.sympy", "sympy.linsolve", "", mk("sympy")),
        method(f"maths.lin2.{third}", third, "", mk(third)),
    ]


# ---------------------------------------------------------------- 1. where do two lines meet (from points)


class GraphPoint(Family):
    id = "lin_graph_point"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        x, y, ma, mb, wide, first = p["x"], p["y"], p["ma"], p["mb"], p["wide"], p["first"]
        if ma == mb:
            raise IllPosed("lines_must_not_be_parallel")
        oa = (-2, 1) if not wide else (-3, 2)
        ob = (-1, 2) if not wide else (-2, 3)
        a_pts = [(x + o, y + ma * o) for o in oa]
        b_pts = [(x + o, y + mb * o) for o in ob]
        lines = [a_pts, b_pts] if first == 0 else [b_pts, a_pts]
        names = ["A", "B"] if first == 0 else ["B", "A"]
        ia, ib = y - ma * x, y - mb * x
        rows = []
        for (x1, y1), (x2, y2) in (a_pts, b_pts):
            rows.append([y2 - y1, -(x2 - x1), (y2 - y1) * x1 - (x2 - x1) * y1])
        model = {"family": self.id, "pts": [[*a_pts[0], *a_pts[1]], [*b_pts[0], *b_pts[1]]]}
        spec = system_spec(rows, model)

        def text_of(xv: Fraction, yv: Fraction) -> dict[str, Any]:
            return pair_rec(xv, yv, pt(xv, yv))

        def closed2(s: Mapping[str, Any]) -> Any:
            r = []
            for x1, y1, x2, y2 in s["model"]["pts"]:
                r.append([y2 - y1, -(x2 - x1), (y2 - y1) * x1 - (x2 - x1) * y1])
            return text_of(*ref.cramer(ref.eqs(r)))

        def param(s: Mapping[str, Any]) -> Any:
            (ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2) = s["model"]["pts"]
            t, u = sympy.symbols("t u")
            sol = sympy.linsolve(
                [ax1 + t * (ax2 - ax1) - bx1 - u * (bx2 - bx1), ay1 + t * (ay2 - ay1) - by1 - u * (by2 - by1)],
                (t, u),
            )
            if len(sol) != 1:
                raise ValueError("lines do not meet once")
            tv = next(iter(sol))[0]
            xv, yv = ax1 + tv * (ax2 - ax1), ay1 + tv * (ay2 - ay1)
            return text_of(ref._rat(xv), ref._rat(yv))

        def scan(s: Mapping[str, Any]) -> Any:
            (ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2) = (
                [F(v) for v in row] for row in s["model"]["pts"]
            )

            def on_a(xv: Fraction) -> Fraction:
                return ay1 + (ay2 - ay1) * (xv - ax1) / (ax2 - ax1)

            def on_b(xv: Fraction) -> Fraction:
                return by1 + (by2 - by1) * (xv - bx1) / (bx2 - bx1)

            return text_of(*ref.scan(lambda xv, yv: [yv - on_b(xv)], lambda xv: on_a(xv)))

        methods = [
            method("maths.lin2.lines", "closed_form", "intersection_of_lines", closed2),
            method("maths.lin2.sympy_param", "sympy.solve", "", param),
            method("maths.lin2.grid", "grid_search", "", scan),
        ]
        key = pair_rec(x, y, pt(x, y))
        wrong = [
            ("MC.PAIR.GRAPH_INTERCEPT_FOR_MEET", pair_rec(0, ia, pt(0, ia)), pt(0, ia)),
            ("MC.PAIR.GRAPH_ONE_LINE_POINT", pair_rec(*a_pts[0], pt(*a_pts[0])), pt(*a_pts[0])),
            ("MC.PAIR.GRAPH_OTHER_LINE_POINT", pair_rec(*b_pts[1], pt(*b_pts[1])), pt(*b_pts[1])),
            ("MC.PAIR.XY_SWAPPED", pair_rec(y, x, pt(y, x)), pt(y, x)),
        ]
        listing = " ".join(
            f"Line {n} passes through {pt(*q[0])} and {pt(*q[1])}." for n, q in zip(names, lines, strict=True)
        )
        stem = pick(
            [
                f"{listing} At which point do the two lines meet?",
                f"{listing} Find the point where the two lines cut each other.",
                f"{listing} Which point do both lines share?",
            ],
            {"x": x, "y": y, "ma": ma},
        )
        xs = F(ib - ia, ma - mb)
        steps = [
            f"Line A: y changes by {ma} each time x goes up by 1, so {slope_text(ma, ia)}.",
            f"Line B: y changes by {mb} each time x goes up by 1, so {slope_text(mb, ib)}.",
            f"At the meeting point both rules give the same y: {fstr(ma)}x + ({ia}) = {fstr(mb)}x + ({ib}), so x = {fstr(xs)}.",
            f"Then y = {fstr(ma)} × {fstr(xs)} + ({ia}) = {fstr(y)}. The lines meet at {pt(x, y)}.",
        ]
        hints = [
            pick(
                [
                    "Find how y changes when x goes up by one on each line.",
                    "Use the two listed points of each line to get its rule first.",
                    "Each line has its own rule linking y to x. Work these out before anything else.",
                    "Start by finding the rise for one step along x on each line.",
                ],
                p,
            ),
            "The meeting point is the one place where both rules give the same y for the same x.",
            "Full method: get the rule for each line from its points, set the two rules equal to find x, then put x into either rule to find y and check it in the other.",
        ]
        return make(
            tpl,
            spec=spec,
            key=key,
            witness={"values": key["values"]},
            key_text=pt(x, y),
            wrong=wrong,
            stem=stem,
            steps=steps,
            hints=hints,
            methods=methods,
            difficulty=clamp_difficulty(0.35, x, y, ma, mb, steps=4),
            role="apply",
            prediction="Before working it out: is the meeting point nearer the first listed points or the last ones?",
            slug_text=slug(x, y, ma, mb, wide, first),
            nsteps=4,
        )


# ---------------------------------------------------------------- 2. one, none or infinitely many


_TYPE_TEXT = {
    "one": "They meet at exactly one point.",
    "none": "They are parallel and never meet.",
    "infinite": "They are the same line.",
    "two": "They meet at exactly two points.",
}


def _determinant(pair: list[Any]) -> Fraction:
    (a1, b1, _), (a2, b2, _) = ref.eqs(pair)
    return a1 * b2 - a2 * b1


class GraphType(Family):
    id = "lin_graph_type"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        kind, a1, b1, c1, m, d = p["kind"], p["a1"], p["b1"], p["c1"], p["m"], p["d"]
        if m in (0, 1) or d == 0:
            raise IllPosed("multiplier_or_offset_unusable")
        row1 = [a1, b1, c1]
        row2 = {
            "one": [m * a1, m * b1 + d, m * c1 + d],
            "none": [m * a1, m * b1, m * c1 + d],
            "infinite": [m * a1, m * b1, m * c1],
        }[kind]
        if 0 in row2 or 0 in row1:
            raise IllPosed("zero_coefficient_hides_the_ratio_test")
        rows = [row1, row2]
        det = _determinant(rows)
        part, witness, lhs = scalar(det)
        model = {"family": self.id, "rows": rows}

        def answer(k: str) -> dict[str, Any]:
            return {**part, "value": _TYPE_TEXT[k]}

        def closed(s: Mapping[str, Any]) -> Any:
            pair = ref.eqs(s["model"]["rows"])
            dd = pair[0][0] * pair[1][1] - pair[1][0] * pair[0][1]
            return {**scalar(dd)[0], "value": _TYPE_TEXT[ref.kind_ratios(pair)]}

        def by_sympy(s: Mapping[str, Any]) -> Any:
            pair = ref.eqs(s["model"]["rows"])
            dd = ref.det2_sympy(pair[0][0], pair[0][1], pair[1][0], pair[1][1])
            return {**scalar(dd)[0], "value": _TYPE_TEXT[ref.kind_sympy(pair)]}

        def by_gauss(s: Mapping[str, Any]) -> Any:
            pair = ref.eqs(s["model"]["rows"])
            dd = ref.det2(pair[0][0], pair[0][1], pair[1][0], pair[1][1])
            return {**scalar(dd)[0], "value": _TYPE_TEXT[ref.kind_gauss(pair)]}

        methods = [
            method("maths.lin2.ratios", "closed_form", "consistency_conditions", closed),
            method("maths.lin2.rank", "sympy.rank", "", by_sympy),
            method("maths.lin2.rows", "row_reduction", "", by_gauss),
        ]
        key = answer(kind)
        wrong_map = {
            "one": [("MC.PAIR.TYPE_ONE_AS_NONE", "none"), ("MC.PAIR.TYPE_ONE_AS_INFINITE", "infinite"), ("MC.PAIR.TYPE_TWO_MEETING_POINTS", "two")],
            "none": [("MC.PAIR.TYPE_CONSTANT_RATIO_IGNORED", "infinite"), ("MC.PAIR.TYPE_RATIOS_NOT_COMPARED", "one"), ("MC.PAIR.TYPE_TWO_MEETING_POINTS", "two")],
            "infinite": [("MC.PAIR.TYPE_COINCIDENT_AS_PARALLEL", "none"), ("MC.PAIR.TYPE_RATIOS_NOT_COMPARED", "one"), ("MC.PAIR.TYPE_TWO_MEETING_POINTS", "two")],
        }[kind]
        wrong = [(mc, answer(k), _TYPE_TEXT[k]) for mc, k in wrong_map]
        e1, e2 = lin_text(*row1), lin_text(*row2)
        stem = pick(
            [
                f"Two straight lines are drawn from {e1} and {e2}. Which statement about them is true?",
                f"Look at the lines {e1} and {e2}. How do their graphs sit?",
                f"The pair {e1} and {e2} is plotted on one set of axes. Which description fits the two lines?",
            ],
            {"a1": a1, "m": m, "kind": kind},
        )
        ratios = f"{fstr(F(row1[0], row2[0]))}, {fstr(F(row1[1], row2[1]))} and {fstr(F(row1[2], row2[2]))}"
        verdict = {
            "one": "The first two ratios differ, so the lines meet at exactly one point.",
            "none": "The first two ratios match but the third differs, so the lines are parallel and never meet.",
            "infinite": "All three ratios match, so the two equations describe the same line.",
        }[kind]
        steps = [
            "Compare the ratios of matching numbers: x coefficients, y coefficients, then the constants.",
            f"Here the three ratios are {ratios}.",
            verdict,
        ]
        hints = [
            pick(
                [
                    "Write the ratio of the x coefficients and the ratio of the y coefficients.",
                    "Compare how the numbers of the first line relate to the numbers of the second.",
                    "Divide matching numbers of the two lines and look at the three results.",
                    "Two lines are decided by the ratios of their matching numbers.",
                ],
                p,
            ),
            "If the first two ratios differ the lines meet once. If they match, the third ratio decides between parallel lines and the same line.",
            "Full method: find the ratio of the x coefficients, the ratio of the y coefficients and the ratio of the constants. Different first two ratios: one meeting point. All three equal: same line. First two equal and the third different: parallel lines.",
        ]
        return make(
            tpl,
            spec={"domain": "algebra", "kind": "polynomial", "lhs": lhs, "model": model},
            key=key,
            witness=witness,
            key_text=_TYPE_TEXT[kind],
            wrong=wrong,
            stem=stem,
            steps=steps,
            hints=hints,
            methods=methods,
            difficulty=clamp_difficulty(0.25, a1, b1, steps=3),
            role="apply",
            prediction="Do you expect these lines to meet, never meet, or lie on top of each other?",
            slug_text=slug(kind, a1, b1, c1, m, d),
            nsteps=3,
        )


# ---------------------------------------------------------------- 3. substitution


def _times(coef: int, expr: str) -> str:
    sign = " - " if coef < 0 else " + "
    mag = abs(coef)
    return sign + ("" if mag == 1 else str(mag)) + f"({expr})"


class SubstForm(Family):
    id = "lin_subst_form"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        x, y, m, a, b, ask = p["x"], p["y"], p["m"], p["a"], p["b"], p["ask"]
        if a + b * m == 0 or b == 0:
            raise IllPosed("pair_has_no_unique_solution")
        n = y - m * x
        rows = [[-m, 1, n], [a, b, a * x + b * y]]
        c2 = a * x + b * y
        model = {"family": self.id, "rows": rows, "ask": ask}
        spec = system_spec(rows, model)
        key, key_text = _fmt_ask(ask, F(x), F(y))
        x_nd = _safe(lambda: F(c2 - n, a + b * m))
        cands: list[tuple[str, tuple[Fraction, Fraction] | None]] = [
            ("MC.PAIR.SUBST_NOT_DISTRIBUTED", (x_nd, m * x_nd + n) if x_nd is not None else None),
            ("MC.PAIR.SUBST_SIGN_SLIP", (F(x), F(m * x - n))),
            ("MC.PAIR.XY_SWAPPED", (F(y), F(x))),
        ]
        wrong = _wrong_from_pairs(ask, cands)
        wrong.append(_one_var(ask, F(x)))
        expr = slope_text(m, n)[4:]
        e2 = lin_text(a, b, c2)
        stem = pick(
            [
                f"Use substitution to solve {slope_text(m, n)} and {e2}."
                if ask == "pair"
                else f"Use substitution on {slope_text(m, n)} and {e2}. What is x + y?",
                f"Solve the pair {slope_text(m, n)}, {e2} by substitution."
                if ask == "pair"
                else f"For the pair {slope_text(m, n)}, {e2}, find the value of x + y using substitution.",
            ],
            {"x": x, "y": y, "m": m},
        )
        bracket = f"{coef_text(a, 'x', True)}{_times(b, expr)} = {fstr(c2)}"
        steps = [
            f"Put y = {expr} into the second equation: {bracket}.",
            f"Multiply out and collect the x terms: {lin_text(a + b * m, 0, c2 - b * n)}, so x = {fstr(x)}.",
            f"Put x = {fstr(x)} back into the first equation: y = {fstr(m)} × {fstr(x)} + ({n}) = {fstr(y)}.",
        ]
        if ask == "sum":
            steps.append(f"So x + y = {fstr(x)} + ({fstr(y)}) = {fstr(x + y)}.")
        hints = [
            pick(
                [
                    "Use the first equation to replace y in the second one.",
                    "The first equation already tells you what y equals. Put that into the other equation.",
                    "Replace y in the second equation by what the first equation says it equals.",
                    "Start by putting the expression for y into the other equation.",
                ],
                p,
            ),
            "Multiply every term inside the bracket, then solve the one-unknown equation that is left.",
            "Full method: substitute for y, multiply out the bracket, collect the x terms, solve for x, then put that value of x back into the first equation to get y.",
        ]
        return make(
            tpl,
            spec=spec,
            key=key,
            witness={"values": key["values"]},
            key_text=key_text,
            wrong=wrong,
            stem=stem,
            steps=steps,
            hints=hints,
            methods=_row_methods("substitution"),
            difficulty=clamp_difficulty(0.3, x, y, m, steps=4),
            role="procedure",
            prediction="Will x or y come out first when you substitute?",
            slug_text=slug(x, y, m, a, b, ask),
            nsteps=len(steps),
        )


class SubstGeneral(Family):
    id = "lin_subst_general"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        x, y, unit, s1, q, a, b = p["x"], p["y"], p["unit"], p["s1"], p["q"], p["a"], p["b"]
        row1 = [s1, q, s1 * x + q * y] if unit == 0 else [q, s1, q * x + s1 * y]
        row2 = [a, b, a * x + b * y]
        if row1[0] * row2[1] - row1[1] * row2[0] == 0:
            raise IllPosed("pair_has_no_unique_solution")
        rows = [row1, row2]
        model = {"family": self.id, "rows": rows, "ask": "pair"}
        spec = system_spec(rows, model)
        key, key_text = _fmt_ask("pair", F(x), F(y))
        c1 = row1[2]
        slip_isolate = [[row1[0], -row1[1], c1], row2] if unit == 0 else [[-row1[0], row1[1], c1], row2]
        # the constant of the isolated expression is dropped when it is put into the second equation
        if unit == 0:
            yd = _safe(lambda: F(row2[2]) / (b - F(a * q, s1)))
            dropped = ((c1 - q * yd) / s1, yd) if yd is not None else None
        else:
            xd = _safe(lambda: F(row2[2]) / (a - F(b * q, s1)))
            dropped = (xd, (c1 - q * xd) / s1) if xd is not None else None
        cands: list[tuple[str, tuple[Fraction, Fraction] | None]] = [
            ("MC.PAIR.SUBST_ISOLATE_SIGN", _safe(lambda: ref.cramer(ref.eqs(slip_isolate)))),
            ("MC.PAIR.SUBST_NOT_DISTRIBUTED", dropped),
            ("MC.PAIR.XY_SWAPPED", (F(y), F(x))),
        ]
        wrong = _wrong_from_pairs("pair", cands)
        wrong.append(_one_var("pair", F(x)))
        e1, e2 = lin_text(*row1), lin_text(*row2)
        stem = pick(
            [
                f"Solve by substitution: {e1} and {e2}.",
                f"Use substitution on the pair {e1}, {e2}.",
                f"Find x and y from {e1} and {e2} by substitution.",
            ],
            {"x": x, "y": y, "q": q},
        )
        var = "x" if unit == 0 else "y"
        other = "y" if unit == 0 else "x"
        oc = row1[1] if unit == 0 else row1[0]
        k0, k1 = F(c1, s1), -F(oc, s1)
        tail = coef_text(k1, other, k0 == 0)
        alone = f"{var} = {tail}" if k0 == 0 else f"{var} = {fstr(k0)}{tail}"
        steps = [
            f"Write {var} on its own using the first equation: {alone}.",
            f"Put that into the second equation and solve for {other}: {other} = {fstr(y if unit == 0 else x)}.",
            f"Use the value of {other} in the line from the first step: {var} = {fstr(x if unit == 0 else y)}.",
        ]
        hints = [
            pick(
                [
                    f"Look for the equation where {var} has the simplest coefficient, and get {var} alone from it.",
                    f"Start with the equation where {var} has the smallest coefficient and make {var} the subject.",
                    f"Write {var} alone from the first equation before you touch the second one.",
                    f"Make {var} the subject of the equation that is easiest to rearrange.",
                ],
                p,
            ),
            f"Take the other term to the opposite side with its sign reversed, then put the result in place of {var} in the second equation.",
            f"Full method: write {var} alone, substitute it into the other equation, solve for {other}, then use that value to get {var}.",
        ]
        return make(
            tpl,
            spec=spec,
            key=key,
            witness={"values": key["values"]},
            key_text=key_text,
            wrong=wrong,
            stem=stem,
            steps=steps,
            hints=hints,
            methods=_row_methods("substitution"),
            difficulty=clamp_difficulty(0.35, x, y, q, steps=5),
            role="procedure",
            prediction="Which letter is easier to get alone, and why?",
            slug_text=slug(x, y, unit, s1, q, a, b),
            nsteps=3,
        )


# ---------------------------------------------------------------- 4. elimination


def _to_xy(u: Fraction, v: Fraction, e: int) -> tuple[Fraction, Fraction]:
    """(eliminated unknown, other unknown) back to (x, y)."""
    return (u, v) if e == 0 else (v, u)


def _elim_rows(e: int, ecoefs: tuple[int, int], oc: tuple[int, int], cs: tuple[int, int]) -> list[list[int]]:
    if e == 0:
        return [[ecoefs[0], oc[0], cs[0]], [ecoefs[1], oc[1], cs[1]]]
    return [[oc[0], ecoefs[0], cs[0]], [oc[1], ecoefs[1], cs[1]]]


def _stem_pair(rows: list[list[int]], p: Mapping[str, Any]) -> str:
    e1, e2 = lin_text(*rows[0]), lin_text(*rows[1])
    return pick(
        [
            f"Solve by elimination: {e1} and {e2}.",
            f"Use elimination on the pair {e1}, {e2}.",
            f"Find x and y by elimination from {e1} and {e2}.",
        ],
        p,
    )


def _elim_hints(p: Mapping[str, Any], full: str) -> list[str]:
    return [
        pick(
            [
                "Choose one unknown and make its coefficients match in size in the two equations.",
                "Look for the unknown that is easiest to remove by adding or subtracting the equations.",
                "Decide which unknown to cancel first, and what to do to the equations to cancel it.",
                "The aim is to get one equation with only one unknown left.",
            ],
            p,
        ),
        "Add the equations when the matching terms have opposite signs and subtract them when the signs agree. Apply the operation to every term, constants included.",
        full,
    ]


def _build_elim(
    fam: str, tpl: Mapping[str, Any], p: Mapping[str, Any], rows: list[list[int]], x: int, y: int, steps: list[str],
    cands: list[tuple[str, tuple[Fraction, Fraction] | None]], full: str, base: float,
) -> Built:
    model = {"family": fam, "rows": rows, "ask": "pair"}
    key, key_text = _fmt_ask("pair", F(x), F(y))
    wrong = _wrong_from_pairs("pair", [*cands, ("MC.PAIR.XY_SWAPPED", (F(y), F(x)))])
    wrong.append(_one_var("pair", F(x)))
    return make(
        tpl,
        spec=system_spec(rows, model),
        key=key,
        witness={"values": key["values"]},
        key_text=key_text,
        wrong=wrong,
        stem=_stem_pair(rows, p),
        steps=steps,
        hints=_elim_hints(p, full),
        methods=_row_methods("elimination"),
        difficulty=clamp_difficulty(base, x, y, steps=len(steps)),
        role="procedure",
        prediction="Which unknown will you cancel first?",
        slug_text=slug(*p.values()),
        nsteps=len(steps),
    )


def _finish_u_v(rows: list[list[int]], e: int, rhs: Fraction, coefv: Fraction) -> tuple[Fraction, Fraction]:
    """From the one-unknown line coefv * v = rhs, find v, then u from the first original equation."""
    v = rhs / coefv
    r = rows[0]
    u = (F(r[2]) - F(r[1 - e]) * v) / F(r[e])
    return _to_xy(u, v, e)


class ElimDirect(Family):
    id = "lin_elim_direct"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        x, y, e, pe, sgn, q1, q2 = p["x"], p["y"], p["e"], p["pe"], p["sgn"], p["q1"], p["q2"]
        if q1 == q2 or (sgn == -1 and q1 + q2 == 0) or q1 == 0 or q2 == 0:
            raise IllPosed("other_coefficients_unusable")
        u, v = (x, y) if e == 0 else (y, x)
        cs = (pe * u + q1 * v, sgn * pe * u + q2 * v)
        rows = _elim_rows(e, (pe, sgn * pe), (q1, q2), cs)
        var, other = ("x", "y") if e == 0 else ("y", "x")
        op = "Subtract" if sgn == 1 else "Add"
        opd = "subtracting" if sgn == 1 else "adding"
        rc = cs[0] - cs[1] if sgn == 1 else cs[0] + cs[1]
        rq = q1 - q2 if sgn == 1 else q1 + q2
        steps = [
            f"The {var} terms are {fstr(pe)}{var} and {fstr(sgn * pe)}{var}, so {opd} the equations cancels {var}.",
            f"{op} the second equation from the first, every term: {lin_text(0, rq, rc, var, other)}, so {other} = {fstr(v)}."
            if sgn == 1
            else f"{op} the two equations, every term: {lin_text(0, rq, rc, var, other)}, so {other} = {fstr(v)}.",
            f"Put {other} = {fstr(v)} in the first equation to get {var} = {fstr(u)}.",
        ]
        if sgn == 1:
            cands = [
                ("MC.PAIR.ELIM_ADD_NOT_SUBTRACT", _safe(lambda: _finish_u_v(rows, e, F(cs[0] + cs[1]), F(q1 + q2)))),
                ("MC.PAIR.ELIM_SIGN_SLIP", _safe(lambda: _finish_u_v(rows, e, F(cs[0] - cs[1]), F(q1 + q2)))),
            ]
        else:
            cands = [
                ("MC.PAIR.ELIM_SUBTRACT_NOT_ADD", _safe(lambda: _finish_u_v(rows, e, F(cs[0] - cs[1]), F(q1 - q2)))),
                ("MC.PAIR.ELIM_SIGN_SLIP", _safe(lambda: _finish_u_v(rows, e, F(cs[0] - cs[1]), F(q1 + q2)))),
            ]
        return _build_elim(
            self.id, tpl, p, rows, x, y, steps, cands,
            "Full method: compare the coefficients of one unknown, add or subtract the equations, using every term, so it cancels, solve the single equation left, then put that value into one of the originals.",
            0.3,
        )


class ElimOne(Family):
    id = "lin_elim_one"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        x, y, e, pe, m, q1, q2, swap = p["x"], p["y"], p["e"], p["pe"], p["m"], p["q1"], p["q2"], p["swap"]
        if abs(m) < 2 or q1 == 0 or q2 == 0 or q2 == m * q1:
            raise IllPosed("scaled_row_would_not_cancel_cleanly")
        u, v = (x, y) if e == 0 else (y, x)
        k = abs(m)
        small = (pe, q1, pe * u + q1 * v)
        big = (m * pe, q2, m * pe * u + q2 * v)
        ordered = [big, small] if swap else [small, big]
        rows = [_elim_rows(e, (r[0], r[0]), (r[1], r[1]), (r[2], r[2]))[0] for r in ordered]
        var, other = ("x", "y") if e == 0 else ("y", "x")
        same = m > 0
        scaled = (k * pe, k * q1, k * small[2])
        rq = scaled[1] - q2 if same else scaled[1] + q2
        rc = scaled[2] - big[2] if same else scaled[2] + big[2]
        steps = [
            f"Multiply the {'first' if not swap else 'second'} equation by {k}, every term. The {var} coefficients are then {'equal' if same else 'equal in size and opposite in sign'}.",
            f"{'Subtract' if same else 'Add'} the equations: {lin_text(0, rq, rc, var, other)}, so {other} = {fstr(v)}.",
            f"Put {other} = {fstr(v)} back to find {var} = {fstr(u)}.",
        ]

        def system_with(first: list[int], second: list[int]) -> tuple[Fraction, Fraction] | None:
            row_s = _elim_rows(e, (first[0], second[0]), (first[1], second[1]), (first[2], second[2]))
            return _safe(lambda: ref.cramer(ref.eqs(row_s)))

        big_row = [big[0], q2, big[2]]
        cands = [
            ("MC.PAIR.ELIM_SCALE_PARTIAL", system_with([scaled[0], scaled[1], small[2]], big_row)),
            ("MC.PAIR.ELIM_SCALE_PARTIAL", system_with([scaled[0], q1, scaled[2]], big_row)),
            ("MC.PAIR.ELIM_DIVIDED_ONE_TERM", system_with([pe, q1, small[2]], [pe, q2, F(big[2], m)])),
            (
                "MC.PAIR.ELIM_ADD_NOT_SUBTRACT" if same else "MC.PAIR.ELIM_SUBTRACT_NOT_ADD",
                _safe(lambda: _finish_u_v(rows, e, F(scaled[2] + big[2] if same else scaled[2] - big[2]), F(scaled[1] + q2 if same else scaled[1] - q2))),
            ),
            ("MC.PAIR.ELIM_SIGN_SLIP", _safe(lambda: _finish_u_v(rows, e, F(scaled[2] + big[2] if same else scaled[2] - big[2]), F(rq)))),
        ]
        return _build_elim(
            self.id, tpl, p, rows, x, y, steps, cands,
            "Full method: multiply the equation with the smaller coefficient by the right number, using every term, so the coefficients of one unknown match, add or subtract to cancel it, solve, then find the other unknown.",
            0.4,
        )


class ElimBoth(Family):
    id = "lin_elim_both"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        x, y, e, a1, a2, q1, q2 = p["x"], p["y"], p["e"], p["a1"], p["a2"], p["q1"], p["q2"]
        if abs(a1) == abs(a2) or a1 % a2 == 0 or a2 % a1 == 0 or q1 == 0 or q2 == 0:
            raise IllPosed("coefficients_not_suited_to_scaling_both")
        if a2 * q1 - a1 * q2 == 0:
            raise IllPosed("pair_has_no_unique_solution")
        u, v = (x, y) if e == 0 else (y, x)
        cs = (a1 * u + q1 * v, a2 * u + q2 * v)
        rows = _elim_rows(e, (a1, a2), (q1, q2), cs)
        var, other = ("x", "y") if e == 0 else ("y", "x")
        rq = a2 * q1 - a1 * q2
        rc = a2 * cs[0] - a1 * cs[1]
        steps = [
            f"Multiply the first equation by {a2} and the second by {a1}, every term, so both {var} coefficients become {fstr(a1 * a2)}.",
            f"Subtract the second new equation from the first: {lin_text(0, rq, rc, var, other)}, so {other} = {fstr(v)}.",
            f"Put {other} = {fstr(v)} in the first original equation to get {var} = {fstr(u)}.",
        ]
        partial = _elim_rows(e, (a1 * a2, a1 * a2), (a2 * q1, a1 * q2), (cs[0], a1 * cs[1]))
        cands = [
            ("MC.PAIR.ELIM_SCALE_PARTIAL", _safe(lambda: ref.cramer(ref.eqs(partial)))),
            ("MC.PAIR.ELIM_ADD_NOT_SUBTRACT", _safe(lambda: _finish_u_v(rows, e, F(a2 * cs[0] + a1 * cs[1]), F(a2 * q1 + a1 * q2)))),
            ("MC.PAIR.ELIM_SIGN_SLIP", _safe(lambda: _finish_u_v(rows, e, F(a2 * cs[0] + a1 * cs[1]), F(rq)))),
        ]
        return _build_elim(
            self.id, tpl, p, rows, x, y, steps, cands,
            "Full method: pick an unknown, multiply each equation by the other equation's coefficient of it, using every term, so they match, subtract to cancel it, solve for the other unknown, then substitute back.",
            0.5,
        )


# ---------------------------------------------------------------- 5. cross-multiplication


def _cross_numbers(a1: int, b1: int, c1: int, a2: int, b2: int, c2: int) -> tuple[int, int, int]:
    """Denominators of x/p = y/q = 1/r for a x + b y + c = 0."""
    return b1 * c2 - b2 * c1, c1 * a2 - c2 * a1, a1 * b2 - a2 * b1


class CrossSolve(Family):
    id = "lin_cross_solve"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        x, y, a1, b1, a2, b2 = p["x"], p["y"], p["a1"], p["b1"], p["a2"], p["b2"]
        r = a1 * b2 - a2 * b1
        if r == 0:
            raise IllPosed("pair_has_no_unique_solution")
        c1, c2 = -(a1 * x + b1 * y), -(a2 * x + b2 * y)
        if 0 in (c1, c2):
            raise IllPosed("constant_term_zero")
        rows = [[a1, b1, -c1], [a2, b2, -c2]]
        model = {"family": self.id, "rows": rows, "ask": "pair"}
        pn, qn, rn = _cross_numbers(a1, b1, c1, a2, b2, c2)
        key, key_text = _fmt_ask("pair", F(x), F(y))
        denom_added = a1 * b2 + a2 * b1
        cands = [
            ("MC.PAIR.CROSS_CONSTANT_SIGN", (F(-x), F(-y))),
            ("MC.PAIR.CROSS_NUMERATOR_ORDER", (F(x), F(-y))),
            ("MC.PAIR.CROSS_DENOM_ADDED", _safe(lambda: (F(pn, denom_added), F(qn, denom_added)))),
            ("MC.PAIR.XY_SWAPPED", (F(y), F(x))),
        ]
        wrong = _wrong_from_pairs("pair", cands)
        wrong.append(_one_var("pair", F(x)))
        e1, e2 = std_zero_text(a1, b1, c1), std_zero_text(a2, b2, c2)
        stem = pick(
            [
                f"Solve the pair {e1} and {e2} with the formula x/p = y/q = 1/r.",
                f"Use the ratio formula to solve {e1} and {e2}.",
                f"Find x and y from {e1} and {e2} using the method of ratios of products.",
            ],
            {"x": x, "y": y, "a1": a1},
        )
        steps = [
            f"Read off the numbers: a1 = {a1}, b1 = {b1}, c1 = {c1}, a2 = {a2}, b2 = {b2}, c2 = {c2}.",
            f"Use x/(b1c2 - b2c1) = y/(c1a2 - c2a1) = 1/(a1b2 - a2b1): x/({pn}) = y/({qn}) = 1/({rn}).",
            f"So x = {pn}/{rn} = {fstr(x)} and y = {qn}/{rn} = {fstr(y)}.",
        ]
        hints = [
            pick(
                [
                    "First check that each equation is written with the constant on the left, equal to zero.",
                    "Read off the three numbers of each equation, keeping their signs.",
                    "The formula needs the coefficients and the constant term of each equation, with signs.",
                    "Match each equation to the standard form with zero on the right before using the formula.",
                ],
                p,
            ),
            "Each denominator is the difference of two products. Keep the order of the subtraction exactly as in the formula.",
            "Full method: write both equations as ax + by + c = 0, build the three differences of products for x, y and 1, then divide to get x and y.",
        ]
        methods = _row_methods("cross_multiplication")
        return make(
            tpl,
            spec=system_spec(rows, model),
            key=key,
            witness={"values": key["values"]},
            key_text=key_text,
            wrong=wrong,
            stem=stem,
            steps=steps,
            hints=hints,
            methods=methods,
            difficulty=clamp_difficulty(0.45, x, y, a1, b2, steps=4),
            role="procedure",
            prediction="Which of the three differences of products will be the denominator of the last ratio?",
            slug_text=slug(x, y, a1, b1, a2, b2),
            nsteps=3,
        )


_PART = {"p": "x", "q": "y", "r": "1"}


class CrossSetup(Family):
    id = "lin_cross_setup"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        which, a1, b1, c1, a2, b2, c2 = p["which"], p["a1"], p["b1"], p["c1"], p["a2"], p["b2"], p["c2"]
        if a1 * b2 - a2 * b1 == 0 or 0 in (c1, c2):
            raise IllPosed("pair_has_no_unique_solution")
        pn, qn, rn = _cross_numbers(a1, b1, c1, a2, b2, c2)
        target = {"p": pn, "q": qn, "r": rn}[which]
        part, witness, lhs = scalar(F(target))
        model = {"family": self.id, "w": which, "v": [a1, b1, c1, a2, b2, c2]}

        def ans(val: Any) -> dict[str, Any]:
            return {**part, "roots": [fstr(F(val))], "value": fstr(F(val))}

        def closed(s: Mapping[str, Any]) -> Any:
            A1, B1, C1, A2, B2, C2 = s["model"]["v"]
            return ans({"p": B1 * C2 - B2 * C1, "q": C1 * A2 - C2 * A1, "r": A1 * B2 - A2 * B1}[s["model"]["w"]])

        def by_sympy(s: Mapping[str, Any]) -> Any:
            A1, B1, C1, A2, B2, C2 = (sympy.Integer(v) for v in s["model"]["v"])
            mats = {
                "p": sympy.Matrix([[B1, C1], [B2, C2]]),
                "q": sympy.Matrix([[C1, A1], [C2, A2]]),
                "r": sympy.Matrix([[A1, B1], [A2, B2]]),
            }
            return ans(ref._rat(mats[s["model"]["w"]].det()))

        def by_rows(s: Mapping[str, Any]) -> Any:
            A1, B1, C1, A2, B2, C2 = (F(v) for v in s["model"]["v"])
            mats = {"p": (B1, C1, B2, C2), "q": (C1, A1, C2, A2), "r": (A1, B1, A2, B2)}
            return ans(ref.det2(*mats[s["model"]["w"]]))

        methods = [
            method("maths.lin2.products", "closed_form", "cross_multiplication", closed),
            method("maths.lin2.det_sympy", "sympy.det", "", by_sympy),
            method("maths.lin2.det_rows", "row_reduction", "", by_rows),
        ]
        alt = {"p": (b1 * c1 - b2 * c2), "q": (c1 * a1 - c2 * a2), "r": (a1 * b1 - a2 * b2)}[which]
        added = {"p": b1 * c2 + b2 * c1, "q": c1 * a2 + c2 * a1, "r": a1 * b2 + a2 * b1}[which]
        other = {"p": qn, "q": pn, "r": pn}[which]
        wrong = [
            ("MC.PAIR.CROSS_NUMERATOR_ORDER", ans(-target), fstr(-target)),
            ("MC.PAIR.CROSS_DENOM_ADDED", ans(added), fstr(added)),
            ("MC.PAIR.CROSS_PAIRING_SLIP", ans(alt), fstr(alt)),
            ("MC.PAIR.XY_SWAPPED", ans(other), fstr(other)),
        ]
        e1, e2 = std_zero_text(a1, b1, c1), std_zero_text(a2, b2, c2)
        stem = pick(
            [
                f"The pair {e1} and {e2} is solved with x/p = y/q = 1/r. Find the value of {which}.",
                f"For {e1} and {e2}, the ratio formula is written x/p = y/q = 1/r. Find the value of {which}.",
            ],
            {"w": which, "a1": a1, "c1": c1},
        )
        formula = {
            "p": f"p = b1c2 - b2c1 = ({b1})({c2}) - ({b2})({c1}) = {pn}",
            "q": f"q = c1a2 - c2a1 = ({c1})({a2}) - ({c2})({a1}) = {qn}",
            "r": f"r = a1b2 - a2b1 = ({a1})({b2}) - ({a2})({b1}) = {rn}",
        }[which]
        steps = [
            f"Read off a1 = {a1}, b1 = {b1}, c1 = {c1}, a2 = {a2}, b2 = {b2}, c2 = {c2}.",
            f"Use the matching difference of products: {formula}.",
        ]
        hints = [
            pick(
                [
                    "Write each equation with zero on the right and read the numbers with their signs.",
                    "Each denominator in the formula is made from two products of the coefficients.",
                    "Pick out the coefficients you need and keep every sign.",
                    "Look at which letters sit under x, under y and under the final ratio in the formula.",
                ],
                p,
            ),
            "Subtract the products in the order the formula gives. Reversing the order reverses the sign of the answer.",
            "Full method: identify the coefficients and constants of both equations, then evaluate the wanted difference of products with great care over signs.",
        ]
        return make(
            tpl,
            spec={"domain": "algebra", "kind": "polynomial", "lhs": lhs, "model": model},
            key=ans(target),
            witness=witness,
            key_text=fstr(target),
            wrong=wrong,
            stem=stem,
            steps=steps,
            hints=hints,
            methods=methods,
            difficulty=clamp_difficulty(0.3, a1, b1, c1, steps=2),
            role="recall",
            prediction="Will the number come out positive or negative?",
            slug_text=slug(which, a1, b1, c1, a2, b2, c2),
            nsteps=2,
        )


LIN2_FAMILIES: dict[str, Family] = {
    f.id: f
    for f in (
        GraphPoint(),
        GraphType(),
        SubstForm(),
        SubstGeneral(),
        ElimDirect(),
        ElimOne(),
        ElimBoth(),
        CrossSolve(),
        CrossSetup(),
    )
}
