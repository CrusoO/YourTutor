# ruff: noqa: E501
"""Continuity, derivatives, applications of derivatives, integrals, areas, differential equations."""

from __future__ import annotations

import math
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import sympy

from app.factory.lanes.maths_c12 import kit
from app.factory.lanes.maths_c12.core import (
    Built,
    F,
    IllPosed,
    case,
    fr,
    hints3,
    isqrt_exact,
    model,
    poly_text,
    sup,
)  # fmt: skip
from app.factory.lanes.maths_c12.m_rf_itf import slug

CH = "cbse.12.maths."
CONT, AOD = CH + "continuity_differentiability", CH + "applications_derivatives"
INT, AAI, DE = CH + "integrals", CH + "applications_integrals", CH + "differential_equations"
PRE_DIFF = "MATH.C12.PRE.DIFFERENTIATE_POWERS"
PRE_INT = "MATH.C12.PRE.INTEGRATE_POWERS"
X = sympy.Symbol("x")


def lin(a: Any, b: Any) -> str:
    return poly_text([b, a])


def powtxt(base: str, n: int) -> str:
    return f"({base}){sup(n)}" if n >= 0 else f"1/({base}){sup(-n)}"


# ================================================================ CONT.FIND_K


def _cont_hand(md: Mapping[str, Any]) -> Fraction:
    c = F(md["c"])
    if md["form"] == "piecewise":
        return (md["a"] * c + md["b"]) / (c * c)
    return 2 * c if md["form"] == "square" else 3 * c * c


def _cont_sympy(md: Mapping[str, Any]) -> Fraction:
    c = sympy.Integer(md["c"])
    k = sympy.Symbol("k")
    if md["form"] == "piecewise":
        left = sympy.limit(md["a"] * X + md["b"], X, c, "-")
        sol = sympy.solve(sympy.Eq(left, k * c**2), k)
        return kit.unsp(sol[0])
    num = X**2 - c**2 if md["form"] == "square" else X**3 - c**3
    return kit.unsp(sympy.limit(num / (X - c), X, c))


def _cont_extrapolate(md: Mapping[str, Any]) -> Fraction:
    """Exact Fractions: the quotient is a polynomial in h, so extrapolate it to h = 0."""
    c = F(md["c"])
    if md["form"] == "piecewise":
        return (md["a"] * c + md["b"]) / (c * c)
    num = (lambda x: x**2 - c**2) if md["form"] == "square" else (lambda x: x**3 - c**3)
    pts = [(F(h), num(c + h) / F(h)) for h in (1, 2, 3, 4)]
    total = F(0)
    for i, (hi, yi) in enumerate(pts):  # Lagrange value at h = 0
        term = yi
        for j, (hj, _) in enumerate(pts):
            if i != j:
                term *= (0 - hj) / (hi - hj)
        total += term
    return total


@model(
    "CONT.FIND_K", chapter=CONT, title="Find the constant that makes a function continuous at a point",
    prereq=[PRE_DIFF], marks=2, technique="equate_limits",
    box={"form": {"choices": ["piecewise", "square", "cube"]}, "c": {"choices": [-2, -1, 1, 2, 3]},
         "a": {"choices": [1, 2, -1, 3]}, "b": {"choices": [-3, -1, 2, 4]}},
)  # fmt: skip
def cont_find_k(p: Mapping[str, Any]) -> Built:
    form, c, a, b = str(p["form"]), int(p["c"]), int(p["a"]), int(p["b"])
    if form != "piecewise" and (a, b) != (1, -3):
        raise IllPosed("unused_parameters")
    md = {"form": form, "c": c, "a": a, "b": b}
    key = _cont_hand(md)
    if form == "piecewise":
        if (a * c + b) == 0:
            raise IllPosed("key_is_zero")
        stem = f"The function f is given by x → {lin(a, b)} for x < {c}, and x → kx² for x ≥ {c}. Find the value of k that makes f continuous at x = {c}."
        left = F(a * c + b)
        wrong = [
            ("MC.C12.CONT.RIGHT_PIECE_NOT_SQUARED", left / c),
            ("MC.C12.CONT.LEFT_VALUE_USED_AS_K", left),
            ("MC.C12.CONT.EQUATION_SOLVED_WITH_SIGN_SLIP", -left / (c * c)),
            ("MC.C12.CONT.MIXED_ENDPOINTS", F(a * c - b) / (c * c)),
        ]
        steps = [
            f"Continuity at x = {c} needs the left limit to equal the value on the right.",
            f"The left limit is {lin(a, b).replace('x', str(c))} = {left}.",
            f"Set {left} = k × {c * c} and solve: k = {fr(key)}.",
        ]
    else:
        n = 2 if form == "square" else 3
        stem = f"The function f is given by x → (x{sup(n)} - {c**n}) / (x - {c}) for x ≠ {c}, and f({c}) = k. Find the value of k that makes f continuous at x = {c}."
        base = F(n) * c ** (n - 1)
        wrong = [
            ("MC.C12.CONT.LIMIT_AS_VALUE_OF_NUMERATOR", F(c**n)),
            ("MC.C12.CONT.POWER_NOT_REDUCED", F(n) * c**n),
            ("MC.C12.CONT.DIVIDED_BY_ZERO_ACCEPTED", F(0)),
            ("MC.C12.CONT.DERIVATIVE_FACTOR_FORGOTTEN", F(c ** (n - 1))),
        ]
        steps = [
            "Factor the top and cancel x - c, which is allowed because x is not equal to c in the limit.",
            f"The limit is {fr(base)}.",
            f"Continuity needs k to equal the limit, so k = {fr(key)}.",
        ]
    return case(
        fam="CONT.FIND_K", md=md, names=["k"], value=key, stem=stem, steps=steps,
        hints=hints3(p, ["What must be true of the limit and the value at the point?", "Work out the limit coming from the formula that is not at the point.", "Identify which formula gives the limit and which gives the value."],
                     "Find the limit as x approaches the point from the formula near it, simplify first if the quotient looks like zero over zero, then set it equal to the value.",
                     "Full method: compute the limit near the point after any cancelling, write the value of the function at the point, equate them and solve for k."),
        wrong=wrong, base=0.35, role="apply", prediction="Which two quantities must be equal for continuity?",
        slug=slug(form, c, a, b), nsteps=3, mags=[c],
        methods=[("c12.cont.hand", "closed_form", "equate_limits", _cont_hand),
                 ("c12.cont.sympy", "sympy.limit", "", _cont_sympy),
                 ("c12.cont.extrapolate", "exact_extrapolation", "", _cont_extrapolate)],
    )  # fmt: skip


