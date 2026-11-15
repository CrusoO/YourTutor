"""Algebra verifier: exact substitution, factorisation and solution count.

Specs carry structured coefficients, never English. Two kinds:

- polynomial: lhs - rhs = 0 for one unknown. Answer `{"roots": [...], "count": n}`; witness is
  either `{"split": {"lead": a, "roots": [[r, multiplicity], ...]}}` (every root rational; the
  kernel expands lead*prod(x - r)^m and demands it equal the polynomial, so no root is missing)
  or `{"discriminant": d}` for a quadratic with no rational split (count 0, 1 or 2).
- linear_system: n equations in n variables with a unique solution (coefficient rank n).
"""

from __future__ import annotations

from typing import Any

from app.factory.kernel.exact import Deadline, Reject, frac, rational_sqrt
from app.factory.kernel.linalg import rank
from app.factory.kernel.poly import Poly


def _need(mapping: dict[str, Any], key: str) -> Any:
    if key not in mapping:
        raise Reject("missing_field", key)
    return mapping[key]


def verify_polynomial(spec: dict, answer: dict, witness: dict, deadline: Deadline) -> dict:
    p = Poly(_need(spec, "lhs")) - Poly(spec.get("rhs", []))
    if p.degree < 1:
        raise Reject("degenerate_equation", "no unknown remains")
    if "roots" not in answer and "count" not in answer:
        raise Reject("empty_answer")
    claimed = [frac(r) for r in answer.get("roots", [])]
    if len(set(claimed)) != len(claimed):
        raise Reject("duplicate_root_in_answer")
    for root in claimed:  # exact substitution into the original equation
        if p.at(root) != 0:
            raise Reject("root_fails_substitution", str(root))
    if "split" in witness:
        split = witness["split"]
        roots = [(frac(r), int(m)) for r, m in _need(split, "roots")]
        if len({r for r, _ in roots}) != len(roots):
            raise Reject("duplicate_root_in_witness")
        if Poly.from_roots(_need(split, "lead"), roots) != p:
            raise Reject("factorisation_mismatch", "lead*prod(x-r)^m is not the polynomial")
        if "roots" in answer and set(claimed) != {r for r, _ in roots}:
            raise Reject("root_set_mismatch", "dropped or invented root")
        if "multiplicity" in answer:
            claimed_m = {frac(k): int(v) for k, v in answer["multiplicity"].items()}
            if claimed_m != dict(roots):
                raise Reject("multiplicity_mismatch")
        count = len(roots)
    elif "discriminant" in witness:
        if p.degree != 2 or claimed:
            raise Reject("discriminant_path_needs_rootless_quadratic")
        c, b, a = p.c
        disc = b * b - 4 * a * c
        if disc != frac(witness["discriminant"]):
            raise Reject("discriminant_mismatch")
        if disc > 0 and rational_sqrt(disc) is not None:
            raise Reject("roots_are_rational", "a split witness is required")
        count = 0 if disc < 0 else (1 if disc == 0 else 2)
    else:
        raise Reject("missing_witness", "algebra needs split or discriminant")
    if "count" in answer and int(answer["count"]) != count:
        raise Reject("count_mismatch", f"certified {count}")
    return {"degree": p.degree, "count": count}


def verify_linear_system(spec: dict, answer: dict, witness: dict, deadline: Deadline) -> dict:
    names = list(_need(spec, "variables"))
    equations = _need(spec, "equations")
    if not 1 <= len(names) <= 4 or len(equations) != len(names) or len(set(names)) != len(names):
        raise Reject("bad_system_shape")
    rows = [[frac(x) for x in eq["coeffs"]] for eq in equations]
    if any(len(row) != len(names) for row in rows):
        raise Reject("bad_system_shape")
    if rank(rows) != len(names):
        raise Reject("not_unique", "coefficient matrix is singular")
    values = {k: frac(v) for k, v in _need(answer, "values").items()}
    if set(values) != set(names):
        raise Reject("variable_set_mismatch")
    for row, eq in zip(rows, equations, strict=True):
        if sum(c * values[n] for c, n in zip(row, names, strict=True)) != frac(eq["const"]):
            raise Reject("equation_fails_substitution")
    if {k: frac(v) for k, v in _need(witness, "values").items()} != values:
        raise Reject("witness_mismatch")
    return {"unknowns": len(names)}


def verify(spec: dict, answer: dict, witness: dict, deadline: Deadline) -> dict:
    kind = spec.get("kind")
    if kind == "polynomial":
        return verify_polynomial(spec, answer, witness, deadline)
    if kind == "linear_system":
        return verify_linear_system(spec, answer, witness, deadline)
    raise Reject("unknown_kind", str(kind))
