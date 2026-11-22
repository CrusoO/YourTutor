"""Pure step checker for one equation with one unknown (slice 1: Class 10 quadratics).

Given the question's equation and the student's lines, say for each line whether it follows from
the last line we can trust:

- ``ok``          same solution set as the last trusted line (or an expression algebraically equal
                  to it). Expanding, factoring, moving terms and "x = 2 or x = 5" all land here.
- ``wrong_step``  read fine, but it does not follow (a lost root, a sign flip, a wrong expansion).
- ``unreadable``  we could not read it. It costs nothing, is never counted as a mistake, and no
                  line after it is judged (they come back ``skipped``): we do not know what the
                  chain looks like any more.
- ``skipped``     blank, or after an unreadable line.

A wrong line does not become the new trusted line, so a later corrected line is judged against the
last good one and is not marked wrong for disagreeing with the mistake.

Input goes only through the allowlist parser (``math_parse.parse_math``), never ``eval`` or
``sympify``. No I/O, no clock, no randomness: the same input gives the same answer. A final-answer
verdict is worked out from the last line alone with the existing ``verify_response``, so a right
answer reached by a path we cannot read is still recognised as right.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import sympy

from app.content.math_parse import ParseError, parse_math
from app.verifier.check import verify_response

OK = "ok"
WRONG_STEP = "wrong_step"
UNREADABLE = "unreadable"
SKIPPED = "skipped"

V_CORRECT = "correct"
V_WRONG = "wrong"
V_NOT_FINAL = "not_final"
V_UNREADABLE = "unreadable"
V_NONE = "none"
V_UNCHECKED = "unchecked"  # the question is not one this checker can decide

# The authored misconception that names "read the root straight off the bracket, wrong sign"
# (content/cbse/10/maths/misconceptions/mc_quad_factor_sign_read.yaml). No other key is invented.
HINT_SIGN_READ = "MC.QUAD.FACTOR_SIGN_READ"

MAX_LINES = 12
MAX_LINE_CHARS = 160

_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−﹣－"), "-")
_PRE = {"²": "^2", "³": "^3", "×": "*", "·": "*", "÷": "/", "＝": "="}
_SPLIT = re.compile(r"\bor\b|\band\b|;|,(?=\s*[A-Za-z]\s*=)", re.IGNORECASE)
_NO_ROOTS = re.compile(r"^(there (are|is) )?no (real )?(roots?|solutions?)\.?$", re.IGNORECASE)
# 9^9^9, 2^(9^9) or x^99999 would make Python build an enormous number before any check can run.
_POWER_BOMB = re.compile(r"\^\s*\(|\^\s*[+-]?\s*\d{2,}|\^\s*[0-9A-Za-z]+\s*\^")


class _Unreadable(Exception):
    pass


@dataclass(frozen=True)
class LineResult:
    state: str
    hint_key: str | None = None


@dataclass(frozen=True)
class StepReport:
    supported: bool
    lines: tuple[LineResult, ...]
    verdict: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "supported": self.supported,
            "lines": [
                {"state": r.state, **({"hint_key": r.hint_key} if r.hint_key else {})}
                for r in self.lines
            ],
            "verdict": self.verdict,
        }


@dataclass(frozen=True)
class _Parsed:
    kind: str  # "eqs" (one or more equations joined by "or"), "expr", "no_real"
    exprs: tuple[sympy.Expr, ...] = ()  # eqs: left minus right; expr: the expression itself
    sides: tuple[tuple[sympy.Expr, sympy.Expr], ...] = ()  # eqs: (left, right)


# --------------------------------------------------------------------------- parsing


def _clean(text: str) -> str:
    s = text.translate(_DASHES)
    for old, new in _PRE.items():
        s = s.replace(old, new)
    s = re.sub(r"(\d)\s+([A-Za-z(])", r"\1*\2", s)  # "2 x" and "3 (x+1)" are products
    s = re.sub(r"\)\s*([A-Za-z0-9])", r")*\1", s)  # "(x+1)x" and "(x+1)2"
    return s.strip()


def _num(value: sympy.Expr) -> sympy.Expr:
    if value.has(sympy.Float):
        return sympy.nsimplify(value, rational=True)
    return value


def _side(text: str, x: sympy.Symbol) -> sympy.Expr:
    text = text.strip()
    if not text or _POWER_BOMB.search(text):
        raise _Unreadable
    try:
        value = _num(parse_math(text))
    except (ParseError, ValueError, TypeError, ZeroDivisionError, RecursionError) as exc:
        raise _Unreadable from exc
    if value.has(sympy.zoo, sympy.nan, sympy.oo, -sympy.oo) or not value.free_symbols <= {x}:
        raise _Unreadable
    return value


def _part(text: str, x: sympy.Symbol, *, multi: bool) -> tuple[sympy.Expr, sympy.Expr]:
    if text.count("=") > 1:
        raise _Unreadable  # chains like a = b = c are not read in slice 1
    if "=" in text:
        left, right = text.split("=", 1)
        return _side(left, x), _side(right, x)
    value = _side(text, x)
    if multi and not value.free_symbols:  # "x = 2 or 5": a bare number means x = number
        return x, value
    raise _Unreadable


def _parse_line(raw: str, x: sympy.Symbol) -> _Parsed:
    if len(raw) > MAX_LINE_CHARS:
        raise _Unreadable
    text = raw.translate(_DASHES).strip()
    if not text:
        raise _Unreadable
    if _NO_ROOTS.match(text):
        return _Parsed("no_real")
    # split on "or" before cleaning: "2 or" must not be read as the product 2*or
    pieces = [_clean(p) for p in _SPLIT.split(text) if p.strip()]
    if not pieces or len(pieces) > 4:
        raise _Unreadable
    if len(pieces) == 1 and "=" not in pieces[0]:
        value = _side(pieces[0], x)
        return _Parsed("expr", exprs=(value,))
    expanded: list[str] = []
    for piece in pieces:
        if "±" in piece:
            expanded += [piece.replace("±", "+"), piece.replace("±", "-")]
        else:
            expanded.append(piece)
    multi = len(expanded) > 1
    sides = tuple(_part(p, x, multi=multi) for p in expanded)
    return _Parsed("eqs", exprs=tuple(left - right for left, right in sides), sides=sides)


# --------------------------------------------------------------------------- mathematics


def _solutions(parsed: _Parsed, x: sympy.Symbol, domain: sympy.Set) -> sympy.Set:
    out: sympy.Set = sympy.EmptySet
    for expr in parsed.exprs:
        try:
            part = sympy.solveset(sympy.simplify(expr), x, domain)
        except (NotImplementedError, ValueError, TypeError, RecursionError) as exc:
            raise _Unreadable from exc
        out = out.union(part)
    return out


def _same_elements(a: sympy.Expr, b: sympy.Expr) -> bool:
    try:
        return bool(sympy.simplify(a - b) == 0)
    except (TypeError, ValueError, RecursionError):
        return False


def _sets_equal(a: sympy.Set, b: sympy.Set) -> bool:
    if isinstance(a, sympy.FiniteSet) and isinstance(b, sympy.FiniteSet):
        ea, eb = list(a), list(b)
        return len(ea) == len(eb) and all(any(_same_elements(p, q) for q in eb) for p in ea)
    if a == b:
        return True
    try:
        return a.symmetric_difference(b) == sympy.EmptySet
    except (NotImplementedError, TypeError, ValueError) as exc:
        raise _Unreadable from exc


def _algebraically_equal(a: sympy.Expr, b: sympy.Expr) -> bool:
    return _same_elements(sympy.expand(a), sympy.expand(b))


def _follows(line: _Parsed, base: _Parsed, x: sympy.Symbol) -> bool:
    if line.kind == "no_real":
        return _solutions(base, x, sympy.S.Reals) == sympy.EmptySet
    if base.kind == "no_real":
        raise _Unreadable
    if line.kind == "expr":
        if base.kind != "eqs" or len(base.sides) != 1:
            return False
        left, right = base.sides[0]
        value = line.exprs[0]
        return _algebraically_equal(value, left - right) or _algebraically_equal(value, left)
    return _sets_equal(
        _solutions(line, x, sympy.S.Complexes), _solutions(base, x, sympy.S.Complexes)
    )


def _linear_factors(expr: sympy.Expr, x: sympy.Symbol) -> bool:
    for factor in sympy.Mul.make_args(expr):
        if factor.is_Pow and factor.exp.is_Integer and factor.exp > 0:
            factor = factor.base
        try:
            if sympy.Poly(factor, x).degree() > 1:
                return False
        except (sympy.PolynomialError, ValueError, TypeError):
            return False
    return True


def _solved_form(parsed: _Parsed, x: sympy.Symbol) -> bool:
    return parsed.kind == "eqs" and all(
        left == x and not right.free_symbols for left, right in parsed.sides
    )


def _sign_flip_hint(line: _Parsed, base: _Parsed, x: sympy.Symbol) -> str | None:
    """The named slip only: the roots were read off the brackets (or a linear factor) with the
    sign of every root flipped. Nothing else is guessed at."""
    if base.kind != "eqs" or not _solved_form(line, x):
        return None
    if not all(_linear_factors(e, x) for e in base.exprs):
        return None
    try:
        true_roots = _solutions(base, x, sympy.S.Reals)
        if not isinstance(true_roots, sympy.FiniteSet) or not len(true_roots):
            return None
        flipped = sympy.FiniteSet(*[-r for r in true_roots])
        if flipped == true_roots:
            return None  # e.g. {0}: a flip changes nothing, so it is not this slip
        return HINT_SIGN_READ if _sets_equal(_solutions(line, x, sympy.S.Reals), flipped) else None
    except _Unreadable:
        return None


# --------------------------------------------------------------------------- the checker


def _unknown_of(question: str) -> tuple[sympy.Symbol, _Parsed] | None:
    text = _clean(question)
    if text.count("=") != 1:
        return None
    letters = sorted(set(re.findall(r"[A-Za-z]", text)))
    if len(letters) != 1:
        return None
    x = sympy.Symbol(letters[0])
    try:
        return x, _parse_line(question, x)
    except _Unreadable:
        return None


def _expected_roots(base: _Parsed, x: sympy.Symbol) -> list[str] | None:
    """The question's real roots as plain text, or None if they cannot be typed (irrational)."""
    try:
        roots = _solutions(base, x, sympy.S.Reals)
    except _Unreadable:
        return None
    if roots == sympy.EmptySet:
        return []
    if not isinstance(roots, sympy.FiniteSet):
        return None
    if not all(r.is_Rational for r in roots):
        return None
    return sorted(str(r) for r in roots)


