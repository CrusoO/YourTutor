# ruff: noqa: E501
"""Independent ways to solve and classify a pair of linear equations a x + b y = c.

cramer       : closed form from the determinants (the cross-multiplication formula).
substitution : write one unknown with the other, put it into the second equation.
elimination  : scale the two equations so one unknown cancels, then back-substitute.
sympy        : SymPy's linear solver and matrix ranks.
gauss        : row reduction of the augmented matrix (also classifies a singular pair).
scan         : a search over a grid of simple rationals (no algebra at all).

Every function reads plain numbers only, never the answer or the witness. A pair is
`(a, b, c)` meaning a x + b y = c.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from fractions import Fraction
from typing import Any

import sympy

F = Fraction
Eq = tuple[Fraction, Fraction, Fraction]


def eqs(raw: Sequence[Sequence[Any]]) -> list[Eq]:
    return [(F(a), F(b), F(c)) for a, b, c in raw]


def cramer(pair: Sequence[Eq]) -> tuple[Fraction, Fraction]:
    (a1, b1, c1), (a2, b2, c2) = pair
    d = a1 * b2 - a2 * b1
    if d == 0:
        raise ValueError("no unique solution")
    return (c1 * b2 - c2 * b1) / d, (a1 * c2 - a2 * c1) / d


def substitution(pair: Sequence[Eq]) -> tuple[Fraction, Fraction]:
    (a1, b1, c1), (a2, b2, c2) = pair
    if b1 != 0:  # y = (c1 - a1 x) / b1, put into the second equation
        coef, rhs = a2 - b2 * a1 / b1, c2 - b2 * c1 / b1
        if coef == 0:
            raise ValueError("no unique solution")
        x = rhs / coef
        return x, (c1 - a1 * x) / b1
    if a1 == 0:
        raise ValueError("degenerate first equation")
    x = c1 / a1  # first equation fixes x on its own
    if b2 == 0:
        raise ValueError("no unique solution")
    return x, (c2 - a2 * x) / b2


def elimination(pair: Sequence[Eq]) -> tuple[Fraction, Fraction]:
    (a1, b1, c1), (a2, b2, c2) = pair
    # a2 * (first) - a1 * (second) removes x
    ycoef, yrhs = a2 * b1 - a1 * b2, a2 * c1 - a1 * c2
    if ycoef == 0:
        raise ValueError("no unique solution")
    y = yrhs / ycoef
    if a1 != 0:
        return (c1 - b1 * y) / a1, y
    return (c2 - b2 * y) / a2, y


def _rat(v: Any) -> Fraction:
    v = sympy.nsimplify(v)
    if not isinstance(v, sympy.Rational):
        raise ValueError("not a rational")
    return F(int(v.p), int(v.q))


def sympy_solve(pair: Sequence[Eq]) -> tuple[Fraction, Fraction]:
    x, y = sympy.symbols("x y")
    system = [
        sympy.Rational(a.numerator, a.denominator) * x
        + sympy.Rational(b.numerator, b.denominator) * y
        - sympy.Rational(c.numerator, c.denominator)
        for a, b, c in pair
    ]
    sol = sympy.linsolve(system, (x, y))
    if len(sol) != 1:
        raise ValueError("no unique solution")
    xv, yv = next(iter(sol))
    return _rat(xv), _rat(yv)


def gauss(pair: Sequence[Eq]) -> tuple[Fraction, Fraction]:
    rows = [[*e] for e in pair]
    for col in range(2):
        piv = next((r for r in range(col, 2) if rows[r][col] != 0), None)
        if piv is None:
            raise ValueError("no unique solution")
        rows[col], rows[piv] = rows[piv], rows[col]
        rows[col] = [v / rows[col][col] for v in rows[col]]
        for r in range(2):
            if r != col:
                f = rows[r][col]
                rows[r] = [v - f * w for v, w in zip(rows[r], rows[col], strict=True)]
    return rows[0][2], rows[1][2]


# ------------------------------------------------------------ classification (one, none, infinite)


def kind_ratios(pair: Sequence[Eq]) -> str:
    """The textbook test: compare a1/a2, b1/b2, c1/c2 (all of a2, b2, c2 must be non-zero)."""
    (a1, b1, c1), (a2, b2, c2) = pair
    if 0 in (a2, b2, c2):
        raise ValueError("ratio test needs non-zero second row")
    ra, rb, rc = a1 / a2, b1 / b2, c1 / c2
    if ra != rb:
        return "one"
    return "infinite" if rb == rc else "none"


def kind_sympy(pair: Sequence[Eq]) -> str:
    m = sympy.Matrix([[sympy.Rational(a.numerator, a.denominator), sympy.Rational(b.numerator, b.denominator)] for a, b, _ in pair])
    aug = sympy.Matrix(
        [[sympy.Rational(v.numerator, v.denominator) for v in row] for row in pair]
    )
    rank_a, rank_aug = m.rank(), aug.rank()
    if rank_a == 2:
        return "one"
    return "infinite" if rank_aug == rank_a else "none"


def kind_gauss(pair: Sequence[Eq]) -> str:
    rows = [[*e] for e in pair]
    r = 0
    for col in range(2):
        piv = next((i for i in range(r, 2) if rows[i][col] != 0), None)
        if piv is None:
            continue
        rows[r], rows[piv] = rows[piv], rows[r]
        rows[r] = [v / rows[r][col] for v in rows[r]]
        for i in range(2):
            if i != r:
                f = rows[i][col]
                rows[i] = [v - f * w for v, w in zip(rows[i], rows[r], strict=True)]
        r += 1
    if r == 2:
        return "one"
    return "none" if any(row[0] == 0 and row[1] == 0 and row[2] != 0 for row in rows) else "infinite"


# ------------------------------------------------------------ search


def _grid() -> list[Fraction]:
    seen = {F(p, d) for d in (1, 2) for p in range(-60 * d, 60 * d + 1)}
    return sorted(seen)


GRID = _grid()


def scan(
    resid: Callable[[Fraction, Fraction], list[Fraction]],
    y_of_x: Callable[[Fraction], Fraction | None],
    grid: Sequence[Fraction] | None = None,
) -> tuple[Fraction, Fraction]:
    """The single grid point (x, y) with y = y_of_x(x) where every residual is zero."""
    hits = []
    for x in grid or GRID:
        try:
            y = y_of_x(x)
            if y is not None and all(r == 0 for r in resid(x, y)):
                hits.append((x, y))
        except ZeroDivisionError:
            continue
    if len(hits) != 1:
        raise ValueError(f"{len(hits)} grid solutions")
    return hits[0]


def linear_y(resid: Callable[[Fraction, Fraction], list[Fraction]], row: int = 0):
    """y_of_x for residuals that are linear in y: solve the chosen residual for y."""

    def y_of_x(x: Fraction) -> Fraction | None:
        r0, r1 = resid(x, F(0))[row], resid(x, F(1))[row]
        return None if r1 == r0 else -r0 / (r1 - r0)

    return y_of_x


def scan_pair(pair: Sequence[Eq]) -> tuple[Fraction, Fraction]:
    def resid(x: Fraction, y: Fraction) -> list[Fraction]:
        return [a * x + b * y - c for a, b, c in pair]

    for row in (0, 1):
        try:
            return scan(resid, linear_y(resid, row))
        except ValueError:
            continue
    raise ValueError("no grid solution")


SOLVERS: dict[str, Callable[[Sequence[Eq]], tuple[Fraction, Fraction]]] = {
    "cramer": cramer,
    "substitution": substitution,
    "elimination": elimination,
    "sympy": sympy_solve,
    "gauss": gauss,
    "scan": scan_pair,
}


def det2(a: Fraction, b: Fraction, c: Fraction, d: Fraction) -> Fraction:
    """The determinant of [[a, b], [c, d]] by row reduction (no a*d - b*c formula)."""
    if a == 0:
        if c == 0:
            return F(0)
        a, b, c, d = c, d, a, b  # row swap
        sign = -1
    else:
        sign = 1
    return sign * a * (d - c * b / a)


def det2_sympy(a: Fraction, b: Fraction, c: Fraction, d: Fraction) -> Fraction:
    m = sympy.Matrix(2, 2, [sympy.Rational(v.numerator, v.denominator) for v in (a, b, c, d)])
    return _rat(m.det())
