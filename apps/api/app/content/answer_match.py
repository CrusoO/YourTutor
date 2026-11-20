"""How a typed response is compared with an authored value. Pure, no I/O.

One place for "is this the same value?" so the diagnosis engine and the reason model read answers
the same way: `x = 4`, `4`, `4.0` and `8/2` are one value; spaces and case never matter.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.content.math_parse import ParseError, expressions_equivalent, parse_math

_VAR_PREFIX = re.compile(r"^\s*[a-zA-Z]\s*=\s*(?!=)")


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def strip_variable(text: str) -> str:
    """`x = 4` as `4`: the answer without a leading `name =`."""
    return _VAR_PREFIX.sub("", text.strip())


def value_of(text: str) -> float | None:
    """A response as a number, accepting `x = 4` style answers. None when it is not one."""
    stripped = strip_variable(text)
    if not stripped:
        return None
    try:
        return float(parse_math(stripped).evalf())
    except (ParseError, TypeError, ValueError):
        return None


def same_value(left: str, right: str) -> bool:
    a = strip_variable(left)
    b = strip_variable(right)
    if not a or not b:
        return False
    if squash(a) == squash(b):
        return True
    return expressions_equivalent(a, b)


def matches_any(response: str, values: Iterable[object]) -> str | None:
    """The first authored value the response equals, or None."""
    for candidate in values:
        if same_value(response, str(candidate)):
            return str(candidate)
    return None
