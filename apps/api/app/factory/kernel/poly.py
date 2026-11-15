"""Exact univariate polynomials with Fraction coefficients (lowest degree first)."""

from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction

from app.factory.kernel.exact import Reject, frac

MAX_DEGREE = 8


class Poly:
    __slots__ = ("c",)

    def __init__(self, coeffs: Iterable[object]) -> None:
        values = [frac(x) for x in coeffs]
        while values and values[-1] == 0:
            values.pop()
        if len(values) > MAX_DEGREE + 1:
            raise Reject("degree_too_high", str(len(values) - 1))
        self.c: tuple[Fraction, ...] = tuple(values)

    @property
    def degree(self) -> int:
        return len(self.c) - 1  # the zero polynomial has degree -1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Poly) and self.c == other.c

    def __hash__(self) -> int:
        return hash(self.c)

    def __add__(self, other: Poly) -> Poly:
        n = max(len(self.c), len(other.c))
        a = list(self.c) + [Fraction(0)] * (n - len(self.c))
        b = list(other.c) + [Fraction(0)] * (n - len(other.c))
        return Poly(x + y for x, y in zip(a, b, strict=True))

    def __neg__(self) -> Poly:
        return Poly(-a for a in self.c)

    def __sub__(self, other: Poly) -> Poly:
        return self + (-other)

    def __mul__(self, other: Poly) -> Poly:
        if not self.c or not other.c:
            return Poly([])
        out = [Fraction(0)] * (len(self.c) + len(other.c) - 1)
        for i, a in enumerate(self.c):
            for j, b in enumerate(other.c):
                out[i + j] += a * b
        return Poly(out)

    def at(self, x: object) -> Fraction:
        """Horner evaluation, exact."""
        point = frac(x)
        total = Fraction(0)
        for coeff in reversed(self.c):
            total = total * point + coeff
        return total

    @staticmethod
    def from_roots(lead: object, roots: Iterable[tuple[object, int]]) -> Poly:
        out = Poly([lead])
        for root, multiplicity in roots:
            if not 1 <= multiplicity <= MAX_DEGREE:
                raise Reject("bad_multiplicity", str(multiplicity))
            for _ in range(multiplicity):
                out = out * Poly([-frac(root), 1])
        return out
