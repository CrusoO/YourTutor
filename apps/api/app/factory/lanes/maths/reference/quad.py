# ruff: noqa: E501
"""Independent ways to read a quadratic equation from its spec: three engines, three groups.

closed   : coefficients read from the lists, quadratic formula in exact integer arithmetic.
sympy    : SymPy builds the polynomial, solves it and takes its discriminant.
interp   : coefficients recovered from the values at x = 0, 1, -1 (never read from the lists), the
           discriminant from the value at the vertex, roots by a rational-root scan.

Each engine returns the same plain dict, so a family method is a small read of one field.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import sympy

from app.factory.kernel.exact import frac, rational_sqrt

PM = "±"
SQRT = "√"


def squarefree(n: int) -> tuple[int, int]:
    """n = k*k*m with m squarefree: returns (k, m)."""
    k, m, d = 1, n, 2
    while d * d <= m:
        while m % (d * d) == 0:
            m //= d * d
            k *= d
        d += 1
    return k, m


def surd_pair_text(p: Fraction, t2: Fraction) -> str:
    """The two roots p +- sqrt(t2), with t2 > 0 and not a rational square, in lowest terms."""
    k, m = squarefree(t2.numerator * t2.denominator)
    q = Fraction(k, t2.denominator)
    scale = math.lcm(p.denominator, q.denominator)
    big_p, big_q = int(p * scale), int(q * scale)
    g = math.gcd(math.gcd(abs(big_p), big_q), scale)
    big_p, big_q, scale = big_p // g, big_q // g, scale // g
    root = (str(big_q) if big_q != 1 else "") + SQRT + str(m)
    if scale == 1:
        return f"{big_p} {PM} {root}" if big_p else f"{PM}{root}"
    return f"({big_p} {PM} {root})/{scale}" if big_p else f"{PM}{root}/{scale}"


def raw_eval(spec: Mapping[str, Any], x: Fraction) -> Fraction:
    """lhs - rhs at x, Horner on the raw coefficient lists."""

    def horner(coeffs: list[Any]) -> Fraction:
        total = Fraction(0)
        for c in reversed(coeffs):
            total = total * x + frac(c)
        return total

    return horner(list(spec["lhs"])) - horner(list(spec.get("rhs", [])))


def _roots_closed(c: Fraction, b: Fraction, a: Fraction) -> list[Fraction] | None:
    disc = b * b - 4 * a * c
    root = rational_sqrt(disc)
    if root is None:
        return None
    return sorted({(-b - root) / (2 * a), (-b + root) / (2 * a)})


def info_closed(spec: Mapping[str, Any]) -> dict[str, Any]:
    lhs = [frac(x) for x in spec["lhs"]] + [Fraction(0)] * 3
    rhs = [frac(x) for x in spec.get("rhs", [])] + [Fraction(0)] * 3
    c, b, a = (lhs[i] - rhs[i] for i in range(3))
    return {"c": c, "b": b, "a": a, "D": b * b - 4 * a * c, "roots": _roots_closed(c, b, a)}


def info_sympy(spec: Mapping[str, Any]) -> dict[str, Any]:
    x = sympy.Symbol("x")

    def poly(coeffs: list[Any]) -> sympy.Expr:
        return sum(
            (
                sympy.Rational(frac(cf).numerator, frac(cf).denominator) * x**i
                for i, cf in enumerate(coeffs)
            ),
            sympy.Integer(0),
        )

    expr = sympy.expand(poly(list(spec["lhs"])) - poly(list(spec.get("rhs", []))))
    p = sympy.Poly(expr, x)
    co = p.all_coeffs()[::-1] + [sympy.Integer(0)] * 3
    c, b, a = (Fraction(int(v.p), int(v.q)) for v in co[:3])
    disc = sympy.discriminant(p, x)
    sols = sympy.solve(expr, x)
    roots = None
    if len(sols) and all(s.is_Rational for s in sols):
        roots = sorted({Fraction(int(s.p), int(s.q)) for s in sols})
    return {
        "c": c, "b": b, "a": a, "D": Fraction(int(disc.p), int(disc.q)), "roots": roots,
        "sympy_solutions": sols,
    }  # fmt: skip


def info_interp(spec: Mapping[str, Any]) -> dict[str, Any]:
    p0, p1, pm1 = (raw_eval(spec, Fraction(v)) for v in (0, 1, -1))
    a = (p1 + pm1) / 2 - p0
    b = (p1 - pm1) / 2
    c = p0
    if a == 0:
        raise ValueError("not quadratic")
    vertex = -b / (2 * a)
    disc = -4 * a * raw_eval(spec, vertex)  # P(vertex) = -D / 4a
    scale = math.lcm(*(x.denominator for x in (a, b, c)))
    ia, ib, ic = int(a * scale), int(b * scale), int(c * scale)
    found: set[Fraction] = set()
    if ic == 0:  # x is a factor: the other root comes from the linear factor
        found.update({Fraction(0), Fraction(-ib, ia)})
    else:
        lows = [d for d in range(1, abs(ic) + 1) if abs(ic) % d == 0]
        highs = [d for d in range(1, abs(ia) + 1) if abs(ia) % d == 0]
        for num in lows:
            for den in highs:
                for sign in (1, -1):
                    r = Fraction(sign * num, den)
                    if ia * r * r + ib * r + ic == 0:
                        found.add(r)
    return {"c": c, "b": b, "a": a, "D": disc, "roots": sorted(found) or None}


ENGINES = {"closed": info_closed, "sympy": info_sympy, "interp": info_interp}