# ================================================================ DIFF.POLY_AT


class Dual:
    """Forward-mode automatic differentiation over exact fractions."""

    def __init__(self, v: Fraction, d: Fraction = F(0)) -> None:
        self.v, self.d = F(v), F(d)

    def _c(self, o: Any) -> Dual:
        return o if isinstance(o, Dual) else Dual(F(o))

    def __add__(self, o: Any) -> Dual:
        o = self._c(o)
        return Dual(self.v + o.v, self.d + o.d)

    __radd__ = __add__

    def __mul__(self, o: Any) -> Dual:
        o = self._c(o)
        return Dual(self.v * o.v, self.v * o.d + self.d * o.v)

    __rmul__ = __mul__

    def __truediv__(self, o: Any) -> Dual:
        o = self._c(o)
        return Dual(self.v / o.v, (self.d * o.v - self.v * o.d) / (o.v * o.v))

    def power(self, n: int) -> Dual:
        out = Dual(F(1))
        for _ in range(abs(n)):
            out = out * self
        return out if n >= 0 else Dual(F(1)) / out


def _f_dual(md: Mapping[str, Any]) -> Fraction:
    x = Dual(F(md["t"]), F(1))
    a, b, c, d, n = (md[k] for k in ("a", "b", "c", "d", "n"))
    u, v = x * a + b, x * c + d
    out = {
        "chain": lambda: u.power(n),
        "product": lambda: u.power(n) * v,
        "quotient": lambda: u / v,
    }[md["form"]]()
    return out.d


def _f_expr(md: Mapping[str, Any]) -> sympy.Expr:
    a, b, c, d, n = (md[k] for k in ("a", "b", "c", "d", "n"))
    u, v = a * X + b, c * X + d
    return {"chain": u**n, "product": u**n * v, "quotient": u / v}[md["form"]]


def _f_sympy(md: Mapping[str, Any]) -> Fraction:
    return kit.unsp(sympy.diff(_f_expr(md), X).subs(X, md["t"]))


def _f_float(md: Mapping[str, Any]) -> Fraction:
    a, b, c, d, n = (md[k] for k in ("a", "b", "c", "d", "n"))

    def f(x: float) -> float:
        u, v = a * x + b, c * x + d
        return {"chain": u**n, "product": u**n * v, "quotient": u / v if v else math.nan}[
            md["form"]
        ]

    t, h = float(md["t"]), 1e-3
    val = (8 * (f(t + h) - f(t - h)) - (f(t + 2 * h) - f(t - 2 * h))) / (12 * h)
    return kit.to_frac(val, 3000, 1e-6)


@model(
    "DIFF.POLY_AT", chapter=CONT, title="Differentiate a power, product or quotient and evaluate at a point",
    prereq=[PRE_DIFF], marks=3, technique="differentiation_rules",
    box={"form": {"choices": ["chain", "product", "quotient"]}, "a": {"choices": [1, 2, -1]}, "b": {"choices": [1, -2]},
         "c": {"choices": [1, -1]}, "d": {"choices": [2, 3]}, "n": {"choices": [2, 3, -1]}, "t": {"choices": [0, 1, 2]}},
)  # fmt: skip
def diff_poly_at(p: Mapping[str, Any]) -> Built:
    form, a, b, c, d, n, t = (p[k] for k in ("form", "a", "b", "c", "d", "n", "t"))
    if form == "chain" and (c, d) != (1, 2):
        raise IllPosed("unused_parameters")
    if form == "quotient" and n != 2:
        raise IllPosed("unused_parameters")
    u, v = F(a * t + b), F(c * t + d)
    if (form == "quotient" or (form == "chain" and n < 0)) and (
        v if form == "quotient" else u
    ) == 0:
        raise IllPosed("undefined_at_the_point")
    if form == "product" and n < 0:
        raise IllPosed("negative_power_with_product_not_used")
    md = {"form": form, "a": a, "b": b, "c": c, "d": d, "n": n, "t": t}
    key = _f_dual(md)
    ut, vt = lin(a, b), lin(c, d)
    if form == "chain":
        fx = powtxt(ut, n)
        true_ = n * a * u ** (n - 1)
        wrong = [
            ("MC.C12.DIFF.CHAIN_FACTOR_FORGOTTEN", n * u ** (n - 1)),
            ("MC.C12.DIFF.POWER_NOT_REDUCED", n * a * u**n),
            ("MC.C12.DIFF.ONLY_INNER_DERIVATIVE", F(a)),
            ("MC.C12.DIFF.EXPONENT_RAISED_INSTEAD", (n + 1) * a * u**n),
        ]
    elif form == "product":
        fx = f"{powtxt(ut, n)} ({vt})"
        true_ = n * a * u ** (n - 1) * v + c * u**n
        wrong = [
            ("MC.C12.DIFF.PRODUCT_AS_PRODUCT_OF_DERIVATIVES", n * a * u ** (n - 1) * c),
            ("MC.C12.DIFF.FIRST_TERM_ONLY", n * a * u ** (n - 1) * v),
            ("MC.C12.DIFF.CHAIN_FACTOR_FORGOTTEN", n * u ** (n - 1) * v + c * u**n),
            ("MC.C12.DIFF.SECOND_TERM_ONLY", c * u**n),
        ]
    else:
        fx = f"({ut}) / ({vt})"
        true_ = (a * v - c * u) / (v * v)
        wrong = [
            ("MC.C12.DIFF.QUOTIENT_ORDER_SWAPPED", (c * u - a * v) / (v * v)),
            ("MC.C12.DIFF.DENOMINATOR_NOT_SQUARED", (a * v - c * u) / v),
            ("MC.C12.DIFF.QUOTIENT_AS_QUOTIENT_OF_DERIVATIVES", F(a, c)),
            ("MC.C12.DIFF.PRODUCT_RULE_USED_FOR_QUOTIENT", (a * v + c * u) / (v * v)),
        ]
    if true_ != key:
        raise IllPosed("hand_formula_disagrees")
    return case(
        fam="DIFF.POLY_AT", md=md, names=["slope"], value=key,
        stem=f"Let y = {fx}. Find the value of dy/dx at x = {t}.",
        steps=["Pick the rule that fits the shape of the function: chain rule for a power of an expression, product rule for two factors, quotient rule for a fraction.", f"Differentiate with that rule, then put x = {t} into the result.", f"The value is {fr(key)}."],
        hints=hints3(p, ["Which differentiation rule matches the shape of this function?", "Differentiate first, substitute second.", "Name the rule, then name the pieces it needs."],
                     "Write down the rule you need, find the derivative of each piece, assemble the derivative, and only then put in the number.",
                     "Full method: choose the rule, differentiate each part and do not forget the derivative of the inside of any bracket, combine, substitute the value, and simplify the fraction."),
        wrong=wrong, base=0.45, role="apply", prediction="Will the slope at this point be positive, zero or negative?",
        slug=slug(form, a, b, c, d, n, t), nsteps=4,
        methods=[("c12.diff.dual", "automatic_differentiation", "differentiation_rules", _f_dual),
                 ("c12.diff.sympy", "sympy.symbolic", "", _f_sympy),
                 ("c12.diff.float", "numeric_limit", "", _f_float)],
    )  # fmt: skip


