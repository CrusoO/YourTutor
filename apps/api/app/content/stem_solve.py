"""Solve authored stems through the allowlist parser — never raw sympify."""

from __future__ import annotations

import re

import sympy

from app.content.math_parse import ParseError, expressions_equivalent, normalize, parse_math
from app.content.schema import Item, ItemType, VerifySpec

_SOLVE = re.compile(r"solve for [a-z]\s*:\s*(.+)$", re.IGNORECASE)
_COMPUTE = re.compile(r"^compute\s+(.+?)\.?$", re.IGNORECASE)


class Unsolvable(ValueError):
    pass


def extract_solvable(stem: str) -> str | None:
    text = stem.strip().rstrip(".")
    match = _SOLVE.search(text)
    if match:
        return match.group(1).strip()
    match = _COMPUTE.match(text)
    if match:
        return match.group(1).strip()
    return None


def _as_expr(value: object) -> sympy.Expr:
    if isinstance(value, sympy.Expr):
        return value
    if isinstance(value, bool):
        raise Unsolvable("not an expression")
    if isinstance(value, int):
        return sympy.Integer(value)
    if isinstance(value, float):
        return sympy.Float(value)
    raise Unsolvable("not an expression")


def solve_extracted(extracted: str, unknown: str | None = None) -> sympy.Expr:
    text = normalize(extracted)
    if "=" in text:
        left, right = text.split("=", 1)
        expr = _as_expr(parse_math(left)) - _as_expr(parse_math(right))
        if unknown:
            symbol = sympy.Symbol(unknown)
            if symbol not in expr.free_symbols:
                raise Unsolvable(f"unknown {unknown} not in expression")
            target = symbol
        else:
            symbols = list(expr.free_symbols)
            if not symbols:
                if expr == 0:
                    raise Unsolvable("identity, not a unique value")
                raise Unsolvable("no free symbol")
            target = symbols[0]
        solutions = sympy.solve(expr, target)
        if len(solutions) != 1:
            raise Unsolvable(f"expected one solution, got {solutions}")
        return _as_expr(solutions[0])
    value = _as_expr(parse_math(text))
    if value.free_symbols:
        raise Unsolvable("arithmetic still has symbols")
    return value


def substitution_holds(equation: str, value: str) -> bool:
    text = normalize(equation)
    if "=" not in text:
        raise Unsolvable("substitution needs an equation")
    left, right = text.split("=", 1)
    expr = _as_expr(parse_math(left)) - _as_expr(parse_math(right))
    symbols = list(expr.free_symbols)
    if len(symbols) != 1:
        raise Unsolvable("substitution needs one unknown")
    plugged = expr.subs(symbols[0], _as_expr(parse_math(value)))
    return sympy.simplify(plugged) == 0


def solution_count_label(equation: str) -> str:
    text = normalize(equation)
    if "=" not in text:
        raise Unsolvable("solution_count needs an equation")
    left, right = text.split("=", 1)
    expr = _as_expr(parse_math(left)) - _as_expr(parse_math(right))
    symbols = list(expr.free_symbols)
    if not symbols:
        return "every" if expr == 0 else "none"
    solutions = sympy.solve(expr, symbols[0])
    if not solutions:
        return "none"
    if len(solutions) == 1:
        return "one"
    return "every"


def _matches_answer(solved: sympy.Expr, answer_sympy: str) -> bool:
    try:
        expected = parse_math(answer_sympy)
    except ParseError:
        return False
    if expressions_equivalent(str(solved), answer_sympy):
        return True
    return sympy.simplify(solved - expected) == 0


def check_item_stem_answer(item: Item) -> str | None:
    """Return None if verified, 'manual' if stem-only review, 'teacher' if not
    machine-verifiable, or an error string on mismatch."""
    if item.type in {ItemType.expression, ItemType.numeric}:
        extracted = extract_solvable(item.stem.en)
        if extracted is not None:
            try:
                solved = solve_extracted(extracted)
            except (ParseError, Unsolvable):
                solved = None
            else:
                if not _matches_answer(solved, item.answer.sympy):
                    return (
                        f"{item.id} stem solves to {solved}, "
                        f"which does not match answer.sympy={item.answer.sympy!r}"
                    )
                return None
    if item.verify:
        return _check_verify(item)
    return "teacher"


def _check_verify(item: Item) -> str | None:
    spec = item.verify
    try:
        if isinstance(spec, str):
            solved = solve_extracted(spec)
            if not _matches_answer(solved, item.answer.sympy):
                return (
                    f"{item.id} verify solves to {solved}, "
                    f"which does not match answer.sympy={item.answer.sympy!r}"
                )
            return None
        assert isinstance(spec, VerifySpec)
        kind = spec.kind
        if kind == "substitution":
            if not spec.equation or spec.value is None:
                return f"{item.id} substitution verify needs equation and value"
            holds = substitution_holds(spec.equation, spec.value)
            expected = "yes" if holds else "no"
            if item.answer.sympy != expected:
                return (
                    f"{item.id} substitution is {expected}, "
                    f"which does not match answer.sympy={item.answer.sympy!r}"
                )
            return None
        if kind == "solution_count":
            equation = spec.equation or spec.expr
            if not equation:
                return f"{item.id} solution_count verify needs equation"
            label = solution_count_label(equation)
            if item.answer.sympy != label:
                return (
                    f"{item.id} solution_count is {label}, "
                    f"which does not match answer.sympy={item.answer.sympy!r}"
                )
            return None
        expr = spec.expr or spec.equation
        if not expr:
            return f"{item.id} equation verify needs expr"
        solved = solve_extracted(expr, unknown=spec.unknown)
        if not _matches_answer(solved, item.answer.sympy):
            return (
                f"{item.id} verify solves to {solved}, "
                f"which does not match answer.sympy={item.answer.sympy!r}"
            )
        return None
    except (ParseError, Unsolvable) as exc:
        return f"{item.id} verify is not machine-solvable: {exc}"
