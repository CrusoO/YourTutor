"""Exact unit conversion with dimension vectors (no pint). Units multiply, divide, take ints."""

from __future__ import annotations

import re
from fractions import Fraction

from app.factory.kernel.exact import Reject, frac

# dimension vector order: length, mass, time, current, temperature, amount
Dim = tuple[int, int, int, int, int, int]
ZERO: Dim = (0, 0, 0, 0, 0, 0)
L: Dim = (1, 0, 0, 0, 0, 0)
M: Dim = (0, 1, 0, 0, 0, 0)
T: Dim = (0, 0, 1, 0, 0, 0)
CURRENT: Dim = (0, 0, 0, 1, 0, 0)
TEMP: Dim = (0, 0, 0, 0, 1, 0)
AMOUNT: Dim = (0, 0, 0, 0, 0, 1)


def dmul(a: Dim, b: Dim, power: int = 1) -> Dim:
    return tuple(x + power * y for x, y in zip(a, b, strict=True))  # type: ignore[return-value]


def _u(factor: str, dim: Dim) -> tuple[Fraction, Dim]:
    return (Fraction(factor), dim)


_FORCE = dmul(dmul(M, L), T, -2)
_ENERGY = dmul(_FORCE, L)
_UNITS: dict[str, tuple[Fraction, Dim]] = {
    "1": _u("1", ZERO), "m": _u("1", L), "cm": _u("1/100", L), "mm": _u("1/1000", L),
    "km": _u("1000", L), "kg": _u("1", M), "g": _u("1/1000", M), "mg": _u("1/1000000", M),
    "s": _u("1", T), "min": _u("60", T), "h": _u("3600", T), "A": _u("1", CURRENT),
    "K": _u("1", TEMP), "mol": _u("1", AMOUNT), "mmol": _u("1/1000", AMOUNT),
    "L": _u("1/1000", dmul(L, L, 3)), "mL": _u("1/1000000", dmul(L, L, 3)),
    "N": _u("1", _FORCE), "J": _u("1", _ENERGY), "W": _u("1", dmul(_ENERGY, T, -1)),
    "Pa": _u("1", dmul(_FORCE, L, -2)), "C": _u("1", dmul(CURRENT, T)),
}  # fmt: skip
_FACTOR = re.compile(r"^([A-Za-z]+|1)(?:\^(-?\d))?$")


def parse_unit(text: str) -> tuple[Fraction, Dim]:
    """`kg*m/s^2`, `km/h`, `J/mol/K`: left to right, each * or / applies to the next factor."""
    if not isinstance(text, str) or not text or len(text) > 40:
        raise Reject("bad_unit", repr(text)[:40])
    tokens = re.split(r"([*/])", text.replace(" ", ""))
    factor, dim, op = Fraction(1), ZERO, "*"
    for index, token in enumerate(tokens):
        if index % 2 == 1:
            op = token
            continue
        match = _FACTOR.match(token)
        if not match or match.group(1) not in _UNITS:
            raise Reject("unknown_unit", token)
        scale, base = _UNITS[match.group(1)]
        power = int(match.group(2) or 1) * (1 if op == "*" else -1)
        factor *= scale**power
        dim = dmul(dim, base, power)
    return factor, dim


def to_si(value: object, unit: str) -> tuple[Fraction, Dim]:
    factor, dim = parse_unit(unit)
    return frac(value) * factor, dim


def from_si(si_value: Fraction, unit: str) -> tuple[Fraction, Dim]:
    factor, dim = parse_unit(unit)
    return si_value / factor, dim