# ================================================================ DIFF.IMPLICIT_AT


def _imp_hand(md: Mapping[str, Any]) -> Fraction:
    A, B, C, x, y = (F(md[k]) for k in ("A", "B", "C", "x0", "y0"))
    return -(2 * A * x + B * y) / (B * x + 2 * C * y)


def _imp_sympy(md: Mapping[str, Any]) -> Fraction:
    y = sympy.Function("y")
    eq = md["A"] * X**2 + md["B"] * X * y(X) + md["C"] * y(X) ** 2 - md["K"]
    slope = sympy.solve(sympy.diff(eq, X), y(X).diff(X))[0]
    return kit.unsp(slope.subs(y(X), md["y0"]).subs(X, md["x0"]))


def _imp_newton(md: Mapping[str, Any]) -> Fraction:
    A, B, C, K = (float(md[k]) for k in ("A", "B", "C", "K"))
    x0, y0 = float(md["x0"]), float(md["y0"])

    def solve_y(x: float) -> float:
        y = y0
        for _ in range(60):
            fy = A * x * x + B * x * y + C * y * y - K
            dy = B * x + 2 * C * y
            y -= fy / dy
        return y

    h = 1e-3
    val = (
        8 * (solve_y(x0 + h) - solve_y(x0 - h)) - (solve_y(x0 + 2 * h) - solve_y(x0 - 2 * h))
    ) / (12 * h)
    return kit.to_frac(val, 2000, 1e-6)


@model(
    "DIFF.IMPLICIT_AT", chapter=CONT, title="Find dy/dx at a point of a curve given implicitly",
    prereq=[PRE_DIFF], marks=3, technique="implicit_differentiation",
    box={"A": {"choices": [1, 2, 3]}, "B": {"choices": [0, 1, -1, 2]}, "C": {"choices": [1, 2, -1]},
         "x0": {"choices": [-2, -1, 1, 2]}, "y0": {"choices": [-1, 1, 2]}},
)  # fmt: skip
def diff_implicit(p: Mapping[str, Any]) -> Built:
    A, B, C, x0, y0 = (int(p[k]) for k in ("A", "B", "C", "x0", "y0"))
    den = B * x0 + 2 * C * y0
    if den == 0:
        raise IllPosed("vertical_tangent")
    K = A * x0 * x0 + B * x0 * y0 + C * y0 * y0
    md = {"A": A, "B": B, "C": C, "K": K, "x0": x0, "y0": y0}
    key = _imp_hand(md)
    if key == 0:
        raise IllPosed("zero_slope")
    lhs = poly_text([0, 0, A], "x")
    terms = [f"{A}x²" if A != 1 else "x²"]
    if B:
        terms.append(("+ " if B > 0 else "- ") + ("" if abs(B) == 1 else str(abs(B))) + "xy")
    terms.append(("+ " if C > 0 else "- ") + ("" if abs(C) == 1 else str(abs(C))) + "y²")
    curve = " ".join(terms)
    del lhs
    fx, fy = 2 * A * x0 + B * y0, den
    wrong = [
        ("MC.C12.DIFF.IMPLICIT_SIGN_DROPPED", F(fx, fy)),
        ("MC.C12.DIFF.IMPLICIT_RATIO_INVERTED", F(-fy, fx) if fx else key + 1),
        ("MC.C12.DIFF.MIXED_TERM_DERIVATIVE_LOST", F(-(2 * A * x0), fy)),
        ("MC.C12.DIFF.Y_TREATED_AS_CONSTANT", F(-fx, 2 * C * y0) if C * y0 else key + 2),
    ]
    return case(
        fam="DIFF.IMPLICIT_AT", md=md, names=["slope"], value=key,
        stem=f"The curve {curve} = {K} passes through the point ({x0}, {y0}). Find dy/dx at that point.",
        steps=["Differentiate both sides with respect to x, treating y as a function of x, so each y term brings a factor dy/dx and xy needs the product rule.", f"Collect the dy/dx terms and solve: dy/dx = -(2·{A}x + {B}y) / ({B}x + 2·{C}y).", f"At the point the value is {fr(key)}."],
        hints=hints3(p, ["Which variable depends on which? Decide before differentiating.", "Every term with y needs the chain rule.", "The mixed term needs the product rule."],
                     "Differentiate both sides with respect to x, gather the dy/dx terms on one side, factor, and divide.",
                     "Full method: differentiate term by term (chain rule on y, product rule on the mixed term), collect the dy/dx terms, solve for dy/dx, then substitute the point."),
        wrong=wrong, base=0.5, role="apply", prediction="Can you find dy/dx without solving the curve for y first?",
        slug=slug(A, B, C, x0, y0), nsteps=5,
        methods=[("c12.imp.partials", "closed_form", "implicit_differentiation", _imp_hand),
                 ("c12.imp.sympy", "sympy.symbolic", "", _imp_sympy),
                 ("c12.imp.newton", "numeric_limit", "", _imp_newton)],
    )  # fmt: skip


