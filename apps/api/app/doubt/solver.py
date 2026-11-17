"""Server solve for `doubt-expr/1`: exact arithmetic, a rule-named trace, kernel verification.

Standard library plus the trusted kernel. No model, no network, no storage. The trace uses the
same rule ids as the web ladder (`apps/web/lib/doubt/rules.ts`), written for the same states, so
the two can be compared on the shared fixtures. Whatever this module computes is untrusted until
`kernel.verify` accepts it: only then is the result labelled `checked_by_code`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from math import gcd, isqrt, lcm
from typing import Any

from app.doubt.schema import MAX_DEGREE, DoubtExpr
from app.factory.kernel import KERNEL_VERSION, verify
from app.factory.kernel.verify import CHECKER_VERSIONS

LABEL_CHECKED = "checked_by_code"
LABEL_NOT_CHECKED = "not_verified"
KERNEL_TIMEOUT_S = 2.0

Poly = list[Fraction]  # lowest degree first, trailing zeros trimmed
Step = dict[str, Any]


@dataclass
class Trace:
    status: str  # solved | no_solution | identity | unsupported
    reason: str | None
    steps: list[Step] = field(default_factory=list)
    roots: list[Fraction] = field(default_factory=list)
    pair: tuple[Fraction, Fraction] | None = None
    irrational: bool = False
    # What the kernel is asked to accept: (spec, answer, witness), or None when it has no kind.
    kernel: tuple[dict, dict, dict] | None = None


# ---- number and polynomial helpers ----


def fs(v: Fraction) -> str:
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def trim(p: Poly) -> Poly:
    out = list(p)
    while out and out[-1] == 0:
        out.pop()
    return out


def coeff(p: Poly, i: int) -> Fraction:
    return p[i] if i < len(p) else Fraction(0)


def degree(p: Poly) -> int:
    return len(p) - 1


def sub(a: Poly, b: Poly) -> Poly:
    return trim([coeff(a, i) - coeff(b, i) for i in range(max(len(a), len(b)))])


def scale(p: Poly, k: Fraction) -> Poly:
    return trim([c * k for c in p])


def at(p: Poly, x: Fraction) -> Fraction:
    acc = Fraction(0)
    for c in reversed(p):
        acc = acc * x + c
    return acc


def show(p: Poly, v: str = "x") -> str:
    """Like the web `Poly.show`: `2x^2 - 3x + 1`."""
    if not p:
        return "0"
    parts: list[str] = []
    for i in range(len(p) - 1, -1, -1):
        co = p[i]
        if co == 0:
            continue
        mag = abs(co)
        if i == 0:
            body = fs(mag)
        else:
            m = "" if mag == 1 else (fs(mag) if mag.denominator == 1 else f"({fs(mag)})")
            body = f"{m}{v}{'^' + str(i) if i > 1 else ''}"
        if not parts:
            parts.append(f"-{body}" if co < 0 else body)
        else:
            parts.append(f"- {body}" if co < 0 else f"+ {body}")
    return " ".join(parts)


def eq_show(left: Poly, right: Poly, v: str = "x") -> str:
    return f"{show(left, v)} = {show(right, v)}"


def divide_root(p: Poly, r: Fraction) -> Poly | None:
    n = len(p)
    if n < 2:
        return None
    q = [Fraction(0)] * (n - 1)
    carry = Fraction(0)
    for i in range(n - 1, 0, -1):
        carry = p[i] + carry * r
        q[i - 1] = carry
    return trim(q) if p[0] + carry * r == 0 else None


def _divisors(n: int) -> list[int]:
    out: list[int] = []
    for i in range(1, isqrt(n) + 1):
        if n % i == 0:
            out.append(i)
            if i * i != n:
                out.append(n // i)
    return out


def to_integers(p: Poly) -> list[int]:
    den = 1
    for c in p:
        den = lcm(den, c.denominator)
    ints = [int(c * den) for c in p]
    g = 0
    for v in ints:
        g = gcd(g, v)
    return [v // (g or 1) for v in ints]


def rational_root(p: Poly) -> Fraction | None:
    """One rational root by the rational-root theorem, or None. Zero first."""
    if degree(p) < 1:
        return None
    if p[0] == 0:
        return Fraction(0)
    ints = to_integers(p)
    ps, qs = _divisors(abs(ints[0])), _divisors(abs(ints[-1]))
    if len(ps) * len(qs) > 40000:
        return None
    for q in qs:
        for pp in ps:
            if gcd(pp, q) != 1:
                continue
            for sign in (1, -1):
                cand = Fraction(pp * sign, q)
                if at(p, cand) == 0:
                    return cand
    return None


def root_factor(r: Fraction, v: str) -> str:
    if r == 0:
        return v
    return f"({v} - {fs(r)})" if r > 0 else f"({v} + {fs(abs(r))})"


def rational_sqrt(x: Fraction) -> Fraction | None:
    if x < 0:
        return None
    n, d = isqrt(x.numerator), isqrt(x.denominator)
    return Fraction(n, d) if n * n == x.numerator and d * d == x.denominator else None


def _step(rule: str, args: dict[str, str], before: str, after: str) -> Step:
    return {"rule": rule, "args": args, "before": before, "after": after}


# ---- poly_eq ----


def _linear_trace(left: Poly, right: Poly, v: str, steps: list[Step]) -> Fraction | str:
    a, b, c, d = coeff(left, 1), coeff(left, 0), coeff(right, 1), coeff(right, 0)

    def state() -> str:
        return eq_show(trim([b, a]), trim([d, c]), v)

    if c != 0:
        before = state()
        rule = "subtract_both_sides" if c > 0 else "add_both_sides"
        amount = show([Fraction(0), abs(c)], v)
        a, c = a - c, Fraction(0)
        steps.append(_step(rule, {"amount": amount}, before, state()))
    if a == 0:
        before = state()
        same = b == d
        steps.append(_step("identity" if same else "no_solution", {}, before, before))
        return "identity" if same else "no_solution"
    if b != 0:
        before = state()
        rule = "subtract_both_sides" if b > 0 else "add_both_sides"
        amount = fs(abs(b))
        d, b = d - b, Fraction(0)
        steps.append(_step(rule, {"amount": amount}, before, state()))
    value = d / a
    if a != 1:
        before = state()
        reciprocal = a.numerator == 1 and a.denominator > 1
        steps.append(
            _step(
                "multiply_both_sides" if reciprocal else "divide_both_sides",
                {"factor": str(a.denominator) if reciprocal else fs(a)},
                before,
                f"{v} = {fs(value)}",
            )
        )
    return value


def _quadratic_trace(q0: Poly, v: str, steps: list[Step]) -> tuple[list[Fraction], str]:
    """Rational roots and a verdict: rational | none | irrational."""
    q = q0
    den = 1
    for co in q:
        den = lcm(den, co.denominator)
    if den > 1:
        before = f"{show(q, v)} = 0"
        q = scale(q, Fraction(den))
        steps.append(
            _step("multiply_both_sides", {"factor": str(den)}, before, f"{show(q, v)} = 0")
        )
    a, b, c = q[2], q[1], q[0]
    disc = b * b - 4 * a * c
    start = f"{show(q, v)} = 0"
    if disc < 0:
        steps.append(_step("discriminant", {"value": fs(disc)}, start, f"D = {fs(disc)}"))
        steps.append(_step("no_real_roots", {}, f"D = {fs(disc)}", "no real solutions"))
        return [], "none"
    root = rational_sqrt(disc)
    if root is None:
        return [], "irrational"
    two = 2 * a
    rs = sorted({(-b - root) / two, (-b + root) / two})
    lead = "" if a == 1 else "-" if a == -1 else fs(a) if a.denominator == 1 else f"({fs(a)})"
    prod = (
        f"{root_factor(rs[0], v)}^2"
        if len(rs) == 1
        else f"{root_factor(rs[0], v)}{root_factor(rs[1], v)}"
    )
    steps.append(_step("factor_quadratic", {}, start, f"{lead}{prod} = 0"))
    zeros = " or ".join(f"{v} - {fs(r)} = 0".replace(f"{v} - -", f"{v} + ") for r in rs)
    steps.append(_step("zero_product", {}, f"{lead}{prod} = 0", zeros))
    for r in rs:
        bef = f"{v} - {fs(r)} = 0".replace(f"{v} - -", f"{v} + ")
        steps.append(
            _step(
                "add_both_sides" if r >= 0 else "subtract_both_sides",
                {"amount": fs(abs(r))},
                bef,
                f"{v} = {fs(r)}",
            )
        )
    return rs, "rational"


def _kernel_inputs(
    left: Poly, right: Poly, p: Poly, roots: list[Fraction]
) -> tuple[dict, dict, dict] | None:
    """Spec, answer and witness for the kernel, or None when the roots do not split p."""
    spec = {
        "domain": "algebra",
        "kind": "polynomial",
        "lhs": [fs(c) for c in left],
        "rhs": [fs(c) for c in right],
    }
    pairs: list[list[Any]] = []
    rest = list(p)
    for r in roots:
        m = 0
        while len(rest) > 1:
            nxt = divide_root(rest, r)
            if nxt is None:
                break
            rest, m = nxt, m + 1
        pairs.append([fs(r), m])
    if len(rest) > 1:  # a factor with no rational root is left over
        if degree(p) == 2 and not roots:
            c, b, a = p
            return spec, {"roots": [], "count": 0}, {"discriminant": fs(b * b - 4 * a * c)}
        return None
    answer = {"roots": [fs(r) for r in roots], "count": len(pairs)}
    return spec, answer, {"split": {"lead": fs(p[-1]), "roots": pairs}}


def solve_poly_eq(req: DoubtExpr) -> Trace:
    left = trim([Fraction(n) for n in req.lhs or []])
    right = trim([Fraction(n) for n in req.rhs or []])
    p = sub(left, right)
    v = "x"
    steps: list[Step] = []
    if not p:
        return Trace("identity", "always_true", [_step("identity", {}, "", "")])
    if degree(p) == 0:
        return Trace("no_solution", "never_true", [_step("no_solution", {}, "", "")])
    if degree(p) > MAX_DEGREE:
        return Trace("unsupported", "too_big")
    max_side = max(degree(left), degree(right))
    if degree(p) == 1:
        l_, r_ = left, right
        if max_side > 1:
            steps.append(_step("write_standard_form", {}, eq_show(left, right), f"{show(p)} = 0"))
            l_, r_ = p, []
        out = _linear_trace(l_, r_, v, steps)
        if isinstance(out, str):
            return Trace(out, "always_true" if out == "identity" else "never_true", steps)
        steps.append(_step("state_result", {}, "", f"{v} = {fs(out)}"))
        return _finish(left, right, p, steps, [out])

    if right or max_side > degree(p) or left != p:
        steps.append(_step("write_standard_form", {}, eq_show(left, right), f"{show(p)} = 0"))
    rest = p
    roots: list[Fraction] = []
    while degree(rest) > 2:
        r = rational_root(rest)
        nxt = divide_root(rest, r) if r is not None else None
        if r is None or nxt is None:
            return Trace("unsupported", "no_rational_root", [], irrational=True)
        steps.append(
            _step(
                "rational_root",
                {"root": fs(r)},
                f"{show(rest, v)} = 0",
                f"{root_factor(r, v)}({show(nxt, v)}) = 0",
            )
        )
        if r not in roots:
            roots.append(r)
        rest = nxt
    found, verdict = _quadratic_trace(rest, v, steps)
    if verdict == "irrational":
        return Trace("solved", "irrational_roots", [], irrational=True)
    roots.extend(r for r in found if r not in roots)
    roots.sort()
    if not roots:
        trace = Trace("no_solution", "no_real_roots", steps)
        trace.kernel = _kernel_inputs(left, right, p, [])
        return trace
    return _finish(left, right, p, steps, roots)


def _finish(left: Poly, right: Poly, p: Poly, steps: list[Step], roots: list[Fraction]) -> Trace:
    roots = sorted(roots)
    steps.append(
        _step(
            "substitute_check",
            {"values": ", ".join(fs(r) for r in roots)},
            "",
            "both sides are equal",
        )
    )
    trace = Trace("solved", None, steps, roots=roots)
    trace.kernel = _kernel_inputs(left, right, p, roots)
    return trace


# ---- linear_system ----


def _lin(a: Fraction, b: Fraction, x: str, y: str) -> str:
    parts: list[str] = []
    for co, name in ((a, x), (b, y)):
        if co == 0:
            continue
        mag = "" if abs(co) == 1 else fs(abs(co))
        body = f"{mag}{name}"
        if not parts:
            parts.append(f"-{body}" if co < 0 else body)
        else:
            parts.append(f"{'-' if co < 0 else '+'} {body}")
    return " ".join(parts) if parts else "0"


def solve_system(req: DoubtExpr) -> Trace:
    assert req.system is not None
    row1, row2 = ([Fraction(n) for n in row] for row in req.system.coeffs)
    a1, b1 = row1
    a2, b2 = row2
    c1, c2 = (Fraction(n) for n in req.system.consts)
    xn, yn = "x", "y"
    zero = Fraction(0)

    def e(a: Fraction, b: Fraction, k: Fraction) -> str:
        return f"{_lin(a, b, xn, yn)} = {fs(k)}"

    steps: list[Step] = []
    if a1 * b2 - a2 * b1 == 0:
        consistent = a1 * c2 == a2 * c1 and b1 * c2 == b2 * c1
        same = consistent and not all(q == 0 for q in (a1, b1, a2, b2))
        steps.append(_step("identity" if same else "no_solution", {}, "", ""))
        return Trace(
            "identity" if same else "no_solution", "same_line" if same else "parallel", steps
        )
    if b1 == 0 or b2 == 0:
        ua, uc = (a1, c1) if b1 == 0 else (a2, c2)
        xv = uc / ua
        before = e(a1, b1, c1) if b1 == 0 else e(a2, b2, c2)
        steps.append(_step("divide_both_sides", {"factor": fs(ua)}, before, f"{xn} = {fs(xv)}"))
    else:
        if b1.denominator == 1 and b2.denominator == 1:
            big = abs(b1.numerator) * abs(b2.numerator)
            m = big // gcd(b1.numerator, b2.numerator)
            m1, m2 = Fraction(m, abs(b1.numerator)), Fraction(m, abs(b2.numerator))
        else:
            m1, m2 = abs(b2), abs(b1)
        r1 = [a1 * m1, b1 * m1, c1 * m1]
        r2 = [a2 * m2, b2 * m2, c2 * m2]
        if m1 != 1:
            steps.append(
                _step(
                    "multiply_both_sides",
                    {"factor": fs(m1), "which": "1"},
                    e(a1, b1, c1),
                    e(r1[0], r1[1], r1[2]),
                )
            )
        if m2 != 1:
            steps.append(
                _step(
                    "multiply_both_sides",
                    {"factor": fs(m2), "which": "2"},
                    e(a2, b2, c2),
                    e(r2[0], r2[1], r2[2]),
                )
            )
        subtract = r1[1] == r2[1]
        ax = r1[0] - r2[0] if subtract else r1[0] + r2[0]
        ck = r1[2] - r2[2] if subtract else r1[2] + r2[2]
        state = f"{_lin(ax, zero, xn, yn)} = {fs(ck)}"
        steps.append(
            _step(
                "eliminate_unknown",
                {"unknown": yn, "op": "subtract" if subtract else "add"},
                f"{e(r1[0], r1[1], r1[2])};  {e(r2[0], r2[1], r2[2])}",
                state,
            )
        )
        xv = ck / ax
        if ax != 1:
            steps.append(_step("divide_both_sides", {"factor": fs(ax)}, state, f"{xn} = {fs(xv)}"))
    ua, ub, uc = (a1, b1, c1) if b1 != 0 else (a2, b2, c2)
    rest = uc - ua * xv
    left = f"{_lin(ub, zero, yn, yn)} = {fs(rest)}"
    steps.append(_step("substitute_back", {"value": fs(xv), "unknown": xn}, e(ua, ub, uc), left))
    yv = rest / ub
    steps.append(_step("solve_one_unknown", {}, left, f"{yn} = {fs(yv)}"))
    steps.append(
        _step(
            "substitute_check",
            {"values": f"{fs(xv)}, {fs(yv)}"},
            "",
            "both equations are equal",
        )
    )
    spec = {
        "domain": "algebra",
        "kind": "linear_system",
        "variables": [xn, yn],
        "equations": [
            {"coeffs": [fs(a1), fs(b1)], "const": fs(c1)},
            {"coeffs": [fs(a2), fs(b2)], "const": fs(c2)},
        ],
    }
    values = {xn: fs(xv), yn: fs(yv)}
    trace = Trace("solved", None, steps, pair=(xv, yv))
    trace.kernel = (spec, {"values": values}, {"values": values})
    return trace


# ---- the whole pipeline ----


def not_verified(reason: str, status: str = "unsupported") -> dict[str, Any]:
    """Honest 'could not check': no answer, no steps, never the 'Checked by code' label."""
    return {
        "schema": "doubt-result/1",
        "verified": False,
        "label": LABEL_NOT_CHECKED,
        "reason": reason,
        "status": status,
        "answer": None,
        "steps": [],
        "proof": None,
    }


def solve_doubt(req: DoubtExpr) -> dict[str, Any]:
    """The `doubt-result/1` body. Never raises for a well-formed request."""
    try:
        trace = solve_poly_eq(req) if req.kind == "poly_eq" else solve_system(req)
    except (ArithmeticError, ValueError, RecursionError):
        return not_verified("unsupported_kind")
    if trace.irrational:
        return not_verified("irrational_roots")
    if trace.status == "unsupported":
        return not_verified(trace.reason or "unsupported_kind")
    if trace.kernel is None:
        # identity, never-true and a singular system: the kernel has no kind for them
        return not_verified(trace.reason or "no_certificate", status=trace.status)
    spec, answer, witness = trace.kernel
    verdict = verify(spec, answer, witness, timeout_s=KERNEL_TIMEOUT_S)
    if not verdict.accepted:
        return not_verified(f"kernel_reject:{verdict.code}")
    if trace.pair is not None:
        shown: dict[str, Any] = {"kind": "pair", "x": fs(trace.pair[0]), "y": fs(trace.pair[1])}
    elif trace.roots:
        shown = {"kind": "values", "values": [fs(r) for r in trace.roots]}
    else:
        shown = {"kind": "none"}
    return {
        "schema": "doubt-result/1",
        "verified": True,
        "label": LABEL_CHECKED,
        "reason": None,
        "status": trace.status,
        "answer": shown,
        "steps": trace.steps,
        "proof": {"kernel": KERNEL_VERSION, "checker": f"algebra:{CHECKER_VERSIONS['algebra']}"},
    }
