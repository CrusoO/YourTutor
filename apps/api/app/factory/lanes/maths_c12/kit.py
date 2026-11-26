# ruff: noqa: E501
"""Exact helpers shared by the Class 12 models: hand-written Fraction algorithms, SymPy bridges."""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from fractions import Fraction
from typing import Any

import sympy

F = Fraction
Mat = list[list[Fraction]]


def lcg(seed: int, n: int, lo: int, hi: int) -> list[int]:
    """n pseudo-random integers in [lo, hi], fixed by the seed (never random at run time)."""
    out, x = [], (seed * 2654435761 + 12345) % 2147483648
    for _ in range(n):
        x = (x * 1103515245 + 12345) % 2147483648
        out.append(lo + (x >> 8) % (hi - lo + 1))
    return out


def sp(x: Any) -> sympy.Rational:
    f = Fraction(x)
    return sympy.Rational(f.numerator, f.denominator)


def unsp(e: Any) -> Fraction:
    e = sympy.nsimplify(e) if not isinstance(e, sympy.Rational | sympy.Integer) else e
    if not getattr(e, "is_Rational", False):
        raise ValueError(f"not a rational number: {e!r}")
    return Fraction(int(e.p), int(e.q))


def to_frac(x: float, maxden: int = 100000, tol: float = 1e-7) -> Fraction:
    """A float result of a numeric method as the nearest fraction; refuses if it is not close."""
    f = Fraction(x).limit_denominator(maxden)
    if abs(float(f) - x) > tol * max(1.0, abs(x)):
        raise ValueError(f"numeric result {x!r} is not close to a fraction")
    return f


def mat(rows: Sequence[Sequence[Any]]) -> Mat:
    return [[Fraction(x) for x in row] for row in rows]


def transpose(m: Mat) -> Mat:
    return [list(r) for r in zip(*m, strict=True)]


def matmul(a: Mat, b: Mat) -> Mat:
    return [
        [sum((a[i][k] * b[k][j] for k in range(len(b))), Fraction(0)) for j in range(len(b[0]))]
        for i in range(len(a))
    ]


def minor(m: Mat, i: int, j: int) -> Mat:
    return [[x for c, x in enumerate(row) if c != j] for r, row in enumerate(m) if r != i]


def det_cofactor(m: Mat) -> Fraction:
    """Expansion along the first row."""
    if len(m) == 1:
        return m[0][0]
    return sum(((-1) ** j) * m[0][j] * det_cofactor(minor(m, 0, j)) for j in range(len(m)))


def _parity(p: Sequence[int]) -> int:
    inv = sum(1 for i in range(len(p)) for j in range(i + 1, len(p)) if p[i] > p[j])
    return -1 if inv % 2 else 1


def det_leibniz(m: Mat) -> Fraction:
    """Sum over permutations (the definition)."""
    n = len(m)
    total = Fraction(0)
    for perm in itertools.permutations(range(n)):
        term = Fraction(_parity(perm))
        for i in range(n):
            term *= m[i][perm[i]]
        total += term
    return total


def cofactor(m: Mat, i: int, j: int) -> Fraction:
    sub = minor(m, i, j)
    return ((-1) ** (i + j)) * (det_cofactor(sub) if sub else Fraction(1))


def adjugate(m: Mat) -> Mat:
    n = len(m)
    return [[cofactor(m, j, i) for j in range(n)] for i in range(n)]


def gauss_inverse(m: Mat) -> Mat:
    """Gauss-Jordan on [A | I]."""
    n = len(m)
    a = [row[:] + [Fraction(int(i == j)) for j in range(n)] for i, row in enumerate(m)]
    for col in range(n):
        piv = next((r for r in range(col, n) if a[r][col] != 0), None)
        if piv is None:
            raise ValueError("singular")
        a[col], a[piv] = a[piv], a[col]
        lead = a[col][col]
        a[col] = [x / lead for x in a[col]]
        for r in range(n):
            if r != col and a[r][col] != 0:
                f = a[r][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col], strict=True)]
    return [row[n:] for row in a]


def gauss_solve(a: Mat, b: Sequence[Fraction]) -> list[Fraction]:
    n = len(a)
    aug = [a[i][:] + [Fraction(b[i])] for i in range(n)]
    for col in range(n):
        piv = next((r for r in range(col, n) if aug[r][col] != 0), None)
        if piv is None:
            raise ValueError("singular")
        aug[col], aug[piv] = aug[piv], aug[col]
        aug[col] = [x / aug[col][col] for x in aug[col]]
        for r in range(n):
            if r != col and aug[r][col] != 0:
                f = aug[r][col]
                aug[r] = [x - f * y for x, y in zip(aug[r], aug[col], strict=True)]
    return [aug[i][n] for i in range(n)]


def smat(m: Mat) -> sympy.Matrix:
    return sympy.Matrix([[sp(x) for x in row] for row in m])


def pmul(a: Sequence[Fraction], b: Sequence[Fraction]) -> list[Fraction]:
    out = [Fraction(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def padd(a: Sequence[Fraction], b: Sequence[Fraction]) -> list[Fraction]:
    n = max(len(a), len(b))
    return [
        (a[i] if i < len(a) else Fraction(0)) + (b[i] if i < len(b) else Fraction(0))
        for i in range(n)
    ]


def pscale(a: Sequence[Fraction], k: Fraction) -> list[Fraction]:
    return [k * x for x in a]


def ppow(a: Sequence[Fraction], n: int) -> list[Fraction]:
    out = [Fraction(1)]
    for _ in range(n):
        out = pmul(out, a)
    return out


def pval(c: Sequence[Fraction], x: Fraction) -> Fraction:
    total = Fraction(0)
    for coeff in reversed(c):
        total = total * x + coeff
    return total


def pder(c: Sequence[Fraction]) -> list[Fraction]:
    return [k * c[k] for k in range(1, len(c))] or [Fraction(0)]


def pint(c: Sequence[Fraction]) -> list[Fraction]:
    """Antiderivative with constant term 0."""
    return [Fraction(0)] + [c[k] / (k + 1) for k in range(len(c))]


def sym_poly(c: Sequence[Fraction], x: sympy.Symbol) -> sympy.Expr:
    return sum((sp(a) * x**k for k, a in enumerate(c)), sympy.Integer(0))