# ================================================================ AOD.TANGENT_NORMAL


def _poly(md: Mapping[str, Any]) -> list[Fraction]:
    return [F(x) for x in md["coef"]]


def _tn_value(slope: Fraction, f0: Fraction, t: Fraction, kind: str) -> Fraction:
    if kind == "intercept":
        return f0 - slope * t
    if kind == "normal_slope":
        return -1 / slope
    return t - f0 / slope  # x-intercept of the tangent


def _tn_hand(md: Mapping[str, Any]) -> Fraction:
    c, t = _poly(md), F(md["t"])
    return _tn_value(kit.pval(kit.pder(c), t), kit.pval(c, t), t, md["kind"])


def _tn_sympy(md: Mapping[str, Any]) -> Fraction:
    expr = kit.sym_poly(_poly(md), X)
    t = sympy.Integer(md["t"])
    return _tn_value(
        kit.unsp(sympy.diff(expr, X).subs(X, t)), kit.unsp(expr.subs(X, t)), F(md["t"]), md["kind"]
    )


def _tn_secant(md: Mapping[str, Any]) -> Fraction:
    c, t = _poly(md), F(md["t"])
    pts = [(F(h), (kit.pval(c, t + h) - kit.pval(c, t)) / h) for h in (1, 2, 3, 4)]
    slope = F(0)
    for i, (hi, yi) in enumerate(pts):  # secant slopes are a polynomial in h: extrapolate to h = 0
        term = yi
        for j, (hj, _) in enumerate(pts):
            if i != j:
                term *= (0 - hj) / (hi - hj)
        slope += term
    return _tn_value(slope, kit.pval(c, t), t, md["kind"])


@model(
    "AOD.TANGENT_NORMAL", chapter=AOD, title="Use the slope of a tangent to find a tangent or normal property",
    prereq=[PRE_DIFF], marks=3, technique="derivative_as_slope",
    box={"deg": {"choices": [2, 3]}, "seed": {"min": 0, "max": 14}, "t": {"choices": [-1, 0, 1, 2]},
         "kind": {"choices": ["intercept", "normal_slope", "x_intercept"]}},
)  # fmt: skip
def tangent_normal(p: Mapping[str, Any]) -> Built:
    deg, seed, t, kind = int(p["deg"]), int(p["seed"]), int(p["t"]), str(p["kind"])
    cs = kit.lcg(seed + 31 * deg, deg + 1, -3, 3)
    if cs[-1] == 0:
        raise IllPosed("degree_drops")
    c = [F(x) for x in cs]
    md = {"coef": [fr(x) for x in c], "t": t, "kind": kind}
    slope, f0 = kit.pval(kit.pder(c), F(t)), kit.pval(c, F(t))
    if slope == 0:
        raise IllPosed("horizontal_tangent")
    key = _tn_hand(md)
    ask = {
        "intercept": "the y-intercept of the tangent to the curve at the point with x = {t}",
        "normal_slope": "the slope of the normal to the curve at the point with x = {t}",
        "x_intercept": "the x-intercept of the tangent to the curve at the point with x = {t}",
    }[kind].format(t=t)
    wrong = {
        "intercept": [
            ("MC.C12.AOD.SLOPE_REPORTED_AS_INTERCEPT", slope),
            ("MC.C12.AOD.POINT_VALUE_REPORTED", f0),
            ("MC.C12.AOD.INTERCEPT_SIGN_SLIP", f0 + slope * t),
            ("MC.C12.AOD.FUNCTION_VALUE_AT_ZERO", c[0]),
        ],
        "normal_slope": [
            ("MC.C12.AOD.NORMAL_SLOPE_NOT_NEGATED", 1 / slope),
            ("MC.C12.AOD.NORMAL_AS_TANGENT", slope),
            ("MC.C12.AOD.NEGATIVE_NOT_RECIPROCAL", -slope),
            ("MC.C12.AOD.POINT_VALUE_REPORTED", f0),
        ],
        "x_intercept": [
            (
                "MC.C12.AOD.SLOPE_AND_HEIGHT_DIVIDED_THE_WRONG_WAY",
                t - slope / f0 if f0 else key + 1,
            ),
            ("MC.C12.AOD.INTERCEPT_SIGN_SLIP", t + f0 / slope),
            ("MC.C12.AOD.POINT_VALUE_REPORTED", f0),
            ("MC.C12.AOD.SLOPE_REPORTED_AS_INTERCEPT", slope),
        ],
    }[kind]
    return case(
        fam="AOD.TANGENT_NORMAL", md=md, names=["value"], value=key,
        stem=f"Let y = {poly_text(c)}. Find {ask}.",
        steps=[f"The slope of the tangent is dy/dx at x = {t}, which is {fr(slope)}.", f"The curve passes through y = {fr(f0)} at that x.", "Write the tangent line through that point with that slope. The normal has the negative reciprocal slope. Then read off what is asked.", f"The value is {fr(key)}."],
        hints=hints3(p, ["What does the derivative tell you about the tangent?", "You need both the slope and the point on the curve.", "Write the line first, then answer the question."],
                     "Find the slope from the derivative, the height from the curve itself, form the line through that point, and read off the quantity asked.",
                     "Full method: derivative gives the slope; the curve gives the point; use the point-slope form for the tangent, with the negative reciprocal slope for the normal; find the intercept or slope asked."),
        wrong=wrong, base=0.5, role="apply", prediction="Is the tangent rising or falling at this point?",
        slug=slug(deg, seed, t, kind), nsteps=5,
        methods=[("c12.tn.rules", "closed_form", "derivative_as_slope", _tn_hand),
                 ("c12.tn.sympy", "sympy.symbolic", "", _tn_sympy),
                 ("c12.tn.secant", "exact_extrapolation", "", _tn_secant)],
    )  # fmt: skip


