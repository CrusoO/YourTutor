# ruff: noqa: E501
"""Independent ways to evaluate the trigonometry in the Class 10 lane (never read from the answer).

closed form    : exact arithmetic in Q(sqrt2, sqrt3) with the special-triangle side ratios
                 (30-60-90 is 1 : sqrt3 : 2, 45-45-90 is 1 : 1 : sqrt2), no sine table.
sympy          : SymPy builds the triangle from the DEFINITIONS (opposite = L sin, adjacent =
                 L cos), solves for the unknown side and simplifies exactly.
numeric        : mpmath at 60 digits, then an integer-relation search (PSLQ) recovers p + q sqrt3.

All three read a structured geometry model, so the choice of sine, cosine or tangent is made by
the method and not copied from the generator.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import mpmath
import sympy

from app.factory.lanes.maths.surd import S, sqrt_of

F = Fraction
SIDES = ("opposite", "adjacent", "hypotenuse")

# (opposite, adjacent, hypotenuse) side ratios of the special triangles, as exact numbers
RATIOS: dict[int, tuple[S, S, S]] = {
    30: (S(1), sqrt_of(3), S(2)),
    45: (S(1), S(1), sqrt_of(2)),
    60: (sqrt_of(3), S(1), S(2)),
}

# exact table values (used by the standard-angle items and by the distractor generators)
SIN = {0: S(0), 30: S(F(1, 2)), 45: sqrt_of(2) / 2, 60: sqrt_of(3) / 2, 90: S(1)}
COS = {0: S(1), 30: sqrt_of(3) / 2, 45: sqrt_of(2) / 2, 60: S(F(1, 2)), 90: S(0)}
TAN: dict[int, S | None] = {0: S(0), 30: sqrt_of(3) / 3, 45: S(1), 60: sqrt_of(3), 90: None}


def s_of(pair: Any) -> S:
    """A model number [p, q] meaning p + q*sqrt3."""
    return S(F(pair[0]), 0, F(pair[1]), 0)


def s_pair(x: S) -> list[str]:
    if x.c[1] or x.c[3]:
        raise ValueError("outside Q(sqrt3)")
    return [str(x.c[0]), str(x.c[2])]


# ---------------------------------------------------------------- single right triangle


def tri_closed(m: Mapping[str, Any]) -> S:
    opp, adj, hyp = RATIOS[int(m["angle"])]
    ratio = {"opposite": opp, "adjacent": adj, "hypotenuse": hyp}
    return s_of(m["value"]) * ratio[m["unknown"]] / ratio[m["known"]]


def _sp_num(x: sympy.Expr) -> S:
    """A SymPy number a + b*sqrt3 -> S."""
    expr = sympy.expand(sympy.radsimp(sympy.simplify(x)))
    coeffs = expr.as_coefficients_dict()
    p = F(0)
    q = F(0)
    for term, c in coeffs.items():
        cf = F(int(sympy.Rational(c).p), int(sympy.Rational(c).q))
        if term == 1:
            p += cf
        elif term == sympy.sqrt(3):
            q += cf
        else:
            raise ValueError(f"unexpected term {term}")
    return S(p, 0, q, 0)


def tri_sympy(m: Mapping[str, Any]) -> S:
    theta = sympy.pi * int(m["angle"]) / 180
    length = sympy.Symbol("L", positive=True)
    sides = {
        "opposite": length * sympy.sin(theta),
        "adjacent": length * sympy.cos(theta),
        "hypotenuse": length,
    }
    value = s_of(m["value"])
    given = sympy.Rational(value.c[0].numerator, value.c[0].denominator) + sympy.Rational(
        value.c[2].numerator, value.c[2].denominator
    ) * sympy.sqrt(3)
    sol = sympy.solve(sympy.Eq(sides[m["known"]], given), length)
    if len(sol) != 1:
        raise ValueError("no unique triangle")
    return _sp_num(sides[m["unknown"]].subs(length, sol[0]))


def _pslq_sqrt3(value: mpmath.mpf) -> S:
    rel = mpmath.pslq([value, 1, mpmath.sqrt(3)], maxcoeff=10**5, maxsteps=10**5)
    if rel is None or rel[0] == 0:
        raise ValueError("no integer relation with 1 and sqrt3")
    a, b, c = rel
    return S(F(-b, a), 0, F(-c, a), 0)


def tri_numeric(m: Mapping[str, Any]) -> S:
    mpmath.mp.dps = 60
    theta = mpmath.radians(int(m["angle"]))
    sides = {
        "opposite": mpmath.sin(theta),
        "adjacent": mpmath.cos(theta),
        "hypotenuse": mpmath.mpf(1),
    }
    value = s_of(m["value"])
    known = mpmath.mpf(value.c[0].numerator) / value.c[0].denominator + (
        mpmath.mpf(value.c[2].numerator) / value.c[2].denominator
    ) * mpmath.sqrt(3)
    unit = known / sides[m["known"]]
    return _pslq_sqrt3(unit * sides[m["unknown"]])


# ---------------------------------------------------------------- two positions on a line


def two_closed(m: Mapping[str, Any]) -> S:
    """Height from two angles: the separation is the difference of the two ground distances."""
    t1, t2 = (int(x) for x in m["angles"])
    cot = {a: RATIOS[a][1] / RATIOS[a][0] for a in (30, 45, 60)}  # adjacent / opposite
    return s_of(m["separation"]) / (cot[t1] - cot[t2])


def two_sympy(m: Mapping[str, Any]) -> S:
    t1, t2 = (int(x) for x in m["angles"])
    h = sympy.Symbol("h", positive=True)
    d1 = h * sympy.cos(sympy.pi * t1 / 180) / sympy.sin(sympy.pi * t1 / 180)
    d2 = h * sympy.cos(sympy.pi * t2 / 180) / sympy.sin(sympy.pi * t2 / 180)
    sep = s_of(m["separation"])
    given = sympy.Rational(sep.c[0].numerator, sep.c[0].denominator) + sympy.Rational(
        sep.c[2].numerator, sep.c[2].denominator
    ) * sympy.sqrt(3)
    sol = sympy.solve(sympy.Eq(d1 - d2, given), h)
    if len(sol) != 1:
        raise ValueError("no unique height")
    return _sp_num(sol[0])


def two_numeric(m: Mapping[str, Any]) -> S:
    mpmath.mp.dps = 60
    t1, t2 = (int(x) for x in m["angles"])
    sep = s_of(m["separation"])
    given = mpmath.mpf(sep.c[0].numerator) / sep.c[0].denominator + (
        mpmath.mpf(sep.c[2].numerator) / sep.c[2].denominator
    ) * mpmath.sqrt(3)
    gap = mpmath.cot(mpmath.radians(t1)) - mpmath.cot(mpmath.radians(t2))
    return _pslq_sqrt3(given / gap)


# ---------------------------------------------------------------- right triangle from two legs


def hyp_closed(p: int, q: int) -> Fraction:
    import math

    h2 = p * p + q * q
    h = math.isqrt(h2)
    if h * h != h2:
        raise ValueError("hypotenuse is not a whole number")
    return F(h)


def ratio_numeric(opp: int, adj: int, name: str) -> Fraction:
    """sin/cos/tan of the angle with these legs, by atan2 and a PSLQ-free rational recovery."""
    mpmath.mp.dps = 50
    theta = mpmath.atan2(opp, adj)
    fn = {"sin": mpmath.sin, "cos": mpmath.cos, "tan": mpmath.tan}[name]
    value = fn(theta)
    frac = F(str(mpmath.nstr(value, 40))).limit_denominator(10**8)
    if abs(value - mpmath.mpf(frac.numerator) / frac.denominator) > mpmath.mpf(10) ** -35:
        raise ValueError("value is not a small rational")
    return frac


def rational_from_mp(value: mpmath.mpf) -> Fraction:
    frac = F(str(mpmath.nstr(value, 40))).limit_denominator(10**8)
    if abs(value - mpmath.mpf(frac.numerator) / frac.denominator) > mpmath.mpf(10) ** -35:
        raise ValueError("value is not a small rational")
    return frac
