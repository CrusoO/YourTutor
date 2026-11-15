"""Kinematics verifier: SUVAT with unit-checked quantities, solved exactly and uniquely.

Spec: three given quantities among s, u, v, a, t (value and unit, or a constant from the table),
and the one to find. The kernel converts to SI with dimension checks, solves the full tuple
itself (all ten given-triples are handled; rational results only), demands exactly one solution
with t >= 0 (so "which root?" cannot be ambiguous), and compares the answer in its own unit.
Witness: the lane's full SI tuple, which must equal the kernel's solution.
"""

from __future__ import annotations

from fractions import Fraction

from app.factory.kernel import units
from app.factory.kernel.constants import constant
from app.factory.kernel.exact import Deadline, Reject, answer_matches, frac, rational_sqrt

SYMS = ("s", "u", "v", "a", "t")
_VEL = units.dmul(units.L, units.T, -1)
DIMS: dict[str, units.Dim] = {
    "s": units.L,
    "u": _VEL,
    "v": _VEL,
    "a": units.dmul(units.L, units.T, -2),
    "t": units.T,
}


def _given_si(spec: dict) -> dict[str, Fraction]:
    out: dict[str, Fraction] = {}
    for sym, q in spec.get("given", {}).items():
        if sym not in DIMS or not isinstance(q, dict):
            raise Reject("bad_given", str(sym))
        if "const" in q:
            if "value" in q:
                raise Reject("bad_given", "constant and value both set")
            const = constant(q["const"])
            si, dim = units.to_si(frac(const.value) * frac(q.get("factor", 1)), const.unit)
        else:
            si, dim = units.to_si(q.get("value"), q.get("unit", ""))
        if dim != DIMS[sym]:
            raise Reject("dimension_mismatch", f"{sym} has the wrong unit dimension")
        out[sym] = si
    if len(out) != 3:
        raise Reject("needs_three_given")
    return out


def _solve(g: dict[str, Fraction]) -> list[dict[str, Fraction]]:
    k = frozenset(g)
    s, u, v, a, t = (g.get(x, Fraction(0)) for x in SYMS)
    out: list[dict[str, Fraction]] = []

    def add(**more: Fraction) -> None:
        out.append({**g, **more})

    if k == {"u", "a", "t"}:
        add(v=u + a * t, s=u * t + a * t * t / 2)
    elif k == {"u", "v", "t"} and t != 0:
        add(a=(v - u) / t, s=(u + v) * t / 2)
    elif k == {"u", "v", "a"} and a != 0:
        add(t=(v - u) / a, s=(v * v - u * u) / (2 * a))
    elif k == {"u", "v", "s"} and u + v != 0:
        tt = 2 * s / (u + v)
        if tt != 0:
            add(t=tt, a=(v - u) / tt)
    elif k == {"u", "a", "s"} and a != 0:
        root = rational_sqrt(u * u + 2 * a * s)
        for vv in [] if root is None else {root, -root}:
            add(v=vv, t=(vv - u) / a)
    elif k == {"v", "a", "t"}:
        add(u=v - a * t, s=v * t - a * t * t / 2)
    elif k == {"v", "a", "s"} and a != 0:
        root = rational_sqrt(v * v - 2 * a * s)
        for uu in [] if root is None else {root, -root}:
            add(u=uu, t=(v - uu) / a)
    elif k == {"a", "t", "s"} and t != 0:
        uu = (s - a * t * t / 2) / t
        add(u=uu, v=uu + a * t)
    elif k == {"u", "s", "t"} and t != 0:
        aa = 2 * (s - u * t) / (t * t)
        add(a=aa, v=u + aa * t)
    elif k == {"v", "s", "t"} and t != 0:
        aa = 2 * (v * t - s) / (t * t)
        add(a=aa, u=v - aa * t)
    return out


def verify(spec: dict, answer: dict, witness: dict, deadline: Deadline) -> dict:
    if spec.get("kind") != "suvat":
        raise Reject("unknown_kind", str(spec.get("kind")))
    given = _given_si(spec)
    find = spec.get("find")
    if find not in DIMS or find in given:
        raise Reject("bad_find", str(find))
    candidates = [c for c in _solve(given) if c["t"] >= 0]
    if not candidates:
        raise Reject("no_rational_solution", "no solution with t >= 0 in rationals")
    unique = {tuple(c[x] for x in SYMS) for c in candidates}
    if len(unique) != 1:
        raise Reject("ambiguous", "more than one physical solution")
    full = dict(zip(SYMS, next(iter(unique)), strict=True))
    if full["v"] != full["u"] + full["a"] * full["t"] or full["v"] ** 2 != (
        full["u"] ** 2 + 2 * full["a"] * full["s"]
    ):
        raise Reject("identity_failed", "SUVAT identities do not hold")  # defence in depth
    if full["s"] != full["u"] * full["t"] + full["a"] * full["t"] ** 2 / 2:
        raise Reject("identity_failed")
    if {k: frac(v) for k, v in witness.items()} != full:
        raise Reject("witness_mismatch", "lane tuple differs from the kernel's solution")
    value, dim = units.from_si(full[find], str(answer.get("unit", "")))
    if dim != DIMS[find]:
        raise Reject("unit_dimension_mismatch", "answer unit has the wrong dimension")
    if not answer_matches(value, answer.get("value"), answer.get("dp")):
        raise Reject("value_mismatch", f"exact value is {value}")
    return {"find": find}


def expected_dim(spec: dict) -> units.Dim | None:
    return DIMS.get(spec.get("find", ""))