# ================================================================ AOD.CUBIC_EXTREMA


def _cubic(md: Mapping[str, Any]) -> list[Fraction]:
    a, pp, qq, d = (F(md[k]) for k in ("a", "p", "q", "d"))
    return [d, 3 * a * pp * qq, -F(3, 2) * a * (pp + qq), a]


def _ext_hand(md: Mapping[str, Any]) -> Fraction:
    c = _cubic(md)
    d1, d2 = kit.pder(c), kit.pder(kit.pder(c))
    q, b, a = d1[0], d1[1], d1[2]
    disc = isqrt_exact(b * b - 4 * a * q)
    if disc is None:
        raise ValueError("irrational critical points")
    roots = [(-b - disc) / (2 * a), (-b + disc) / (2 * a)]
    x = next(r for r in roots if (kit.pval(d2, r) < 0) == ("max" in md["ask"]))
    return x if md["ask"].startswith("x_") else kit.pval(c, x)


def _ext_sympy(md: Mapping[str, Any]) -> Fraction:
    expr = kit.sym_poly(_cubic(md), X)
    crit = sympy.solve(sympy.diff(expr, X), X)
    sec = sympy.diff(expr, X, 2)
    x = next(r for r in crit if (sec.subs(X, r) < 0) == ("max" in md["ask"]))
    return kit.unsp(x) if md["ask"].startswith("x_") else kit.unsp(expr.subs(X, x))


def _ext_scan(md: Mapping[str, Any]) -> Fraction:
    c = _cubic(md)
    xs = [F(i, 2) for i in range(-24, 25)]
    best = []
    for i in range(1, len(xs) - 1):
        lo, m, r = (kit.pval(c, xs[j]) for j in (i - 1, i, i + 1))
        if m > lo and m > r and "max" in md["ask"]:
            best.append(xs[i])
        if m < lo and m < r and "min" in md["ask"]:
            best.append(xs[i])
    if len(best) != 1:
        raise ValueError("not exactly one local extremum of that kind on the grid")
    return best[0] if md["ask"].startswith("x_") else kit.pval(c, best[0])


@model(
    "AOD.CUBIC_EXTREMA", chapter=AOD, title="Find a local maximum or minimum of a cubic function",
    prereq=[PRE_DIFF], marks=3, technique="second_derivative_test",
    box={"p": {"choices": [-2, -1, 0, 1]}, "q": {"choices": [1, 2, 3, 4]}, "a": {"choices": [1, -1, 2, -2]},
         "d": {"choices": [0, 4]}, "ask": {"choices": ["max_value", "min_value", "x_max"]}},
)  # fmt: skip
def cubic_extrema(p: Mapping[str, Any]) -> Built:
    pp, qq, a, d, ask = int(p["p"]), int(p["q"]), int(p["a"]), int(p["d"]), str(p["ask"])
    if qq <= pp or (pp + qq) % 2 != 0 and a % 2 != 0:
        raise IllPosed("not_a_nice_cubic")
    md = {"p": pp, "q": qq, "a": a, "d": d, "ask": ask}
    c = _cubic(md)
    if any(x.denominator != 1 for x in c):
        raise IllPosed("fractional_coefficients")
    key = _ext_hand(md)
    mx = pp if a > 0 else qq
    mn = qq if a > 0 else pp
    f = lambda x: kit.pval(c, F(x))  # noqa: E731
    ask_txt = {
        "max_value": "the local maximum value of the function",
        "min_value": "the local minimum value of the function",
        "x_max": "the value of x at which the function has a local maximum",
    }[ask]
    flat = F(pp + qq, 2)
    wrong = [
        (
            "MC.C12.AOD.MAX_MIN_SWAPPED",
            f(mn) if ask == "max_value" else (f(mx) if ask == "min_value" else F(mn)),
        ),
        (
            "MC.C12.AOD.CRITICAL_X_REPORTED_AS_VALUE",
            F(mx) if ask == "max_value" else (F(mn) if ask == "min_value" else f(mx)),
        ),
        ("MC.C12.AOD.INFLECTION_POINT_USED", f(flat) if ask != "x_max" else flat),
        ("MC.C12.AOD.CONSTANT_TERM_REPORTED", c[0] if ask != "x_max" else F(0)),
    ]
    return case(
        fam="AOD.CUBIC_EXTREMA", md=md, names=["answer"], value=key,
        stem=f"Let y = {poly_text(c)}. Find {ask_txt}.",
        steps=["Differentiate and set the derivative equal to zero to find the critical points.", "Use the sign of the second derivative at each critical point: negative gives a local maximum, positive a local minimum.", f"The answer is {fr(key)}."],
        hints=hints3(p, ["Where does the slope of the curve become zero?", "Finding the critical points is only half the job: you must classify them.", "Differentiate once, then decide which critical point is which."],
                     "Solve for the points where the derivative is zero, then use the second derivative or the change of sign of the first to tell maximum from minimum.",
                     "Full method: derivative equal to zero, solve, second derivative at each solution, choose the maximum or minimum asked, and put that x into the original function if a value is wanted."),
        wrong=wrong, base=0.5, role="apply", prediction="Will the maximum be to the left or the right of the minimum?",
        slug=slug(pp, qq, a, d, ask), nsteps=5,
        methods=[("c12.ext.second", "closed_form", "second_derivative_test", _ext_hand),
                 ("c12.ext.sympy", "sympy.symbolic", "", _ext_sympy),
                 ("c12.ext.scan", "enumeration", "", _ext_scan)],
    )  # fmt: skip


