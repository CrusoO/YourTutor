"""Independent exact reference solver for the doubt solver's fixtures.

Standard library only (`fractions`, `ast`, `math`). It shares no code and no parser with the
TypeScript solver in `apps/web/lib/doubt`: expressions are read with Python's own `ast` module
and solved with the rational-root theorem and the quadratic formula on `Fraction`.

Used ONLY by the fixture-parity tests: the TypeScript answers recorded in
`packages/shared/fixtures/doubt/cases.json` must be reproduced here and, where the factory
kernel has a kind for it, re-verified by `kernel.verify`. Nothing imports this module at runtime.
"""

from __future__ import annotations

import ast
from fractions import Fraction
from math import isqrt
from typing import Any

MAX_EXPONENT = 64
MAX_DEGREE = 8


class ReferenceError(ValueError):
    """The expression is outside what the reference understands."""


# ---- Reading canonical expressions with Python's own parser ----

Poly = list[Fraction]  # lowest degree first, trailing zeros trimmed


def _trim(p: Poly) -> Poly:
    out = list(p)
    while out and out[-1] == 0:
        out.pop()
    return out


def _padd(a: Poly, b: Poly) -> Poly:
    n = max(len(a), len(b))
    return _trim(
        [
            (a[i] if i < len(a) else Fraction(0)) + (b[i] if i < len(b) else Fraction(0))
            for i in range(n)
        ]
    )


def _pscale(a: Poly, k: Fraction) -> Poly:
    return _trim([c * k for c in a])


