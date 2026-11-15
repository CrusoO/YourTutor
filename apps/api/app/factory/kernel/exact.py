"""Exact arithmetic, canonical JSON and hashing for the trusted kernel (stdlib only).

Floats are refused everywhere: a number is an int, a Fraction or a decimal/rational string.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from fractions import Fraction
from typing import Any

_DECIMAL = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d{1,3})?$")
_RATIO = re.compile(r"^[+-]?\d{1,40}/\d{1,40}$")
_MAX_CHARS = 60


class Reject(Exception):  # noqa: N818 - a verdict, not an error
    """The kernel refuses. Always carries a stable machine code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class Deadline:
    """Cooperative time budget. Loops call check(); expiry rejects (fail closed)."""

    def __init__(self, seconds: float = 30) -> None:
        self._end = time.monotonic() + seconds

    def check(self) -> None:
        if time.monotonic() > self._end:
            raise Reject("timeout")


def frac(value: Any) -> Fraction:
    """Exact rational from an int, Fraction or decimal/ratio string. Floats and bools reject."""
    if isinstance(value, bool | float):
        raise Reject("not_exact", f"{type(value).__name__} is not an exact number")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        text = value.strip()
        if len(text) <= _MAX_CHARS and (_DECIMAL.match(text) or _RATIO.match(text)):
            try:
                return Fraction(text)
            except (ValueError, ZeroDivisionError) as exc:
                raise Reject("not_a_number", repr(value)) from exc
    raise Reject("not_a_number", repr(value)[:40])


def is_number_text(value: Any) -> bool:
    try:
        frac(value)
    except Reject:
        return False
    return True


def canon(value: Any) -> Any:
    """Canonical JSON-able form: numbers as lowest-terms strings, other strings unchanged."""
    if isinstance(value, dict):
        return {str(k): canon(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [canon(v) for v in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, float):
        raise Reject("not_exact", "float in kernel data")
    if isinstance(value, int | Fraction) or (isinstance(value, str) and is_number_text(value)):
        return str(frac(value))
    if isinstance(value, str):
        return value
    raise Reject("not_json", type(value).__name__)


def canonical_json(value: Any) -> str:
    return json.dumps(canon(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def chash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def round_half_up(value: Fraction, dp: int) -> Fraction:
    if not 0 <= dp <= 12:
        raise Reject("bad_dp", str(dp))
    scale = 10**dp
    rounded = (abs(value) * scale * 2 + 1) // 2
    return Fraction(rounded if value >= 0 else -rounded, scale)


def answer_matches(exact: Fraction, claimed: Any, dp: Any = None) -> bool:
    """Claimed value equals the exact one, or its rounding at `dp` decimal places."""
    claimed_value = frac(claimed)
    if dp is None:
        return claimed_value == exact
    return claimed_value == round_half_up(exact, int(dp))


def rational_sqrt(value: Fraction) -> Fraction | None:
    if value < 0:
        return None
    n, d = math.isqrt(value.numerator), math.isqrt(value.denominator)
    if n * n == value.numerator and d * d == value.denominator:
        return Fraction(n, d)
    return None