# ================================================================ INT.DEFINITE_POLY


def _int_hand(md: Mapping[str, Any]) -> Fraction:
    anti = kit.pint([F(x) for x in md["coef"]])
    return kit.pval(anti, F(md["hi"])) - kit.pval(anti, F(md["lo"]))


def _int_sympy(md: Mapping[str, Any]) -> Fraction:
    return kit.unsp(
        sympy.integrate(kit.sym_poly([F(x) for x in md["coef"]], X), (X, md["lo"], md["hi"]))
    )


def _int_boole(md: Mapping[str, Any]) -> Fraction:
    c, lo, hi = [F(x) for x in md["coef"]], F(md["lo"]), F(md["hi"])
    h = (hi - lo) / 4
    f = [kit.pval(c, lo + i * h) for i in range(5)]
    return 2 * h / 45 * (7 * f[0] + 32 * f[1] + 12 * f[2] + 32 * f[3] + 7 * f[4])


@model(
    "INT.DEFINITE_POLY", chapter=INT, title="Evaluate a definite integral of a polynomial", prereq=[PRE_INT],
    marks=2, technique="antiderivative",
    box={"deg": {"choices": [2, 3, 4]}, "seed": {"min": 0, "max": 14}, "lo": {"choices": [-1, 0, 1]}, "hi": {"choices": [2, 3]}},
)  # fmt: skip
def int_definite_poly(p: Mapping[str, Any]) -> Built:
    deg, seed, lo, hi = int(p["deg"]), int(p["seed"]), int(p["lo"]), int(p["hi"])
    cs = kit.lcg(seed + 17 * deg, deg + 1, -4, 4)
    if cs[-1] == 0 or cs[0] == 0:
        raise IllPosed("a_term_is_missing")
    c = [F(x) for x in cs]
    md = {"coef": cs, "lo": lo, "hi": hi}
    key = _int_hand(md)
    anti = kit.pint(c)
    wrong = [
        (
            "MC.C12.INT.POWER_RULE_NOT_DIVIDED",
            sum(c[k] * (F(hi) ** (k + 1) - F(lo) ** (k + 1)) for k in range(len(c))),
        ),
        ("MC.C12.INT.LIMITS_SUBTRACTED_WRONG_WAY", -key),
        ("MC.C12.INT.LOWER_LIMIT_IGNORED", kit.pval(anti, F(hi))),
        (
            "MC.C12.INT.CONSTANT_TERM_DROPPED",
            sum(c[k] / (k + 1) * (F(hi) ** (k + 1) - F(lo) ** (k + 1)) for k in range(1, len(c))),
        ),
    ]
    return case(
        fam="INT.DEFINITE_POLY", md=md, names=["value"], value=key,
        stem=f"Evaluate the definite integral of {poly_text(c)} with respect to x from x = {lo} to x = {hi}.",
        steps=["Find an antiderivative term by term: raise each power by one and divide by the new power.", f"The antiderivative is {poly_text(anti)}.", f"Subtract its value at {lo} from its value at {hi}: {fr(key)}."],
        hints=hints3(p, ["Integration undoes differentiation: what happens to each power?", "Do not forget to divide by the new power.", "Find the antiderivative before you use the limits."],
                     "Write the antiderivative term by term, then evaluate it at the upper limit and subtract its value at the lower limit.",
                     "Full method: raise each power by one and divide by the new power, substitute the upper limit, substitute the lower limit, and subtract in that order."),
        wrong=wrong, base=0.35, role="apply", prediction="Roughly how large should the answer be?",
        slug=slug(deg, seed, lo, hi), nsteps=4,
        methods=[("c12.int.antiderivative", "closed_form", "antiderivative", _int_hand),
                 ("c12.int.sympy", "sympy.symbolic", "", _int_sympy),
                 ("c12.int.boole", "newton_cotes_exact", "", _int_boole)],
    )  # fmt: skip


# ================================================================ AAI.AREA_CURVES


def _area_formula(md: Mapping[str, Any]) -> Fraction:
    r, s, k = F(md["r"]), F(md["s"]), F(abs(md["k"]))
    return k * (s - r) ** 3 / 6


def _area_integral(md: Mapping[str, Any]) -> Fraction:
    r, s = F(md["r"]), F(md["s"])
    if md["kind"] == "parabola_axis":
        top = kit.pscale(kit.pmul([-r, F(1)], [-s, F(1)]), F(md["k"]))
    else:  # curve minus line: k (x - r)(x - s) is the gap between the line and the curve
        top = kit.pscale(kit.pmul([-r, F(1)], [-s, F(1)]), F(md["k"]))
    anti = kit.pint(top)
    return abs(kit.pval(anti, s) - kit.pval(anti, r))


def _area_sympy(md: Mapping[str, Any]) -> Fraction:
    k = md["k"]
    if md["kind"] == "parabola_axis":
        f, g = k * (X - md["r"]) * (X - md["s"]), sympy.Integer(0)
    else:
        f, g = k * X**2, k * ((md["r"] + md["s"]) * X - md["r"] * md["s"])
    pts = sorted(sympy.solve(sympy.Eq(f, g), X))
    return abs(kit.unsp(sympy.integrate(sympy.expand(f - g), (X, pts[0], pts[1]))))


def _area_boole(md: Mapping[str, Any]) -> Fraction:
    r, s, k = F(md["r"]), F(md["s"]), F(md["k"])
    h = (s - r) / 4

    def gap(x: Fraction) -> Fraction:
        return k * (x - r) * (x - s)

    v = [gap(r + i * h) for i in range(5)]
    return abs(2 * h / 45 * (7 * v[0] + 32 * v[1] + 12 * v[2] + 32 * v[3] + 7 * v[4]))