def _final_verdict(lines: list[str], base: _Parsed, x: sympy.Symbol) -> str:
    texts = [t for t in lines if t.strip()]
    if not texts:
        return V_NONE
    expected = _expected_roots(base, x)
    if expected is None:
        return V_UNCHECKED
    try:
        last = _parse_line(texts[-1], x)
    except _Unreadable:
        return V_UNREADABLE
    if last.kind == "no_real":
        return V_CORRECT if not expected else V_WRONG
    if not _solved_form(last, x):
        return V_NOT_FINAL
    given = sorted({str(right) for _, right in last.sides})
    matched_given = all(any(verify_response(g, answer_sympy=e) for e in expected) for g in given)
    matched_expected = all(any(verify_response(g, answer_sympy=e) for g in given) for e in expected)
    return V_CORRECT if matched_given and matched_expected else V_WRONG


def check_steps(question: str, lines: list[str]) -> StepReport:
    """Classify each of the student's lines and give the final-answer verdict."""
    start = _unknown_of(question)
    if start is None or len(lines) > MAX_LINES:
        return StepReport(False, tuple(LineResult(UNREADABLE) for _ in lines), V_UNCHECKED)
    x, base = start
    results: list[LineResult] = []
    trusted = base
    blocked = False
    for raw in lines:
        if blocked or not raw.strip():
            results.append(LineResult(SKIPPED))
            continue
        try:
            line = _parse_line(raw, x)
            if _follows(line, trusted, x):
                results.append(LineResult(OK))
                if line.kind != "expr":
                    trusted = line
            else:
                results.append(LineResult(WRONG_STEP, _sign_flip_hint(line, trusted, x)))
        except _Unreadable:
            results.append(LineResult(UNREADABLE))
            blocked = True
    return StepReport(True, tuple(results), _final_verdict(lines, base, x))
