"""Exact numbers, lane units and a tiny exact expression evaluator for the physics lane.

Nothing here is trusted by the kernel: it only builds data. Units are built on the kernel unit
table (`units.parse_unit`); the lane adds the electrical and optical names the kernel table does
not have (volt, ohm, dioptre, kilowatt-hour) by expanding them into kernel units.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.kernel import units as kunits
from app.factory.kernel.exact import frac, rational_sqrt

Dim = kunits.Dim

# lane unit -> (factor applied to the kernel expression, kernel expression)
_EXPAND: dict[str, tuple[Fraction, str]] = {
    "V": (Fraction(1), "W/A"),
    "mV": (Fraction(1, 1000), "W/A"),
    "kV": (Fraction(1000), "W/A"),
    "ohm": (Fraction(1), "W/A^2"),
    "kohm": (Fraction(1000), "W/A^2"),
    "mA": (Fraction(1, 1000), "A"),
    "kW": (Fraction(1000), "W"),
    "kJ": (Fraction(1000), "J"),
    "kWh": (Fraction(3_600_000), "J"),
    "ohm*m": (Fraction(1), "W/A^2*m"),
    "D": (Fraction(1), "1/m"),
    "unit": (Fraction(1), "1"),
    "m/s": (Fraction(1), "m/s"),
}

UNIT_TEXT = {
    "ohm": "Ω",
    "kohm": "kΩ",
    "ohm*m": "Ω m",
    "m^2": "m²",
    "mm^2": "mm²",
    "cm^2": "cm²",
    "unit": "",
    "1": "",
}


def unit_si(unit: str) -> tuple[Fraction, Dim]:
    """(SI per one of this unit, dimension vector). Raises Reject on an unknown unit."""
    if unit in _EXPAND:
        scale, expr = _EXPAND[unit]
        factor, dim = kunits.parse_unit(expr)
        return scale * factor, dim
    return kunits.parse_unit(unit)


def to_si(value: Any, unit: str) -> Fraction:
    return frac(value) * unit_si(unit)[0]


def from_si(si_value: Fraction, unit: str) -> Fraction:
    return si_value / unit_si(unit)[0]


def unit_text(unit: str) -> str:
    return UNIT_TEXT.get(unit, unit)


# ---------------------------------------------------------------- decimals


def dec(value: Fraction, max_places: int = 12) -> str | None:
    """Exact terminating decimal text, or None when the fraction does not terminate."""
    d = value.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d != 1:
        return None
    sign = "-" if value < 0 else ""
    num, den = abs(value.numerator), value.denominator
    places = 0
    while num % den:
        num *= 10
        places += 1
        if places > max_places:
            return None
    whole = num // den
    if places == 0:
        return f"{sign}{whole}"
    digits = str(whole).rjust(places + 1, "0")
    text = f"{digits[:-places]}.{digits[-places:]}".rstrip("0").rstrip(".")
    return f"{sign}{text}"


def fstr(value: Fraction) -> str:
    """Canonical exact text: a terminating decimal if there is one, else a ratio."""
    text = dec(value)
    return text if text is not None else f"{value.numerator}/{value.denominator}"


def sig_figs(value: Fraction) -> int | None:
    """Significant digits of a terminating decimal (trailing zeros of integers not counted)."""
    text = dec(abs(value))
    if text is None:
        return None
    if value == 0:
        return 1
    digits = text.replace(".", "").lstrip("0")
    if "." not in text:
        digits = digits.rstrip("0")
    return len(digits) or 1


def disp(value: Fraction) -> str:
    """Learner-facing number: plain decimal, or `a x 10^k` for very large or small values."""
    if value == 0:
        return "0"
    mag = abs(value)
    if mag >= 10**6 or mag < Fraction(1, 1000):
        exp = 0
        m = mag
        while m >= 10:
            m /= 10
            exp += 1
        while m < 1:
            m *= 10
            exp -= 1
        text = dec(m)
        if text is None:
            return f"{float(value):.3g}"
        sign = "-" if value < 0 else ""
        return f"{sign}{text} x 10^{exp}"
    text = dec(value)
    return text if text is not None else f"{float(value):.3g}"


def quantity_text(value: Fraction, unit: str) -> str:
    return f"{disp(value)} {unit_text(unit)}".strip()


# ---------------------------------------------------------------- expressions

_TOKEN = re.compile(r"\s*(\d+\.?\d*(?:[eE][+-]?\d+)?|[A-Za-z_][A-Za-z_0-9]*|[-+*/^()])")


class ExprError(ValueError):
    pass


def _tokens(text: str) -> list[str]:
    out, pos = [], 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip():
                raise ExprError(f"bad character in {text!r}")
            break
        out.append(m.group(1))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, text: str, env: Mapping[str, Fraction]) -> None:
        self.t, self.i, self.env = _tokens(text), 0, env

    def peek(self) -> str | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self) -> str:
        tok = self.peek()
        if tok is None:
            raise ExprError("unexpected end")
        self.i += 1
        return tok

    def expr(self) -> Fraction:
        v = self.term()
        while self.peek() in ("+", "-"):
            v = v + self.term() if self.take() == "+" else v - self.term()
        return v

    def term(self) -> Fraction:
        v = self.unary()
        while self.peek() in ("*", "/"):
            if self.take() == "*":
                v = v * self.unary()
            else:
                d = self.unary()
                if d == 0:
                    raise ExprError("division by zero")
                v = v / d
        return v

    def unary(self) -> Fraction:
        if self.peek() == "-":
            self.take()
            return -self.unary()
        return self.power()

    def power(self) -> Fraction:
        base = self.atom()
        if self.peek() == "^":
            self.take()
            exp = self.unary()
            if exp.denominator != 1 or abs(exp) > 6:
                raise ExprError("only small integer powers")
            if base == 0 and exp < 0:
                raise ExprError("division by zero")
            return base ** int(exp)
        return base

    def atom(self) -> Fraction:
        tok = self.take()
        if tok == "(":
            v = self.expr()
            if self.take() != ")":
                raise ExprError("missing )")
            return v
        if tok[0].isdigit():
            return Fraction(tok)
        if self.peek() == "(" and tok == "abs":
            self.take()
            v = self.expr()
            if self.take() != ")":
                raise ExprError("missing )")
            return abs(v)
        if self.peek() == "(" and tok == "sqrt":
            self.take()
            v = self.expr()
            if self.take() != ")":
                raise ExprError("missing )")
            root = rational_sqrt(v)
            if root is None:
                raise ExprError("not a perfect square")
            return root
        if tok not in self.env:
            raise ExprError(f"unknown name {tok}")
        return self.env[tok]


def evaluate(text: str, env: Mapping[str, Fraction]) -> Fraction:
    """Exact value of an arithmetic expression over named Fractions (+ - * / ^int sqrt)."""
    parser = _Parser(text, env)
    value = parser.expr()
    if parser.peek() is not None:
        raise ExprError(f"trailing text in {text!r}")
    return value


def expr_names(text: str) -> set[str]:
    return {
        t for t in _tokens(text) if (t[0].isalpha() or t[0] == "_") and t not in ("sqrt", "abs")
    }
