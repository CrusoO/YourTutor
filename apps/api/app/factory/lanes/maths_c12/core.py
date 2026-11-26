# ruff: noqa: E501
"""Shared plumbing for the Class 12 maths lane.

A MODEL is one question type. It is registered with `@model(...)` (skill, chapter, parameter box,
marks, allowed technique) and builds an item BACKWARD from a parameter tuple: the answer is chosen
first, so numbers are nice and the key is unique. The builder calls `case(...)`, which

* encodes the answer for the kernel (a scalar becomes the root of `u - v = 0`; a vector or matrix
  becomes a linear system with one equation per component, or the real system for the "solve a
  system" model),
* wraps the independent METHODS (pure functions of the structured model stored in the spec),
* lays out the named wrong options.

The kernel proves only that the stored answer satisfies the stored relation. The real checking is
done by the methods: each one recomputes the answer from the structured model by a different
algorithm or library, and a disagreement is a rejection (never a vote).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from app.factory.lanes.maths.core import (
    Built,
    Family,
    FnMethod,
    IllPosed,
    clamp_difficulty,
    pick,
)

F = Fraction
Vals = tuple[Fraction, ...]
SUPERSCRIPT = "⁰¹²³⁴⁵⁶⁷⁸⁹"
PI = "π"

__all__ = [
    "F", "IllPosed", "Built", "pick", "clamp_difficulty", "model", "case", "MODELS", "FAMILIES",
    "fr", "fs", "poly_text", "mat_text", "vec_text", "sup", "paren", "hints3", "isqrt_exact",
    "Spec", "norm", "encode",
]  # fmt: skip


def fr(x: Any) -> str:
    """A number as lowest-terms text: '3', '-3/2'."""
    return str(Fraction(x))


fs = fr


def sup(n: int) -> str:
    return "".join(SUPERSCRIPT[int(c)] for c in str(n))


def paren(x: Any) -> str:
    text = fr(x)
    return f"({text})" if (Fraction(x) < 0 or "/" in text) else text


def poly_text(coeffs: Sequence[Any], var: str = "x") -> str:
    """Coefficients lowest power first -> '2x² - 4x - 30'."""
    out = ""
    for power in range(len(coeffs) - 1, -1, -1):
        c = Fraction(coeffs[power])
        if c == 0:
            continue
        mag = abs(c)
        mtxt = (
            "" if (mag == 1 and power > 0) else (str(mag) if mag.denominator == 1 else f"({mag})")
        )
        body = mtxt + ("" if power == 0 else var + ("" if power == 1 else sup(power)))
        out = (
            (("-" if c < 0 else "") + body) if not out else out + (" - " if c < 0 else " + ") + body
        )
    return out or "0"


def mat_text(rows: Sequence[Sequence[Any]]) -> str:
    return "[" + ", ".join("[" + ", ".join(fr(x) for x in row) + "]" for row in rows) + "]"


def vec_text(v: Sequence[Any]) -> str:
    """A vector as '2i - j + 3k' (a zero vector is '0')."""
    out = ""
    for c, unit in zip(v, "ijk", strict=False):
        c = Fraction(c)
        if c == 0:
            continue
        mag = abs(c)
        body = ("" if mag == 1 else fr(mag)) + unit
        out = (
            (("-" if c < 0 else "") + body) if not out else out + (" - " if c < 0 else " + ") + body
        )
    return out or "0"


def isqrt_exact(x: Fraction) -> Fraction | None:
    """Exact rational square root of a non-negative Fraction, or None."""
    if x < 0:
        return None
    n, d = math.isqrt(x.numerator), math.isqrt(x.denominator)
    return Fraction(n, d) if n * n == x.numerator and d * d == x.denominator else None


def norm(v: Any) -> Vals:
    if isinstance(v, tuple | list):
        return tuple(Fraction(x) for x in v)
    return (Fraction(v),)


def encode(names: Sequence[str], vals: Vals) -> dict[str, Any]:
    """The kernel answer record for a value tuple."""
    if len(vals) == 1:
        return {"roots": [fr(vals[0])], "count": 1}
    return {"values": {n: fr(v) for n, v in zip(names, vals, strict=True)}}


def hints3(p: Mapping[str, Any], nudges: Sequence[str], method: str, full: str) -> list[str]:
    return [pick(list(nudges), p), method, full]


# ---------------------------------------------------------------- registry


@dataclass
class Spec:
    short: str
    chapter: str
    title: str
    prereq: list[str]
    marks: int
    box: dict[str, Any]
    technique: str
    forbidden: list[str]
    build: Callable[[Mapping[str, Any]], Built]
    version: str

    @property
    def skill_id(self) -> str:
        return "MATH.C12." + self.short

    @property
    def template_id(self) -> str:
        return "TPL.C12." + self.short


MODELS: dict[str, Spec] = {}
FAMILIES: dict[str, Family] = {}
DEFAULT_FORBIDDEN = ["proof", "graph_reading", "diagram", "free_text"]


class _ModelFamily(Family):
    def __init__(self, spec: Spec) -> None:
        self.id, self.version, self.spec = spec.short, spec.version, spec

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        built = self.spec.build(p)
        built.tags = [f"marks:{tpl['form']['marks']}", *built.tags]
        return built


def model(
    short: str,
    *,
    chapter: str,
    title: str,
    prereq: list[str],
    marks: int,
    box: dict[str, Any],
    technique: str,
    version: str = "1",
    forbidden: list[str] | None = None,
) -> Callable[[Callable[[Mapping[str, Any]], Built]], Callable[[Mapping[str, Any]], Built]]:
    def deco(fn: Callable[[Mapping[str, Any]], Built]) -> Callable[[Mapping[str, Any]], Built]:
        spec = Spec(short, chapter, title, prereq, marks, box, technique,
                    forbidden or DEFAULT_FORBIDDEN, fn, version)  # fmt: skip
        MODELS[short] = spec
        FAMILIES[short] = _ModelFamily(spec)
        return fn

    return deco


def _wrap(fn: Callable[[Mapping[str, Any]], Any]) -> Callable[[Mapping[str, Any]], Any]:
    def run(spec: Mapping[str, Any]) -> Any:
        md = spec["model"]
        return encode(md["names"], norm(fn(md)))

    return run


def case(
    *,
    fam: str,
    md: Mapping[str, Any],
    names: Sequence[str],
    value: Any,
    stem: str,
    steps: list[str],
    hints: list[str],
    wrong: Sequence[tuple[str, Any]],
    methods: Sequence[tuple[str, str, str, Callable[[Mapping[str, Any]], Any]]],
    base: float,
    role: str,
    prediction: str,
    slug: str,
    fmt: Callable[[Vals], str] | None = None,
    kernel: Mapping[str, Any] | None = None,
    tokens: Sequence[str] | None = None,
    mags: Sequence[Any] = (),
    nsteps: int = 3,
) -> Built:
    vals = norm(value)
    show = fmt or (lambda v: fr(v[0]))
    model_md = {"family": fam, "names": list(names), **md}
    answer = encode(names, vals)
    if len(vals) == 1:
        spec: dict[str, Any] = {
            "domain": "algebra", "kind": "polynomial", "lhs": [fr(-vals[0]), 1], "model": model_md,
        }  # fmt: skip
        witness: dict[str, Any] = {"split": {"lead": 1, "roots": [[fr(vals[0]), 1]]}}
    else:
        names_l = list(names)
        eqs = (
            [dict(e) for e in kernel["equations"]]
            if kernel
            else [
                {"coeffs": [1 if j == i else 0 for j in range(len(vals))], "const": fr(v)}
                for i, v in enumerate(vals)
            ]
        )
        spec = {
            "domain": "algebra", "kind": "linear_system", "variables": names_l,
            "equations": eqs, "model": model_md,
        }  # fmt: skip
        witness = {"values": {n: fr(v) for n, v in zip(names_l, vals, strict=True)}}
    key_text = show(vals)
    wrong_out = []
    for mc, wv in wrong:
        wvals = norm(wv)
        if len(wvals) != len(vals):
            continue
        wrong_out.append((mc, encode(names, wvals), show(wvals)))
    toks = list(tokens) if tokens is not None else [key_text]
    return Built(
        spec=spec, answer=answer, witness=witness, stem=stem, steps=steps, hints=hints,
        wrong=wrong_out, key_text=key_text, tokens=toks,
        difficulty=clamp_difficulty(base, *mags, steps=nsteps), role=role, prediction=prediction,
        methods=[FnMethod(i, g, t, _wrap(f)) for i, g, t, f in methods],
        slug=slug, tags=[f"steps:{nsteps}"],
    )  # fmt: skip
