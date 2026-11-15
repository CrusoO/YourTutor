"""Genetics verifier: exact Punnett enumeration, cross-checked by the multiplication rule.

Parents are strings of allele pairs, one pair per unlinked locus ("AaBb"). Two independent exact
computations must agree before the answer is compared: (1) enumerate every gamete pairing,
(2) multiply the per-locus probabilities. Phenotype keys: complete dominance gives the upper-case
letter if the genotype has one, else the lower-case letter; incomplete dominance keeps the
genotype ("Aa" is its own phenotype). Answer forms: `probabilities` (zeros omitted), `ratio`
(sorted high to low), `probability` (one named outcome).
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from fractions import Fraction

from app.factory.kernel.exact import Deadline, Reject, frac

MAX_LOCI = 4


def _loci(parent: object) -> list[tuple[str, str]]:
    if not isinstance(parent, str) or not parent or len(parent) % 2 or len(parent) > 2 * MAX_LOCI:
        raise Reject("bad_parent", repr(parent)[:20])
    pairs = [(parent[i], parent[i + 1]) for i in range(0, len(parent), 2)]
    for a, b in pairs:
        same_letter = a.isalpha() and b.isalpha() and a.isascii() and b.isascii()
        if not (same_letter and a.lower() == b.lower()):
            raise Reject("bad_parent", "each locus needs two alleles of one letter")
    return pairs


def gametes(parent: str) -> list[str]:
    return ["".join(choice) for choice in itertools.product(*_loci(parent))]


def _genotype(pairs: list[tuple[str, str]]) -> str:
    return "".join("".join(sorted(pair)) for pair in pairs)  # upper case sorts before lower


def enumerate_cross(p1: str, p2: str, deadline: Deadline) -> dict[str, Fraction]:
    g1, g2 = gametes(p1), gametes(p2)
    if [x.lower() for x in p1[::2]] != [x.lower() for x in p2[::2]]:
        raise Reject("loci_mismatch")
    counts: Counter[str] = Counter()
    for a, b in itertools.product(g1, g2):
        deadline.check()
        counts[_genotype(list(zip(a, b, strict=True)))] += 1
    total = len(g1) * len(g2)
    return {k: Fraction(v, total) for k, v in counts.items()}


def multiplication_rule(p1: str, p2: str) -> dict[str, Fraction]:
    per_locus: list[dict[str, Fraction]] = []
    for pair1, pair2 in zip(_loci(p1), _loci(p2), strict=True):
        cells = Counter("".join(sorted((a, b))) for a in pair1 for b in pair2)
        per_locus.append({k: Fraction(v, 4) for k, v in cells.items()})
    out: dict[str, Fraction] = {}
    for combo in itertools.product(*(d.items() for d in per_locus)):
        out["".join(k for k, _ in combo)] = math.prod((p for _, p in combo), start=Fraction(1))
    return out


def phenotype(genotype: str, dominance: dict[str, str]) -> str:
    parts = []
    for i in range(0, len(genotype), 2):
        pair = genotype[i : i + 2]
        if dominance.get(pair[0].upper(), "complete") == "incomplete":
            parts.append(pair)
        else:
            parts.append(pair[0])  # upper case sorts first: dominant letter if present
    return "".join(parts)


def _ratio(probs: dict[str, Fraction]) -> list[int]:
    den = math.lcm(*(p.denominator for p in probs.values()))
    ints = [int(p * den) for p in probs.values()]
    g = math.gcd(*ints)
    return sorted((i // g for i in ints), reverse=True)


def verify(spec: dict, answer: dict, witness: dict, deadline: Deadline) -> dict:
    if spec.get("kind") != "cross":
        raise Reject("unknown_kind", str(spec.get("kind")))
    parents = spec.get("parents")
    if not isinstance(parents, list) or len(parents) != 2:
        raise Reject("bad_parents")
    p1, p2 = parents
    exact = enumerate_cross(p1, p2, deadline)
    if exact != multiplication_rule(p1, p2):
        raise Reject("internal_disagreement", "enumeration and multiplication rule differ")
    if sum(exact.values()) != 1:
        raise Reject("probabilities_do_not_sum_to_one")
    if witness.get("gametes") != [sorted(gametes(p1)), sorted(gametes(p2))]:
        raise Reject("witness_mismatch", "lane gametes differ from the kernel's")
    dominance = spec.get("dominance", {})
    ask = spec.get("ask")
    dist: dict[str, Fraction] = {}
    if ask == "genotype":
        dist = exact
    elif ask == "phenotype":
        for genotype, p in exact.items():
            key = phenotype(genotype, dominance)
            dist[key] = dist.get(key, Fraction(0)) + p
    else:
        raise Reject("bad_ask", str(ask))
    checked = False
    if "probabilities" in answer:
        claimed = {k: frac(v) for k, v in answer["probabilities"].items() if frac(v) != 0}
        if claimed != dist:
            raise Reject("distribution_mismatch", "dropped, swapped or wrong outcome")
        checked = True
    if "ratio" in answer:
        if [int(x) for x in answer["ratio"]] != _ratio(dist):
            raise Reject("ratio_mismatch", f"exact ratio is {_ratio(dist)}")
        checked = True
    if "probability" in answer:
        target = spec.get("target")
        if target not in dist or frac(answer["probability"]) != dist[target]:
            raise Reject("probability_mismatch")
        checked = True
    if not checked:
        raise Reject("empty_answer")
    return {"outcomes": len(dist)}
