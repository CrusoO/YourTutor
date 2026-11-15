"""Exact linear algebra over Q: rank, nullspace, primitive integer vectors."""

from __future__ import annotations

import math
from fractions import Fraction

from app.factory.kernel.exact import Deadline, Reject

Matrix = list[list[Fraction]]


def rref(rows: Matrix, deadline: Deadline | None = None) -> tuple[Matrix, list[int]]:
    m = [row[:] for row in rows]
    pivots: list[int] = []
    r = 0
    ncols = len(m[0]) if m else 0
    for col in range(ncols):
        if deadline:
            deadline.check()
        pivot = next((i for i in range(r, len(m)) if m[i][col] != 0), None)
        if pivot is None:
            continue
        m[r], m[pivot] = m[pivot], m[r]
        lead = m[r][col]
        m[r] = [x / lead for x in m[r]]
        for i in range(len(m)):
            if i != r and m[i][col] != 0:
                factor = m[i][col]
                m[i] = [a - factor * b for a, b in zip(m[i], m[r], strict=True)]
        pivots.append(col)
        r += 1
    return m, pivots


def rank(rows: Matrix) -> int:
    return len(rref(rows)[1]) if rows else 0


def nullspace(rows: Matrix, ncols: int) -> list[list[Fraction]]:
    reduced, pivots = rref(rows) if rows else ([], [])
    free = [c for c in range(ncols) if c not in pivots]
    basis: list[list[Fraction]] = []
    for f in free:
        vec = [Fraction(0)] * ncols
        vec[f] = Fraction(1)
        for row, p in zip(reduced, pivots, strict=False):
            vec[p] = -row[f]
        basis.append(vec)
    return basis


def primitive_integer(vec: list[Fraction]) -> list[int]:
    """Smallest integer multiple of vec with gcd 1, first nonzero entry positive."""
    if not any(vec):
        raise Reject("zero_vector")
    den = 1
    for x in vec:
        den = den * x.denominator // math.gcd(den, x.denominator)
    ints = [int(x * den) for x in vec]
    g = math.gcd(*ints)
    ints = [i // g for i in ints]
    first = next(i for i in ints if i != 0)
    return [-i for i in ints] if first < 0 else ints


def times(rows: list[list[int]], vec: list[int]) -> list[int]:
    return [sum(a * b for a, b in zip(row, vec, strict=True)) for row in rows]
