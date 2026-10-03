"""Allowlist parser — never pass raw input to sympy.sympify."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import sympy
from sympy.parsing.sympy_parser import parse_expr

_ALLOWED = re.compile(r"^([A-Za-z]\s*=\s*)?[0-9A-Za-z+\-*/^()., ]+$")
_MAX_LEN = 64
_MAX_PARENS = 8


class ParseError(ValueError):
    pass


def _ascii_digits(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if ch.isdecimal():
            out.append(str(unicodedata.digit(ch)))
        else:
            out.append(ch)
    return "".join(out)


def normalize(text: str, *, notation_profile: str = "default_ascii") -> str:
    from app.registries.loaders import load_notation_profiles

    profiles = load_notation_profiles()
    profile = profiles.get(notation_profile) or profiles["default_ascii"]
    s = _ascii_digits(text.strip())
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    for sym in profile.multiply_symbols:
        if sym != "*":
            s = s.replace(sym, "*")
    for sym in profile.divide_symbols:
        if sym != "/":
            s = s.replace(sym, "/")
    if profile.decimal_separator == ",":
        s = re.sub(r"(\d),(\d)", r"\1.\2", s)
    elif "," in s:
        # Decimal comma profile not active — reject comma decimals.
        if re.search(r"\d,\d", s):
            raise ParseError("decimal comma not allowed for this notation profile")
    return re.sub(r"\s+", " ", s).strip()


def _safe_parse(expr: str) -> sympy.Expr:
    if len(expr) > _MAX_LEN:
        raise ParseError("expression too long")
    if expr.count("(") > _MAX_PARENS or "__" in expr:
        raise ParseError("expression rejected")
    if not _ALLOWED.match(expr):
        raise ParseError("expression failed allowlist")
    body = expr
    if "=" in expr:
        left, right = expr.split("=", 1)
        left, right = left.strip(), right.strip()
        if re.fullmatch(r"[A-Za-z]", left):
            body = right
        else:
            body = f"({left})-({right})"
    body = body.replace("^", "**")
    if not _ALLOWED.match(body.replace("**", "^")) and "**" not in body:
        raise ParseError("expression failed allowlist")
    # Implicit multiplication on allowlisted text only (2x → 2*x, 2(x-1) → 2*(x-1)).
    body = re.sub(r"(\d)([A-Za-z(])", r"\1*\2", body)
    body = re.sub(r"([A-Za-z)])(\()", r"\1*\2", body)
    allowed_names = {
        "Integer": sympy.Integer,
        "Float": sympy.Float,
        "Rational": sympy.Rational,
        "Symbol": sympy.Symbol,
        "Add": sympy.Add,
        "Mul": sympy.Mul,
        "Pow": sympy.Pow,
    }
    letters = {ch: sympy.Symbol(ch) for ch in re.findall(r"[A-Za-z]", body)}
    try:
        parsed = parse_expr(
            body,
            evaluate=True,
            local_dict=letters,
            global_dict=allowed_names,
            transformations=(),
        )
    except Exception as exc:  # noqa: BLE001 — convert parser failures
        raise ParseError(f"could not parse expression: {exc}") from exc
    return _to_expr(parsed)


def _to_expr(value: object) -> sympy.Expr:
    if isinstance(value, sympy.Expr):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return sympy.Integer(value)
    if isinstance(value, float):
        return sympy.Float(value)
    raise ParseError("parser returned non-expression")


def parse_math(text: str) -> sympy.Expr:
    return _safe_parse(normalize(text))


def expressions_equivalent(left: str, right: str, *, numeric_tol: float = 1e-9) -> bool:
    try:
        a = parse_math(left)
        b = parse_math(right)
    except ParseError:
        return False
    diff = sympy.simplify(a - b)
    if diff == 0:
        return True
    if diff.is_number:
        return abs(float(diff.evalf())) < numeric_tol
    return False


@dataclass(frozen=True)
class ExtractedNumber:
    raw: str


_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def find_numbers(text: str) -> list[str]:
    return _NUMBER.findall(normalize(text))
