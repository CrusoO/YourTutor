"""Reference Methods: second, differently built computations used by the worked example and the
fault-injection corpus. They read the SPEC only. Each lane writes its own; these show the pattern.

Shared code with the kernel is limited to formula parsing, unit conversion and the constants table
(all pinned by golden tests); the arithmetic itself is a different formulation or library.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import sympy

from app.factory.kernel import genetics as kgen
from app.factory.kernel import units
from app.factory.kernel.constants import constant
from app.factory.kernel.exact import frac, rational_sqrt, round_half_up
from app.factory.kernel.stoichiometry import molar_mass, parse_formula


def poly_coeffs(spec: Mapping[str, Any]) -> list[Fraction]:
    lhs = [frac(x) for x in spec["lhs"]]
    rhs = [frac(x) for x in spec.get("rhs", [])]
    n = max(len(lhs), len(rhs))
    lhs += [Fraction(0)] * (n - len(lhs))
    rhs += [Fraction(0)] * (n - len(rhs))
    return [a - b for a, b in zip(lhs, rhs, strict=True)]


def _answer_roots(roots: list[Fraction]) -> dict[str, Any]:
    ordered = sorted(set(roots))
    return {"roots": [str(r) for r in ordered], "count": len(ordered)}


class QuadraticFormula:
    id, version, independence_group, technique = (
        "alg.quadratic_formula",
        "1",
        "closed_form",
        "quadratic_formula",
    )

    def solve(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        c, b, a = poly_coeffs(spec)
        root = rational_sqrt(b * b - 4 * a * c)
        if root is None:
            raise ValueError("irrational or complex roots: outside this method")
        return _answer_roots([(-b + root) / (2 * a), (-b - root) / (2 * a)])


class RationalRootScan:
    """Rational root theorem: try every +-p/q (p | c0, q | lead) and keep those that vanish."""

    id, version, independence_group, technique = (
        "alg.rational_root_scan",
        "1",
        "enumeration",
        "factorise_quadratic",
    )

    def solve(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        coeffs = poly_coeffs(spec)
        scale = math.lcm(*(x.denominator for x in coeffs))
        ints = [int(x * scale) for x in coeffs]
        lead, low = abs(ints[-1]), abs(ints[0])
        if low == 0:
            raise ValueError("zero root: factor x out first")
        found = set()
        for p in (d for d in range(1, low + 1) if low % d == 0):
            for q in (d for d in range(1, lead + 1) if lead % d == 0):
                for sign in (1, -1):
                    r = Fraction(sign * p, q)
                    if sum(c * r**i for i, c in enumerate(ints)) == 0:
                        found.add(r)
        return _answer_roots(list(found))


def _unit_answer(spec: Mapping[str, Any], si_value: Fraction) -> dict[str, Any]:
    unit, dp = spec["answer_unit"], spec.get("answer_dp")
    value, _ = units.from_si(si_value, unit)
    if dp is not None:
        value = round_half_up(value, int(dp))
    out: dict[str, Any] = {"value": str(value), "unit": unit}
    if dp is not None:
        out["dp"] = dp
    return out


class SuvatSympy:
    """Solve the SUVAT equations with SymPy for the unknowns, then take the physical root."""

    id, version, independence_group, technique = (
        "kin.suvat_sympy",
        "1",
        "sympy.solve",
        "uniform_accel_eq",
    )

    def solve(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        given = {}
        for sym, q in spec["given"].items():
            if "const" in q:
                c = constant(q["const"])
                value, unit = frac(c.value) * frac(q.get("factor", 1)), c.unit
            else:
                value, unit = q["value"], q["unit"]
            given[sym] = units.to_si(value, unit)[0]
        syms = dict(zip("suvat", sympy.symbols("s u v a t", real=True), strict=True))
        s, u, v, a, t = (syms[k] for k in "suvat")
        eqs = [v - (u + a * t), s - (u * t + a * t**2 / 2)]
        known = {syms[k]: sympy.Rational(x.numerator, x.denominator) for k, x in given.items()}
        unknown = [x for x in syms.values() if x not in known]
        sols = sympy.solve([e.subs(known) for e in eqs], unknown, dict=True)
        pick = {
            tuple(sol.get(x, known.get(x)) for x in syms.values())
            for sol in sols
            if sol.get(t, known.get(t, 0)) >= 0
        }
        if len(pick) != 1:
            raise ValueError("no unique physical solution")
        values = dict(zip("suvat", next(iter(pick)), strict=True))
        target = values[spec["find"]]
        return _unit_answer(spec, Fraction(int(target.p), int(target.q)))


class BalanceBruteForce:
    """Smallest coefficient vector (entries 1..12) with equal atoms and charge on both sides."""

    id, version, independence_group, technique = (
        "stoich.balance_scan",
        "1",
        "enumeration",
        "balance_by_inspection",
    )

    def solve(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        species = spec["species"]
        counts = [parse_formula(sp["formula"]) for sp in species]
        sign = [1 if sp["side"] == "L" else -1 for sp in species]
        keys = sorted({e for c in counts for e in c})
        best = None
        for combo in itertools.product(range(1, 13), repeat=len(species)):
            ok = (
                all(
                    sum(s * k * c.get(e, 0) for s, k, c in zip(sign, combo, counts, strict=True))
                    == 0
                    for e in keys
                )
                and sum(
                    s * k * int(sp.get("charge", 0))
                    for s, k, sp in zip(sign, combo, species, strict=True)
                )
                == 0
            )
            if ok and math.gcd(*combo) == 1:
                if best is not None:
                    raise ValueError("more than one balance")
                best = combo
        if best is None:
            raise ValueError("no balance with coefficients up to 12")
        return {"coefficients": list(best)}


class MassSympy:
    id, version, independence_group, technique = (
        "stoich.mass_sympy",
        "1",
        "sympy.rational",
        "mole_concept",
    )

    def solve(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        sp, co = spec["reaction"]["species"], spec["reaction"]["coefficients"]
        g, t = spec["given"], spec["target"]
        mm = [
            sympy.Rational(m.numerator, m.denominator)
            for m in (molar_mass(x["formula"]) for x in sp)
        ]
        si, _ = units.to_si(g["value"], g["unit"])
        given_si = sympy.Rational(si.numerator, si.denominator)
        moles = (
            given_si * 1000 / mm[g["index"]] if g.get("quantity", "mass") == "mass" else given_si
        )
        target = moles * sympy.Rational(co[t["index"]], co[g["index"]])
        out_si = target * mm[t["index"]] / 1000 if t["quantity"] == "mass" else target
        return _unit_answer(spec, Fraction(int(out_si.p), int(out_si.q)))


class CrossSympy:
    """Expand the product of per-locus (allele)(allele) polynomials with SymPy."""

    id, version, independence_group, technique = (
        "gen.cross_sympy",
        "1",
        "sympy.expand",
        "punnett_square",
    )

    def solve(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        p1, p2 = spec["parents"]
        total: sympy.Expr = sympy.Integer(1)
        for i, (pair1, pair2) in enumerate(zip(kgen._loci(p1), kgen._loci(p2), strict=True)):

            def sym(allele: str, i: int = i) -> sympy.Symbol:
                return sympy.Symbol(f"L{i}_{allele}")

            g1, g2 = sum(sym(a) for a in pair1), sum(sym(a) for a in pair2)
            cell = sympy.expand(g1 * g2)
            total = total * sympy.Poly(cell).as_expr()
        total = sympy.expand(total)
        dist: dict[str, Fraction] = {}
        denom = 4 ** len(kgen._loci(p1))
        for monom, coeff in sympy.Poly(total).terms():
            gens = sympy.Poly(total).gens
            alleles: dict[int, list[str]] = {}
            for gen, power in zip(gens, monom, strict=True):
                locus, allele = gen.name[1:].split("_")
                alleles.setdefault(int(locus), []).extend([allele] * power)
            genotype = "".join("".join(sorted(alleles[k])) for k in sorted(alleles))
            dist[genotype] = dist.get(genotype, Fraction(0)) + Fraction(int(coeff), denom)
        if spec["ask"] == "phenotype":
            merged: dict[str, Fraction] = {}
            for genotype, p in dist.items():
                key = kgen.phenotype(genotype, spec.get("dominance", {}))
                merged[key] = merged.get(key, Fraction(0)) + p
            dist = merged
        return {"probabilities": {k: str(v) for k, v in sorted(dist.items())}}