@model(
    "AAI.AREA_CURVES", chapter=AAI, title="Find the area enclosed by a parabola and the x-axis or a line",
    prereq=[PRE_INT], marks=3, technique="area_by_integration",
    box={"kind": {"choices": ["parabola_axis", "parabola_line"]}, "r": {"choices": [-2, -1, 0, 1]},
         "s": {"choices": [1, 2, 3, 4]}, "k": {"choices": [1, 2, 3, -1]}},
)  # fmt: skip
def area_curves(p: Mapping[str, Any]) -> Built:
    kind, r, s, k = str(p["kind"]), int(p["r"]), int(p["s"]), int(p["k"])
    if s <= r:
        raise IllPosed("roots_not_ordered")
    if kind == "parabola_line" and k < 0:
        raise IllPosed("unused_sign_variation")
    md = {"kind": kind, "r": r, "s": s, "k": k}
    key = _area_formula(md)
    span = s - r
    if kind == "parabola_axis":
        eq = poly_text([k * r * s, -k * (r + s), k])
        stem = f"Find the area of the region enclosed between the curve y = {eq} and the x-axis."
    else:
        line = poly_text([-k * r * s, k * (r + s)])
        stem = f"Find the area of the region enclosed between the parabola y = {poly_text([0, 0, k])} and the line y = {line}."
    wrong = [
        ("MC.C12.AAI.AREA_FORMULA_FACTOR_MISSING", F(abs(k)) * span**3),
        ("MC.C12.AAI.AREA_FORMULA_THIRD_USED", F(abs(k)) * span**3 / 3),
        ("MC.C12.AAI.NEGATIVE_AREA_REPORTED", -key),
        ("MC.C12.AAI.ONE_CURVE_ONLY", F(abs(k)) * span**3 / 6 + F(abs(k)) * span),
    ]
    return case(
        fam="AAI.AREA_CURVES", md=md, names=["area"], value=key, stem=stem,
        steps=[f"Find where the two curves meet: x = {r} and x = {s}.", "Subtract the lower curve from the upper curve and integrate between those two values.", f"The area is {fr(key)} square units."],
        hints=hints3(p, ["Where do the two boundaries meet?", "Area is never negative, so decide which curve is on top.", "Find the meeting points before you integrate."],
                     "Solve for the meeting points, write the upper minus the lower curve, integrate between the meeting points, and take the positive value.",
                     "Full method: meeting points, upper minus lower, antiderivative, upper limit minus lower limit, and make sure the final area is positive."),
        wrong=wrong, base=0.5, role="apply", prediction="Is the enclosed region above or below the x-axis?",
        slug=slug(kind, r, s, k), nsteps=4,
        methods=[("c12.area.formula", "closed_form", "area_by_integration", _area_formula),
                 ("c12.area.integral", "polynomial_integration", "", _area_integral),
                 ("c12.area.sympy", "sympy.symbolic", "", _area_sympy),
                 ("c12.area.boole", "newton_cotes_exact", "", _area_boole)],
    )  # fmt: skip


# ================================================================ DE.ORDER_DEGREE


def _term_txt(order: int, power: int) -> str:
    tok = "dy/dx" if order == 1 else f"d{sup(order)}y/dx{sup(order)}"
    return tok if power == 1 else f"({tok}){sup(power)}"


def _de_text(md: Mapping[str, Any]) -> str:
    parts = [_term_txt(o, g) for o, g in md["terms"]]
    return " + ".join(parts + [md["extra"]]) + " = 0"


