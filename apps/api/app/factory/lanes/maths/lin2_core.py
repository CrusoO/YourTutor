# ruff: noqa: E501
"""Shared plumbing for the Pair of Linear Equations lane (Class 10 maths, chapter 3).

Every family builds BACKWARD from a chosen solution, so the numbers are clean. Each item carries a
kernel-checkable spec (a 2x2 linear system with a unique solution, or a one-unknown polynomial
for the k and type items) and three independent lane methods that read only the structured
`spec["model"]`. `make` throws a tuple away (IllPosed) when those methods disagree, so a bad
tuple is a counted skip and never a stamped item.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from fractions import Fraction
from typing import Any

from app.factory.kernel.exact import chash
from app.factory.lanes.maths.core import Built, FnMethod, IllPosed, fstr

F = Fraction
Rows = list[list[Any]]


# ---------------------------------------------------------------- text


def coef_text(c: Fraction | int, var: str, first: bool) -> str:
    c = F(c)
    mag = abs(c)
    body = (str(mag) if mag != 1 else "") + var
    if first:
        return ("-" if c < 0 else "") + body
    return (" - " if c < 0 else " + ") + body


def lin_text(a: Any, b: Any, c: Any, xs: str = "x", ys: str = "y") -> str:
    """a x + b y = c, written the way a student reads it. Zero terms are left out."""
    out = ""
    for coef, var in ((a, xs), (b, ys)):
        if F(coef) != 0:
            out += coef_text(coef, var, not out)
    return f"{out or '0'} = {fstr(c)}"


def std_zero_text(a: Any, b: Any, c: Any) -> str:
    """a x + b y + c = 0."""
    out = coef_text(a, "x", True) + coef_text(b, "y", False)
    k = F(c)
    if k != 0:
        out += (" - " if k < 0 else " + ") + str(abs(k))
    return out + " = 0"


def slope_text(m: Any, n: Any) -> str:
    """y = m x + n."""
    out = coef_text(m, "x", True)
    k = F(n)
    if k != 0:
        out += (" - " if k < 0 else " + ") + str(abs(k))
    return "y = " + out


def pt(x: Any, y: Any) -> str:
    return f"({fstr(x)}, {fstr(y)})"


def slug(*parts: Any) -> str:
    return "_".join(str(x).replace("-", "m").replace("/", "d").replace(" ", "") for x in parts)


# ---------------------------------------------------------------- answers


def pair_rec(
    x: Any, y: Any, text: str | None = None, names: tuple[str, str] = ("x", "y")
) -> dict[str, Any]:
    return {
        "values": {names[0]: fstr(x), names[1]: fstr(y)},
        "value": text if text is not None else f"x = {fstr(x)}, y = {fstr(y)}",
    }


def nice(v: Fraction, *, positive: bool = False, maxden: int = 12, limit: int = 400) -> bool:
    """A wrong value worth showing a student: small denominator, not absurdly large."""
    if positive and v <= 0:
        return False
    return v.denominator <= maxden and abs(v.numerator) <= limit * v.denominator


# ---------------------------------------------------------------- methods


def memo(fn: Callable[[Mapping[str, Any]], Any]) -> Callable[[Mapping[str, Any]], Any]:
    """Cache a method by the structured model (methods read nothing else)."""
    cache: dict[str, tuple[bool, Any]] = {}

    def run(spec: Mapping[str, Any]) -> Any:
        key = json.dumps(spec["model"], sort_keys=True)
        if key not in cache:
            try:
                cache[key] = (True, fn(spec))
            except Exception as exc:  # noqa: BLE001 - replayed on every call, fail closed
                cache[key] = (False, f"{type(exc).__name__}: {exc}")
        ok, val = cache[key]
        if not ok:
            raise ValueError(val)
        return copy.deepcopy(val)

    return run


def method(
    mid: str, group: str, technique: str, fn: Callable[[Mapping[str, Any]], Any]
) -> FnMethod:
    return FnMethod(mid, group, technique, memo(fn))


def agree(spec: dict[str, Any], methods: list[FnMethod], answer: dict[str, Any]) -> None:
    """Throw the tuple away unless every independent method reproduces the answer exactly."""
    for m in methods:
        try:
            got = m.solve(spec)
        except Exception as exc:  # noqa: BLE001
            raise IllPosed("methods_disagree:method_error") from exc
        if chash(got) != chash(answer):
            raise IllPosed("methods_disagree")


def system_spec(
    rows: Rows, model: dict[str, Any], names: tuple[str, str] = ("x", "y")
) -> dict[str, Any]:
    return {
        "domain": "algebra",
        "kind": "linear_system",
        "variables": list(names),
        "equations": [{"coeffs": [fstr(a), fstr(b)], "const": fstr(c)} for a, b, c in rows],
        "model": model,
    }


def make(
    tpl: Mapping[str, Any],
    *,
    spec: dict[str, Any],
    key: dict[str, Any],
    witness: dict[str, Any],
    key_text: str,
    wrong: list[tuple[str, dict[str, Any], str]],
    stem: str,
    steps: list[str],
    hints: list[str],
    methods: list[FnMethod],
    difficulty: float,
    role: str,
    prediction: str,
    slug_text: str,
    nsteps: int,
    tokens: list[str] | None = None,
) -> Built:
    agree(spec, methods, key)
    return Built(
        spec=spec,
        answer=key,
        witness=witness,
        stem=stem,
        steps=steps,
        hints=hints,
        wrong=wrong,
        key_text=key_text,
        tokens=tokens or [key_text],
        difficulty=difficulty,
        role=role,
        prediction=prediction,
        methods=methods,
        slug=slug_text,
        tags=[f"marks:{tpl['form']['marks']}", f"steps:{nsteps}"],
    )
