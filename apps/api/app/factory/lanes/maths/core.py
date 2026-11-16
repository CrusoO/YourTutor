# ruff: noqa: E501
"""Shared plumbing for the Class 10 maths lane: what a family returns, methods, kernel witnesses.

A FAMILY is one question model (for example "nth term of an AP"). It builds an item BACKWARD from
a parameter tuple (the answer is chosen first), so numbers are nice and the answer is unique. The
lane turns the family's `Built` record into an ItemContext for the factory pipeline.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from app.factory.kernel.exact import rational_sqrt

SQ = "²"
DEG = "°"
SQRT = "√"
MINUS = "-"


class IllPosed(Exception):  # noqa: N818 - a refusal reason, not an error
    """The parameter tuple does not make a good item. The message is the counted reason."""


@dataclass
class Built:
    spec: dict[str, Any]
    answer: dict[str, Any]
    witness: dict[str, Any]
    stem: str
    steps: list[str]
    hints: list[str]
    # (misconception id, answer record, option text), in priority order; the lane takes the first
    # three whose records and texts differ from the key and from each other.
    wrong: list[tuple[str, dict[str, Any], str]]
    key_text: str
    tokens: list[str]
    difficulty: float
    role: str
    prediction: str
    methods: list[Any]
    slug: str
    tags: list[str] = field(default_factory=list)


class FnMethod:
    """An independent method: a pure function of the spec. Deep-copyable (fault injection)."""

    def __init__(
        self, id: str, group: str, technique: str, fn: Callable[[Mapping[str, Any]], Any]
    ) -> None:  # noqa: A002
        self.id, self.version, self.independence_group, self.technique = id, "1", group, technique
        self.fn = fn

    def solve(self, spec: Mapping[str, Any]) -> Any:
        return self.fn(spec)


class Family:
    id = ""
    version = "1"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------- small helpers


def fstr(x: Any) -> str:
    """A number as a lowest-terms string: '3', '-3/2'."""
    return str(Fraction(x))


def fnum(x: Any) -> str:
    """A number for reading in a stem: '3', '-3/2'."""
    return fstr(x)


def poly_text(coeffs: list[Any], var: str = "x") -> str:
    """Coefficients lowest power first -> '2x² - 4x - 30'. Zero polynomial -> '0'."""
    out = ""
    for power in range(len(coeffs) - 1, -1, -1):
        c = Fraction(coeffs[power])
        if c == 0:
            continue
        mag = abs(c)
        sym = "" if power == 0 else (var if power == 1 else var + SQ)
        body = (str(mag) if (mag != 1 or power == 0) else "") + sym
        if not out:
            out = ("-" if c < 0 else "") + body
        else:
            out += (" - " if c < 0 else " + ") + body
    return out or "0"


def as_int_or_str(x: Any) -> Any:
    f = Fraction(x)
    return int(f) if f.denominator == 1 else str(f)


def quad_kernel(c: Fraction, b: Fraction, a: Fraction) -> tuple[dict[str, Any], dict[str, Any]]:
    """Kernel pieces for a x^2 + b x + c = 0: (answer part, witness). Exact, rational only."""
    disc = b * b - 4 * a * c
    if disc == 0:
        r = -b / (2 * a)
        return (
            {"roots": [fstr(r)], "count": 1},
            {"split": {"lead": fstr(a), "roots": [[fstr(r), 2]]}},
        )
    root = rational_sqrt(disc)
    if disc > 0 and root is not None:
        r1, r2 = sorted([(-b - root) / (2 * a), (-b + root) / (2 * a)])
        return (
            {"roots": [fstr(r1), fstr(r2)], "count": 2},
            {"split": {"lead": fstr(a), "roots": [[fstr(r1), 1], [fstr(r2), 1]]}},
        )
    return {"count": 0 if disc < 0 else 2}, {"discriminant": fstr(disc)}


def distinct_wrong(
    key: dict[str, Any],
    key_text: str,
    wrong: list[tuple[str, dict[str, Any], str]],
    chash: Callable[[Any], str],
) -> list[tuple[str, dict[str, Any], str]]:
    """First three candidates that differ from the key and from each other (record and text)."""
    seen_rec, seen_txt = {chash(key)}, {key_text}
    picked: list[tuple[str, dict[str, Any], str]] = []
    for mc, rec, text in wrong:
        h = chash(rec)
        if h in seen_rec or text in seen_txt:
            continue
        seen_rec.add(h)
        seen_txt.add(text)
        picked.append((mc, rec, text))
        if len(picked) == 3:
            break
    return picked


def clamp_difficulty(base: float, *magnitudes: Any, steps: int = 0) -> float:
    """Difficulty prior from solution-trace features: more steps and bigger numbers are harder."""
    size = sum(len(str(abs(int(Fraction(m))))) - 1 for m in magnitudes if m is not None)
    return round(min(0.95, max(0.05, base + 0.03 * steps + 0.02 * size)), 3)


def pick(variants: list[str], p: Mapping[str, Any]) -> str:
    """Deterministic variant of a phrase from the parameters (never random)."""
    key = int(hashlib.sha256(repr(sorted(p.items())).encode()).hexdigest()[:8], 16)
    return variants[key % len(variants)]


_LETTER = re.compile(r"(?<![A-Za-z])[abcd](?![A-Za-z])")


def hint_problems(stem: str, hints: list[str]) -> str | None:
    """Lane-side lint on hints, so a bad text is a counted refusal and never a silent pass."""
    if len(hints) != 3:
        return "needs_three_hints"
    for hint in hints[:2]:
        if _LETTER.search(hint):
            return "hint_has_option_letter_word"
    if "=" not in stem:
        for hint in hints:
            low = hint.lower()
            if "equation" in low or "both sides" in low:
                return "hint_uses_equation_words_without_equals"
    return None