def _de_hand(md: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
    top = max(o for o, _ in md["terms"])
    return F(top), F(next(g for o, g in md["terms"] if o == top))


def _de_sympy(md: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
    expr = sympy.Integer(0)
    symbols = {}
    for o, g in md["terms"]:
        sym = sympy.Symbol(f"D{o}")
        symbols[o] = sym
        expr += sym**g
    order = max(symbols)
    return F(order), F(sympy.degree(expr, symbols[order]))


_SUP_MAP = {c: str(i) for i, c in enumerate("⁰¹²³⁴⁵⁶⁷⁸⁹")}


def _de_parse(md: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
    """Read the order and degree back from the equation text shown to the student."""
    import re

    text = md["text"]
    best, power = 0, 1
    for m in re.finditer(r"\(?d([⁰¹²³⁴⁵⁶⁷⁸⁹]*)y/dx[⁰¹²³⁴⁵⁶⁷⁸⁹]*\)?([⁰¹²³⁴⁵⁶⁷⁸⁹]*)", text):
        order = int("".join(_SUP_MAP[c] for c in m.group(1)) or 1)
        pw = int("".join(_SUP_MAP[c] for c in m.group(2)) or 1)
        if order > best:
            best, power = order, pw
    return F(best), F(power)


@model(
    "DE.ORDER_DEGREE", chapter=DE, title="State the order and degree of a differential equation",
    prereq=[PRE_DIFF], marks=1, technique="read_highest_derivative",
    box={"o": {"choices": [1, 2, 3]}, "g": {"choices": [1, 2, 3]}, "lp": {"choices": [1, 2, 3, 4]},
         "extra": {"choices": ["y", "x", "xy"]}},
)  # fmt: skip
def de_order_degree(p: Mapping[str, Any]) -> Built:
    o, g, lp, extra = int(p["o"]), int(p["g"]), int(p["lp"]), str(p["extra"])
    if o == 1 and lp != 1:
        raise IllPosed("no_lower_derivative_to_raise")
    terms = [(o, g)] + ([(1, lp)] if o > 1 else [])
    if o == 1:
        terms = [(1, g)]
    md = {"terms": [list(t) for t in terms], "extra": extra}
    md["text"] = _de_text(md)
    key = _de_hand(md)
    top_power = max(gg for _, gg in terms)
    wrong = [
        ("MC.C12.DE.DEGREE_FROM_HIGHEST_POWER", (F(o), F(top_power))),
        ("MC.C12.DE.ORDER_DEGREE_SWAPPED", (key[1], key[0])),
        ("MC.C12.DE.ORDER_FROM_LOWER_DERIVATIVE", (F(1), key[1])),
        ("MC.C12.DE.ORDER_AS_HIGHEST_POWER", (F(top_power), F(1))),
        ("MC.C12.DE.DEGREE_COUNTED_AS_ONE", (key[0], F(1))),
        ("MC.C12.DE.ORDER_AND_DEGREE_BOTH_ADDED", (key[0] + key[1], key[1])),
    ]
    return case(
        fam="DE.ORDER_DEGREE", md=md, names=["order", "degree"], value=key,
        fmt=lambda v: f"order {fr(v[0])}, degree {fr(v[1])}",
        stem=f"State the order and the degree of the differential equation {md['text']}.",
        steps=["The order is the order of the highest derivative that appears.", "The degree is the power of that highest derivative once the equation is a polynomial in its derivatives.", f"Order {o} and degree {g}."],
        hints=hints3(p, ["Which derivative in the equation is the highest one?", "Order and degree are different ideas: one counts derivatives, one counts powers.", "Find the highest derivative first, then look at its own power."],
                     "The order is the highest derivative present; the degree is the exponent on that same highest derivative, not on any other term.",
                     "Full method: list every derivative, pick the highest order, read the power on that one derivative, and ignore the powers on lower ones."),
        wrong=wrong, base=0.2, role="recall", prediction="Which term decides the order?",
        slug=slug(o, g, lp, extra), nsteps=2, tokens=[f"order {o}, degree {g}"],
        methods=[("c12.de.hand", "closed_form", "read_highest_derivative", _de_hand),
                 ("c12.de.sympy", "sympy.degree", "", _de_sympy),
                 ("c12.de.parse", "text_parse", "", _de_parse)],
    )  # fmt: skip


# ================================================================ DE.PARTICULAR


def _dp_hand(md: Mapping[str, Any]) -> Fraction:
    anti = kit.pint([F(md["c"]), F(md["b"]), F(md["a"])])
    return F(md["y0"]) + kit.pval(anti, F(md["x1"])) - kit.pval(anti, F(md["x0"]))


def _dp_sympy(md: Mapping[str, Any]) -> Fraction:
    y = sympy.Function("y")
    sol = sympy.dsolve(
        sympy.Eq(y(X).diff(X), md["a"] * X**2 + md["b"] * X + md["c"]),
        y(X),
        ics={y(md["x0"]): md["y0"]},
    )
    return kit.unsp(sol.rhs.subs(X, md["x1"]))


def _dp_simpson(md: Mapping[str, Any]) -> Fraction:
    lo, hi = F(md["x0"]), F(md["x1"])
    mid = (lo + hi) / 2

    def f(x: Fraction) -> Fraction:
        return md["a"] * x * x + md["b"] * x + md["c"]

    return F(md["y0"]) + (hi - lo) / 6 * (f(lo) + 4 * f(mid) + f(hi))


@model(
    "DE.PARTICULAR", chapter=DE, title="Find a value of the particular solution of dy/dx = polynomial",
    prereq=[PRE_INT], marks=3, technique="integrate_then_fit_constant",
    box={"a": {"choices": [-1, 1, 3]}, "b": {"choices": [-2, 0, 2]}, "c": {"choices": [1, -3]},
         "x0": {"choices": [0, 1]}, "y0": {"choices": [-2, 1, 4]}, "x1": {"choices": [2, 3]}},
)  # fmt: skip
def de_particular(p: Mapping[str, Any]) -> Built:
    a, b, c, x0, y0, x1 = (int(p[k]) for k in ("a", "b", "c", "x0", "y0", "x1"))
    md = {"a": a, "b": b, "c": c, "x0": x0, "y0": y0, "x1": x1}
    key = _dp_hand(md)
    anti = kit.pint([F(c), F(b), F(a)])
    const = y0 - kit.pval(anti, F(x0))
    wrong = [
        ("MC.C12.DE.CONSTANT_OF_INTEGRATION_FORGOTTEN", kit.pval(anti, F(x1))),
        ("MC.C12.DE.INITIAL_VALUE_USED_AS_CONSTANT", y0 + kit.pval(anti, F(x1))),
        ("MC.C12.DE.DERIVATIVE_EVALUATED_NOT_SOLUTION", F(a * x1 * x1 + b * x1 + c)),
        ("MC.C12.DE.CONSTANT_SIGN_SLIP", kit.pval(anti, F(x1)) - const),
    ]
    return case(
        fam="DE.PARTICULAR", md=md, names=["y"], value=key,
        stem=f"A function y satisfies dy/dx = {poly_text([c, b, a])}, and y = {y0} when x = {x0}. Find the value of y when x = {x1}.",
        steps=["Integrate both sides: the general solution has an arbitrary constant.", f"Use y = {y0} at x = {x0} to find the constant: {fr(const)}.", f"Put x = {x1} into the particular solution: y = {fr(key)}."],
        hints=hints3(p, ["Is the equation giving you y or the slope of y?", "Integration brings in an unknown constant, so the given pair of values has some work to do.", "Find the general solution first."],
                     "Integrate to get the general solution, use the given pair of values to fix the constant, then evaluate at the new x.",
                     "Full method: integrate term by term with a constant, substitute the known x and y, solve for the constant, write the particular solution, and substitute the asked x."),
        wrong=wrong, base=0.45, role="apply", prediction="What does the given pair of values let you find?",
        slug=slug(a, b, c, x0, y0, x1), nsteps=4,
        methods=[("c12.dep.integrate", "closed_form", "integrate_then_fit_constant", _dp_hand),
                 ("c12.dep.sympy", "sympy.dsolve", "", _dp_sympy),
                 ("c12.dep.simpson", "newton_cotes_exact", "", _dp_simpson)],
    )  # fmt: skip
