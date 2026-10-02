"""Allowlist verifier — never raw sympy.sympify. Used online and on sync."""

from __future__ import annotations

from typing import Any

from app.content.leak import hint_leaks_answer
from app.content.math_parse import ParseError, expressions_equivalent, normalize, parse_math
from app.content.stem_solve import (
    Unsolvable,
    solution_count_label,
    solve_extracted,
    substitution_holds,
)


def leak_check(hint_text: str, answer: str, *, level: int) -> bool:
    """True when a retry hint (level 1–2) leaks the answer. Level 3 is not checked."""
    if level >= 3:
        return False
    if hint_leaks_answer(hint_text, answer):
        return True
    return False


def verify_response(
    response: str,
    *,
    answer_sympy: str,
    accept: list[str] | None = None,
    item_type: str = "expression",
    verify: str | dict[str, Any] | None = None,
    options: list[dict[str, Any]] | None = None,
) -> bool:
    """Return whether `response` matches the authored answer. Ignores any client flag."""
    from app.observe.otel import span

    with span("verifier", component="verifier"):
        return _verify_response(
            response,
            answer_sympy=answer_sympy,
            accept=accept,
            item_type=item_type,
            verify=verify,
            options=options,
        )


def _verify_response(
    response: str,
    *,
    answer_sympy: str,
    accept: list[str] | None = None,
    item_type: str = "expression",
    verify: str | dict[str, Any] | None = None,
    options: list[dict[str, Any]] | None = None,
) -> bool:
    text = normalize(response)
    expected = normalize(answer_sympy)
    accepted = [normalize(a) for a in (accept or [])]
    if text == expected or text in accepted:
        return True
    if item_type == "mcq":
        return _mcq_match(text, expected, options or [])
    if verify:
        try:
            if _verify_spec(text, expected, verify):
                return True
        except (ParseError, Unsolvable):
            return False
    try:
        if expressions_equivalent(text, answer_sympy):
            return True
        if "=" in text:
            rhs = text.rsplit("=", 1)[-1]
            if expressions_equivalent(rhs, answer_sympy):
                return True
        parse_math(text)
    except ParseError:
        return False
    return False


def _mcq_match(text: str, expected: str, options: list[dict[str, Any]]) -> bool:
    if text == expected:
        return True
    for option in options:
        oid = normalize(str(option.get("id", "")))
        label = normalize(str(option.get("en", "")))
        if text in {oid, label} and oid == expected:
            return True
    return False


def _verify_spec(text: str, expected: str, verify: str | dict[str, Any]) -> bool:
    if isinstance(verify, str):
        solved = solve_extracted(verify)
        return expressions_equivalent(str(solved), expected) and expressions_equivalent(
            text, expected
        )
    kind = verify.get("kind", "equation")
    if kind == "substitution":
        equation = verify.get("equation") or ""
        value = verify.get("value")
        if not equation or value is None:
            return False
        holds = substitution_holds(equation, str(value))
        label = "yes" if holds else "no"
        return text in {label, "1" if holds else "0"} and expected == label
    if kind == "solution_count":
        equation = verify.get("equation") or verify.get("expr") or ""
        label = solution_count_label(equation)
        return text == label and expected == label
    expr = verify.get("expr") or verify.get("equation")
    if not expr:
        return False
    solved = solve_extracted(str(expr), unknown=verify.get("unknown"))
    return expressions_equivalent(str(solved), expected) and expressions_equivalent(
        text, expected
    )
