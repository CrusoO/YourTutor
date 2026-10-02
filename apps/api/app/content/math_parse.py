"""Allowlist parser — never pass raw input to sympy.sympify."""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy
from sympy.parsing.sympy_parser import parse_expr

_DEVANAGARI = str.maketrans("०१२३४५६७८९", "0123456789")
_BENGALI = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_ALLOWED = re.compile(r"^([A-Za-z]\s*=\s*)?[0-9A-Za-z+\-*/^(). ]+$")
_MAX_LEN = 64
_MAX_PARENS = 8


class ParseError(ValueError):
    pass


def normalize(text: str) -> str:
    s = text.strip().translate(_DEVANAGARI).translate(_BENGALI)
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    s = s.replace("×", "*").replace("·", "*")
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
    allowed_names = {
        "Integer": sympy.Integer,
        "Float": sympy.Float,
        "Rational": sympy.Rational,
        "Symbol": sympy.Symbol,
        "Add": sympy.Add,
        "Mul": sympy.Mul,
        "Pow": sympy.Pow,
    }
    try:
        return parse_expr(
            body,
            evaluate=True,
            local_dict={},
            global_dict=allowed_names,
            transformations=(),
        )
    except Exception as exc:  # noqa: BLE001 — convert parser failures
        raise ParseError(f"could not parse expression: {exc}") from exc


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
