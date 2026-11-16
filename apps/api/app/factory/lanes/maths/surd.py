# ruff: noqa: E501
"""Exact arithmetic in Q(sqrt2, sqrt3): numbers a + b*sqrt2 + c*sqrt3 + d*sqrt6, Fraction coefficients.

Enough for the special-angle trig table (sin/cos/tan of 0, 30, 45, 60, 90 degrees) and for the
heights-and-distances answers. Written for the maths lane; not part of the trusted kernel.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Any

SQRT = "√"
# basis index: 0 -> 1, 1 -> sqrt2, 2 -> sqrt3, 3 -> sqrt6
_ROOT_OF = {1: 2, 2: 3, 3: 6}
_MUL: dict[tuple[int, int], tuple[int, int]] = {
    (0, 0): (0, 1), (0, 1): (1, 1), (0, 2): (2, 1), (0, 3): (3, 1),
    (1, 1): (0, 2), (1, 2): (3, 1), (1, 3): (2, 2),
    (2, 2): (0, 3), (2, 3): (1, 3),
    (3, 3): (0, 6),
}  # fmt: skip


def _mul_basis(i: int, j: int) -> tuple[int, int]:
    return _MUL[(i, j)] if (i, j) in _MUL else _MUL[(j, i)]


class S:
    """An element of Q(sqrt2, sqrt3). Immutable."""

    __slots__ = ("c",)

    def __init__(self, c0: Any = 0, c2: Any = 0, c3: Any = 0, c6: Any = 0) -> None:
        self.c = (Fraction(c0), Fraction(c2), Fraction(c3), Fraction(c6))

    @staticmethod
    def of(value: Any) -> S:
        return value if isinstance(value, S) else S(value)

    def __add__(self, other: Any) -> S:
        o = S.of(other)
        return S(*(a + b for a, b in zip(self.c, o.c, strict=True)))

    __radd__ = __add__

    def __neg__(self) -> S:
        return S(*(-a for a in self.c))

    def __sub__(self, other: Any) -> S:
        return self + (-S.of(other))

    def __rsub__(self, other: Any) -> S:
        return S.of(other) - self

    def __mul__(self, other: Any) -> S:
        o = S.of(other)
        out = [Fraction(0)] * 4
        for i, a in enumerate(self.c):
            if not a:
                continue
            for j, b in enumerate(o.c):
                if not b:
                    continue
                k, f = _mul_basis(i, j)
                out[k] += a * b * f
        return S(*out)

    __rmul__ = __mul__

    def inverse(self) -> S:
        """Solve self * x = 1 as a 4x4 linear system over Fractions."""
        if not any(self.c):
            raise ZeroDivisionError("inverse of zero")
        cols = [self * S(*(1 if k == i else 0 for k in range(4))) for i in range(4)]
        rows = [[cols[j].c[i] for j in range(4)] + [Fraction(1 if i == 0 else 0)] for i in range(4)]
        for col in range(4):
            pivot = next(r for r in range(col, 4) if rows[r][col] != 0)
            rows[col], rows[pivot] = rows[pivot], rows[col]
            scale = rows[col][col]
            rows[col] = [x / scale for x in rows[col]]
            for r in range(4):
                if r != col and rows[r][col] != 0:
                    factor = rows[r][col]
                    rows[r] = [x - factor * y for x, y in zip(rows[r], rows[col], strict=True)]
        return S(*(rows[i][4] for i in range(4)))

    def __truediv__(self, other: Any) -> S:
        return self * S.of(other).inverse()

    def __rtruediv__(self, other: Any) -> S:
        return S.of(other) * self.inverse()

    def __pow__(self, n: int) -> S:
        out = S(1)
        for _ in range(n):
            out = out * self
        return out

    def __eq__(self, other: object) -> bool:
        return isinstance(other, S | int | Fraction) and self.c == S.of(other).c

    def __hash__(self) -> int:
        return hash(self.c)

    @property
    def is_rational(self) -> bool:
        return not any(self.c[1:])

    @property
    def rational(self) -> Fraction:
        if not self.is_rational:
            raise ValueError("not rational")
        return self.c[0]

    def only_sqrt3(self) -> bool:
        return not (self.c[1] or self.c[3])

    def text(self) -> str:
        return fmt(self)

    def __repr__(self) -> str:
        return f"S({fmt(self)})"


def _coeff_text(q: Fraction, root: int) -> str:
    """One term: q * sqrt(root) with q a Fraction (root 1 means a plain number)."""
    mag = abs(q)
    if root == 1:
        return str(mag)
    num, den = mag.numerator, mag.denominator
    body = (str(num) if num != 1 else "") + SQRT + str(root)
    return body if den == 1 else f"{body}/{den}"


def fmt(x: S) -> str:
    """Canonical text: rational part first, then sqrt2, sqrt3, sqrt6 terms; '-' for minus."""
    terms = [(x.c[0], 1), (x.c[1], 2), (x.c[2], 3), (x.c[3], 6)]
    out = ""
    for q, root in terms:
        if not q:
            continue
        sign = "-" if q < 0 else "+"
        body = _coeff_text(q, root)
        out += f"-{body}" if not out and sign == "-" else (body if not out else f" {sign} {body}")
    return out or "0"


def sqrt_of(n: int) -> S:
    """sqrt(n) when it lies in the field (n a square, or twice, thrice or six times a square)."""
    if n < 0:
        raise ValueError("negative")
    root = math.isqrt(n)
    if root * root == n:
        return S(root)
    for m, slot in ((2, 1), (3, 2), (6, 3)):
        if n % m == 0:
            q = n // m
            r = math.isqrt(q)
            if r * r == q:
                parts = [0, 0, 0, 0]
                parts[slot] = r
                return S(*parts)
    raise ValueError(f"sqrt({n}) is not in Q(sqrt2, sqrt3)")
