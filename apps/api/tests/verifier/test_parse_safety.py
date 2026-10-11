"""Hardening: student and author text can never reach Python built-ins through the parser."""

from __future__ import annotations

import time
import warnings

import pytest
import sympy

from app.content.math_parse import ParseError, parse_math

HOSTILE = [
    "__import__('os')",
    "__class__",
    "x.__class__",
    "().__class__.__bases__",
    "(1).real",
    "x.func",
    "abs(-3)",
    "eval(1)",
    "exec(1)",
    "open(1)",
    "print(1)",
    "exit()",
    "quit()",
    "input()",
    "help()",
    "breakpoint()",
    "globals()",
    "locals()",
    "getattr(1,2)",
    "lambda x: x",
    "Integer(5)",
    "Symbol",
    "1; 2",
    "[1]",
    "{1}",
    "'a'",
    '"a"',
    "x = y = 1",
    "1 if 1 else 2",
]


@pytest.mark.parametrize("text", HOSTILE)
def test_hostile_text_is_rejected_as_a_parse_error(text: str) -> None:
    with pytest.raises(ParseError):
        parse_math(text)


def test_very_long_input_is_refused_before_any_parsing() -> None:
    with pytest.raises(ParseError, match="too long"):
        parse_math("1+" * 200 + "1")


def test_a_parenthesis_bomb_is_refused_quickly() -> None:
    start = time.perf_counter()
    for text in ("(" * 60 + "1" + ")" * 60, "((((((((((1))))))))))", "(1" * 30):
        with pytest.raises(ParseError):
            parse_math(text)
    assert time.perf_counter() - start < 2


def test_builtins_are_not_reachable_even_if_the_allowlist_lets_the_name_through() -> None:
    from sympy.parsing.sympy_parser import parse_expr

    with pytest.raises(NameError):
        parse_expr("abs", local_dict={}, global_dict={"__builtins__": {}}, transformations=())


def test_ordinary_maths_still_parses() -> None:
    x = sympy.Symbol("x")
    assert parse_math("2x + 3") == 2 * x + 3
    assert parse_math("(x+1)^2") == (x + 1) ** 2
    assert float(parse_math("3/4")) == 0.75
    assert parse_math("-5") == -5
    assert parse_math("y = 2(3)") == 6


def test_odd_text_does_not_emit_a_syntax_warning() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", SyntaxWarning)
        for text in ("2(3)", "3(4)(5)", "x is 1.5"):
            try:
                parse_math(text)
            except ParseError:
                pass
