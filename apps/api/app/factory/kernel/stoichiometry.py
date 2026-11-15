"""Stoichiometry verifier: atom and charge balance as an integer matrix times a vector.

- balance: species (formula, charge, side L/R); answer `{"coefficients": [...]}`. Accepted only if
  M * c = 0 exactly, every c >= 1, gcd(c) = 1 and rank(M) = n - 1 (the solution is unique up to
  scale, so "the" balanced equation is well defined). Witness: the lane's own atom counts, which
  must equal the kernel's parse of each formula.
- mass: given a balanced reaction, a given species mass and a target species; answer is a mass or
  amount in the stated unit, exact or rounded half-up at `dp`. Witness: molar masses used.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Any

from app.factory.kernel import units
from app.factory.kernel.constants import atomic_mass
from app.factory.kernel.exact import Deadline, Reject, answer_matches, frac
from app.factory.kernel.linalg import rank, times

MAX_SPECIES = 12


def parse_formula(text: object) -> dict[str, int]:
    """`Ca(OH)2` -> {'Ca': 1, 'O': 2, 'H': 2}. Unknown elements and odd characters reject."""
    if not isinstance(text, str) or not 1 <= len(text) <= 40 or not text.isascii():
        raise Reject("bad_formula", repr(text)[:40])
    stack: list[dict[str, int]] = [{}]
    i, n = 0, len(text)

    def number(pos: int) -> tuple[int, int]:
        end = pos
        while end < n and text[end].isdigit():
            end += 1
        if end - pos > 3:
            raise Reject("bad_formula", "subscript too long")
        value = int(text[pos:end]) if end > pos else 1
        if value == 0:
            raise Reject("bad_formula", "zero subscript")
        return value, end

    while i < n:
        ch = text[i]
        if ch == "(":
            stack.append({})
            i += 1
        elif ch == ")":
            if len(stack) < 2:
                raise Reject("bad_formula", "unbalanced parentheses")
            inner = stack.pop()
            mult, i = number(i + 1)
            for sym, cnt in inner.items():
                stack[-1][sym] = stack[-1].get(sym, 0) + cnt * mult
        elif ch.isupper():
            sym = ch + (text[i + 1] if i + 1 < n and text[i + 1].islower() else "")
            atomic_mass(sym)  # rejects unknown elements
            cnt, i = number(i + len(sym))
            stack[-1][sym] = stack[-1].get(sym, 0) + cnt
        else:
            raise Reject("bad_formula", f"unexpected {ch!r}")
    if len(stack) != 1:
        raise Reject("bad_formula", "unbalanced parentheses")
    return stack[0]


def molar_mass(formula: str) -> Fraction:
    return sum((frac(atomic_mass(s)) * c for s, c in parse_formula(formula).items()), Fraction(0))


def _matrix(species: list[dict]) -> tuple[list[list[int]], list[dict[str, int]]]:
    if not 2 <= len(species) <= MAX_SPECIES:
        raise Reject("bad_species_count")
    sides = {sp.get("side") for sp in species}
    if sides != {"L", "R"}:
        raise Reject("needs_both_sides")
    counts = [parse_formula(sp.get("formula")) for sp in species]
    charges = [int(sp.get("charge", 0)) for sp in species]
    sign = [1 if sp["side"] == "L" else -1 for sp in species]
    elements = sorted({e for c in counts for e in c})
    rows = [[s * c.get(e, 0) for s, c in zip(sign, counts, strict=True)] for e in elements]
    if any(charges):
        rows.append([s * q for s, q in zip(sign, charges, strict=True)])
    return rows, counts


def check_balanced(species: list[dict], coeffs: Any) -> list[dict[str, int]]:
    rows, counts = _matrix(species)
    if (
        not isinstance(coeffs, list)
        or len(coeffs) != len(species)
        or any(isinstance(c, bool) or not isinstance(c, int) or not 1 <= c <= 1000 for c in coeffs)
    ):
        raise Reject("bad_coefficients")
    if any(times(rows, coeffs)):
        raise Reject("not_balanced", "atom or charge count differs between sides")
    if math.gcd(*coeffs) != 1:
        raise Reject("not_smallest", "coefficients share a factor")
    if rank([[Fraction(x) for x in row] for row in rows]) != len(species) - 1:
        raise Reject("not_unique", "balance is not unique up to scale")
    return counts


def verify_balance(spec: dict, answer: dict, witness: dict, deadline: Deadline) -> dict:
    counts = check_balanced(spec.get("species", []), answer.get("coefficients"))
    if witness.get("atom_counts") != counts:
        raise Reject("witness_mismatch", "lane atom counts differ from the kernel's parse")
    return {"species": len(counts)}


def verify_mass(spec: dict, answer: dict, witness: dict, deadline: Deadline) -> dict:
    reaction = spec.get("reaction", {})
    species = reaction.get("species", [])
    coeffs = reaction.get("coefficients")
    check_balanced(species, coeffs)
    given, target = spec.get("given", {}), spec.get("target", {})
    gi, ti = int(given.get("index", -1)), int(target.get("index", -1))
    if not (0 <= gi < len(species) and 0 <= ti < len(species)) or gi == ti:
        raise Reject("bad_species_index")
    if given.get("quantity", "mass") not in ("mass", "moles") or target.get("quantity") not in (
        "mass",
        "moles",
    ):
        raise Reject("bad_quantity")
    masses = [molar_mass(sp["formula"]) for sp in species]
    if witness.get("molar_masses") != [str(m) for m in masses]:
        raise Reject("witness_mismatch", "molar masses differ from the constants table")
    si, dim = units.to_si(given.get("value"), given.get("unit", ""))
    if given.get("quantity", "mass") == "mass":
        if dim != units.M:
            raise Reject("dimension_mismatch", "given mass")
        moles = si * 1000 / masses[gi]  # SI mass is kg; molar masses are g/mol
    else:
        if dim != units.AMOUNT:
            raise Reject("dimension_mismatch", "given amount")
        moles = si
    target_moles = moles * Fraction(coeffs[ti], coeffs[gi])
    exact_si = target_moles * masses[ti] / 1000 if target["quantity"] == "mass" else target_moles
    want = units.M if target["quantity"] == "mass" else units.AMOUNT
    value, got = units.from_si(exact_si, str(answer.get("unit", "")))
    if got != want:
        raise Reject("unit_dimension_mismatch", "answer unit has the wrong dimension")
    if not answer_matches(value, answer.get("value"), answer.get("dp")):
        raise Reject("value_mismatch", f"exact value is {value}")
    return {"moles_target": str(target_moles)}


def expected_dim(spec: dict) -> units.Dim | None:
    if spec.get("kind") != "mass":
        return None
    return units.M if spec.get("target", {}).get("quantity") == "mass" else units.AMOUNT


def verify(spec: dict, answer: dict, witness: dict, deadline: Deadline) -> dict:
    kind = spec.get("kind")
    if kind == "balance":
        return verify_balance(spec, answer, witness, deadline)
    if kind == "mass":
        return verify_mass(spec, answer, witness, deadline)
    raise Reject("unknown_kind", str(kind))