def _pmul(a: Poly, b: Poly) -> Poly:
    if not a or not b:
        return []
    out = [Fraction(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return _trim(out)


def _ppow(a: Poly, e: int) -> Poly:
    out: Poly = [Fraction(1)]
    for _ in range(e):
        out = _pmul(out, a)
        if len(out) > MAX_DEGREE + 1:
            raise ReferenceError("degree too high")
    return out


def _source(text: str) -> ast.expr:
    try:
        return ast.parse(text.replace("^", "**").strip(), mode="eval").body
    except SyntaxError as exc:
        raise ReferenceError(f"cannot parse {text!r}") from exc


def _const(p: Poly) -> Fraction | None:
    if not p:
        return Fraction(0)
    return p[0] if len(p) == 1 else None


def _eval_poly(node: ast.expr, letter: str) -> Poly:
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    ):
        return _trim([Fraction(node.value)])
    if isinstance(node, ast.Name):
        if node.id != letter:
            raise ReferenceError(f"unexpected name {node.id}")
        return [Fraction(0), Fraction(1)]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _pscale(_eval_poly(node.operand, letter), Fraction(-1))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _eval_poly(node.operand, letter)
    if isinstance(node, ast.BinOp):
        a = _eval_poly(node.left, letter)
        b = _eval_poly(node.right, letter)
        if isinstance(node.op, ast.Add):
            return _padd(a, b)
        if isinstance(node.op, ast.Sub):
            return _padd(a, _pscale(b, Fraction(-1)))
        if isinstance(node.op, ast.Mult):
            return _pmul(a, b)
        if isinstance(node.op, ast.Div):
            k = _const(b)
            if not k:
                raise ReferenceError("division by a non-constant or zero")
            return _pscale(a, 1 / k)
        if isinstance(node.op, ast.Pow):
            e = _const(b)
            if e is None or e.denominator != 1 or abs(e) > MAX_EXPONENT:
                raise ReferenceError("bad exponent")
            n = int(e)
            base = _const(a)
            if base is not None:
                if base == 0 and n < 0:
                    raise ReferenceError("0 to a negative power")
                return _trim([base**n])
            if n < 0:
                raise ReferenceError("negative power of an unknown")
            return _ppow(a, n)
    raise ReferenceError(f"unsupported syntax {ast.dump(node)[:40]}")


def parse_poly(text: str, letter: str = "x") -> Poly:
    """Canonical explicit text (`3*x - 2`, `(x+1)**2`, `(1/2)`) as exact coefficients."""
    return _eval_poly(_source(text), letter)


def eval_arith(text: str) -> Fraction:
    p = parse_poly(text, "x")
    value = _const(p)
    if value is None:
        raise ReferenceError("not a constant")
    return value


def parse_linear(text: str) -> tuple[dict[str, Fraction], Fraction]:
    """a*x + b*y + c as ({"x": a, "y": b}, c). Each of x and y is read as the unknown in turn."""
    sub = parse_poly(text.replace("y", "(0)"), "x")
    px = parse_poly(text.replace("x", "(0)"), "y")
    c = sub[0] if sub else Fraction(0)
    a = sub[1] if len(sub) > 1 else Fraction(0)
    b = px[1] if len(px) > 1 else Fraction(0)
    if len(sub) > 2 or len(px) > 2:
        raise ReferenceError("not linear")
    return {"x": a, "y": b}, c


# ---- Exact roots ----


def _divisors(n: int) -> list[int]:
    n = abs(n)
    out = []
    for i in range(1, isqrt(n) + 1):
        if n % i == 0:
            out.append(i)
            if i * i != n:
                out.append(n // i)
    return out


def _to_ints(p: Poly) -> list[int]:
    from math import gcd, lcm

    den = 1
    for c in p:
        den = lcm(den, c.denominator)
    ints = [int(c * den) for c in p]
    g = 0
    for v in ints:
        g = gcd(g, v)
    return [v // (g or 1) for v in ints]


def _at(p: Poly, x: Fraction) -> Fraction:
    acc = Fraction(0)
    for c in reversed(p):
        acc = acc * x + c
    return acc


def _squarefree(n: int) -> tuple[int, int]:
    """n = s*s*d with d square-free."""
    s, d, k = 1, 1, 2
    rest = n
    while k * k <= rest:
        count = 0
        while rest % k == 0:
            rest //= k
            count += 1
        s *= k ** (count // 2)
        d *= k ** (count % 2)
        k += 1
    return s, d * rest


def surd_text(p: Fraction, q: Fraction, d: int) -> str:
    """Canonical text of p + q*sqrt(d): p omitted when 0, q when 1, '+' only after a printed p."""
    mag = "" if abs(q) == 1 else str(abs(q))
    tail = f"{mag}√{d}"
    if p == 0:
        return f"{'-' if q < 0 else ''}{tail}"
    return f"{p}{'-' if q < 0 else '+'}{tail}"


def _fstr(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def solve_poly(p: Poly) -> dict[str, Any]:
    """Real roots of p = 0: {"rational": [Fraction], "surds": [(p, q, d)], "complex_left": bool}."""
    if len(p) - 1 < 1 or len(p) - 1 > 4:
        raise ReferenceError("degree outside 1..4")
    rational: list[Fraction] = []
    surds: list[tuple[Fraction, Fraction, int]] = []
    rest = list(p)
    complex_left = False
    while len(rest) - 1 > 2:
        root = _rational_root(rest)
        if root is None:
            raise ReferenceError("no rational root")
        if root not in rational:
            rational.append(root)
        rest = _divide_root(rest, root)
    if len(rest) - 1 == 2:
        c, b, a = rest
        disc = b * b - 4 * a * c
        if disc < 0:
            complex_left = True
        else:
            num, den = disc.numerator, disc.denominator
            rn, rd = isqrt(num), isqrt(den)
            if rn * rn == num and rd * rd == den:
                root_d = Fraction(rn, rd)
                for r in ((-b - root_d) / (2 * a), (-b + root_d) / (2 * a)):
                    if r not in rational:
                        rational.append(r)
            else:
                s, d = _squarefree(num * den)
                q = abs(Fraction(s, den) / (2 * a))
                surds = [(-b / (2 * a), -q, d), (-b / (2 * a), q, d)]
    elif len(rest) - 1 == 1:
        r = -rest[0] / rest[1]
        if r not in rational:
            rational.append(r)
    return {"rational": sorted(rational), "surds": surds, "complex_left": complex_left}


def _rational_root(p: Poly) -> Fraction | None:
    if p[0] == 0:
        return Fraction(0)
    ints = _to_ints(p)
    for q in _divisors(ints[-1]):
        for pp in _divisors(ints[0]):
            for sign in (1, -1):
                cand = Fraction(pp * sign, q)
                if _at(p, cand) == 0:
                    return cand
    return None


def _divide_root(p: Poly, r: Fraction) -> Poly:
    n = len(p)
    q = [Fraction(0)] * (n - 1)
    carry = Fraction(0)
    for i in range(n - 1, 0, -1):
        carry = p[i] + carry * r
        q[i - 1] = carry
    return _trim(q)


# ---- Case solving ----


def solve_case(case: dict[str, Any]) -> dict[str, Any]:
    """Re-solve a cases.json record; returns {"status", "answer"} in the fixture's shape."""
    kind = case["kind"]
    if kind == "arith":
        value = eval_arith(case["expr"])
        out: dict[str, Any] = {
            "status": "solved",
            "answer": {"kind": "values", "values": [_fstr(value)]},
        }
        if case.get("claimed") is not None:
            out["claimTrue"] = Fraction(case["claimed"]) == value
        return out
    if kind == "poly_simplify":
        p = parse_poly(case["expr"])
        return {"status": "solved", "answer": {"kind": "expr", "coeffs": [_fstr(c) for c in p]}}
    if kind == "poly_eq":
        left, right = parse_poly(case["lhsText"]), parse_poly(case["rhsText"])
        p = _padd(left, _pscale(right, Fraction(-1)))
        if not p:
            return {"status": "identity", "answer": {"kind": "none"}}
        if len(p) == 1:
            return {"status": "no_solution", "answer": {"kind": "none"}}
        roots = solve_poly(p)
        values = [_fstr(r) for r in roots["rational"]]
        surds = [surd_text(*s) for s in roots["surds"]]
        if not values and not surds:
            return {"status": "no_solution", "answer": {"kind": "none"}}
        if surds:
            return {
                "status": "solved",
                "answer": {"kind": "surd", "values": values, "surds": surds},
            }
        return {"status": "solved", "answer": {"kind": "values", "values": values}}
    if kind == "linear_system":
        rows = []
        for text in case["system"]["texts"]:
            left, right = text.split("=")
            (la, lc), (ra, rc) = parse_linear(left), parse_linear(right)
            rows.append((la["x"] - ra["x"], la["y"] - ra["y"], rc - lc))
        (a1, b1, c1), (a2, b2, c2) = rows
        det = a1 * b2 - a2 * b1
        if det == 0:
            same = a1 * c2 == a2 * c1 and b1 * c2 == b2 * c1 and any([a1, b1, a2, b2])
            return {"status": "identity" if same else "no_solution", "answer": {"kind": "none"}}
        x = (c1 * b2 - c2 * b1) / det
        y = (a1 * c2 - a2 * c1) / det
        return {"status": "solved", "answer": {"kind": "pair", "x": _fstr(x), "y": _fstr(y)}}
    raise ReferenceError(f"unknown kind {kind}")


def kernel_inputs(case: dict[str, Any]) -> tuple[dict, dict, dict] | None:
    """(spec, answer, witness) for `kernel.verify`, built independently of the TypeScript answer.

    None when the kernel has no kind for this case (arithmetic, simplify, irrational roots,
    complex factors).
    """
    kind = case["kind"]
    if kind == "poly_eq":
        left, right = parse_poly(case["lhsText"]), parse_poly(case["rhsText"])
        p = _padd(left, _pscale(right, Fraction(-1)))
        if len(p) < 2:
            return None
        spec: dict[str, Any] = {
            "domain": "algebra",
            "kind": "polynomial",
            "lhs": [_fstr(c) for c in left],
            "rhs": [_fstr(c) for c in right],
        }
        roots = solve_poly(p)
        if roots["surds"]:
            return None
        pairs: list[list[Any]] = []
        rest = list(p)
        for r in roots["rational"]:
            m = 0
            while len(rest) > 1 and _at(rest, r) == 0:
                rest = _divide_root(rest, r)
                m += 1
            pairs.append([_fstr(r), m])
        if len(rest) > 1:  # a quadratic factor with no real roots is left over
            if len(p) == 3 and not pairs:
                c, b, a = p
                answer = {"roots": [], "count": 0}
                return spec, answer, {"discriminant": _fstr(b * b - 4 * a * c)}
            return None
        lead = _fstr(p[-1])
        return (
            spec,
            {"roots": [_fstr(r) for r in roots["rational"]], "count": len(pairs)},
            {"split": {"lead": lead, "roots": pairs}},
        )
    if kind == "linear_system":
        rows = []
        for text in case["system"]["texts"]:
            left, right = text.split("=")
            (la, lc), (ra, rc) = parse_linear(left), parse_linear(right)
            rows.append((la["x"] - ra["x"], la["y"] - ra["y"], rc - lc))
        (a1, b1, c1), (a2, b2, c2) = rows
        if a1 * b2 - a2 * b1 == 0:
            return None
        spec = {
            "domain": "algebra",
            "kind": "linear_system",
            "variables": ["x", "y"],
            "equations": [
                {"coeffs": [_fstr(a1), _fstr(b1)], "const": _fstr(c1)},
                {"coeffs": [_fstr(a2), _fstr(b2)], "const": _fstr(c2)},
            ],
        }
        sol = solve_case(case)["answer"]
        values = {"x": sol["x"], "y": sol["y"]}
        return spec, {"values": values}, {"values": values}
    return None


def check_surd_roots(case: dict[str, Any], surds: list[str]) -> bool:
    """Exact check that each canonical surd string satisfies lhs - rhs = 0 in Q(sqrt d)."""
    left, right = parse_poly(case["lhsText"]), parse_poly(case["rhsText"])
    p = _padd(left, _pscale(right, Fraction(-1)))
    for text in surds:
        pp, q, d = _read_surd(text)
        acc = (Fraction(0), Fraction(0))
        for c in reversed(p):
            # (a + b sqrt d)(pp + q sqrt d) + c
            a, b = acc
            acc = (a * pp + b * q * d + c, a * q + b * pp)
        if acc != (0, 0):
            return False
    return True


def _read_surd(text: str) -> tuple[Fraction, Fraction, int]:
    body, d = text.split("√")
    sign = 1
    p = Fraction(0)
    q_text = body
    for i in range(1, len(body)):
        if body[i] in "+-":
            p = Fraction(body[:i])
            sign = -1 if body[i] == "-" else 1
            q_text = body[i + 1 :]
            break
    else:
        if body.startswith("-"):
            sign, q_text = -1, body[1:]
        elif body.startswith("+"):
            q_text = body[1:]
    q = Fraction(q_text) if q_text else Fraction(1)
    return p, sign * q, int(d)


def numbers_in(text: str) -> list[Fraction]:
    """Every plain number written in a text (used by the ladder parity check)."""
    import re

    return [Fraction(m) for m in re.findall(r"\d+(?:\.\d+)?(?:/\d+)?", text)]
