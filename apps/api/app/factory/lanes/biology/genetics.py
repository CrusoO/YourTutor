"""Genetics helpers for the heredity models: invented traits, two independent solvers, kernel spec.

Two independent computations of the offspring distribution of a cross (parents are strings of
allele pairs, one pair per unlinked gene, for example "TtRr"):

- Method A, the Punnett grid: list every gamete of each parent, pair them in a full grid, and tally
  the zygotes.
- Method B, the allele-frequency rule: for each gene on its own, every allele a parent passes on has
  a share; a genotype share is the product of the two shares; genes combine by multiplication.

The kernel adds a third check (its own enumeration against its own product rule). The traits are
invented for the stems ("in a certain plant species ..."), so no biological fact is asserted.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from app.factory.lanes.biology.common import qs


@dataclass(frozen=True)
class Trait:
    letter: str
    organism: str  # "plant" | "animal"
    dom: str  # adjective of the dominant form
    rec: str
    noun: str  # plural noun the adjective goes with
    gene: str  # what the gene decides, for the stem

    def phrase(self, dominant: bool) -> str:
        return f"{self.dom if dominant else self.rec} {self.noun}"


TRAITS: dict[str, Trait] = {
    t.letter: t
    for t in (
        Trait("T", "plant", "tall", "short", "stems", "stem height"),
        Trait("R", "plant", "round", "wrinkled", "seeds", "seed shape"),
        Trait("Y", "plant", "yellow", "green", "seeds", "seed colour"),
        Trait("P", "plant", "purple", "white", "flowers", "flower colour"),
        Trait("B", "animal", "black", "brown", "coats", "coat colour"),
        Trait("L", "animal", "long", "short", "hair", "hair length"),
        Trait("W", "plant", "smooth", "hairy", "leaves", "leaf surface"),
        Trait("D", "plant", "broad", "narrow", "leaves", "leaf width"),
        Trait("S", "animal", "spotted", "plain", "coats", "coat pattern"),
        Trait("E", "animal", "curly", "straight", "tails", "tail shape"),
    )
}


def subst(pattern: str, letters: str) -> str:
    """Swap the pattern letters H, G for the trait letters (H first, G second)."""
    out = pattern.replace("H", letters[0].upper()).replace("h", letters[0].lower())
    if len(letters) > 1:
        out = out.replace("G", letters[1].upper()).replace("g", letters[1].lower())
    return out


def pairs_of(parent: str) -> list[str]:
    return [parent[i : i + 2] for i in range(0, len(parent), 2)]


def tidy(pair: str) -> str:
    """A pair with its upper-case allele first."""
    return "".join(sorted(pair))


def gamete_list(parent: str) -> list[str]:
    """Every gamete (with repeats), one allele per gene, in the parent's gene order."""
    return ["".join(c) for c in itertools.product(*[(p[0], p[1]) for p in pairs_of(parent)])]


def witness_gametes(p1: str, p2: str) -> dict[str, Any]:
    return {"gametes": [sorted(gamete_list(p1)), sorted(gamete_list(p2))]}


def class_order(letters: str, kind: str) -> list[str]:
    """All possible classes in a fixed order, dominant first. kind: phen | gen."""
    sets: list[tuple[str, ...]]
    if kind == "phen":
        sets = [(c.upper(), c.lower()) for c in letters]
    else:
        sets = [(c.upper() * 2, c.upper() + c.lower(), c.lower() * 2) for c in letters]
    return ["".join(c) for c in itertools.product(*sets)]


def _phen(genotype: str) -> str:
    return "".join(p[0] for p in pairs_of(genotype))


# ---------------------------------------------------------------- method A: the Punnett grid


def dist_grid(p1: str, p2: str, kind: str) -> dict[str, Fraction]:
    g1, g2 = gamete_list(p1), gamete_list(p2)
    grid = [[(a, b) for b in g2] for a in g1]  # the Punnett square, row by row
    total = len(g1) * len(g2)
    tally: dict[str, int] = {}
    for row in grid:
        for a, b in row:
            genotype = "".join(tidy(x + y) for x, y in zip(a, b, strict=True))
            key = genotype if kind == "gen" else _phen(genotype)
            tally[key] = tally.get(key, 0) + 1
    return {k: Fraction(v, total) for k, v in tally.items()}


# ---------------------------------------------------------------- method B: allele shares


def _shares(pair: str) -> dict[str, Fraction]:
    out: dict[str, Fraction] = {}
    for allele in pair:
        out[allele] = out.get(allele, Fraction(0)) + Fraction(1, 2)
    return out


def _gene_dist(pair1: str, pair2: str, kind: str) -> dict[str, Fraction]:
    out: dict[str, Fraction] = {}
    for a, fa in _shares(pair1).items():
        for b, fb in _shares(pair2).items():
            key = tidy(a + b) if kind == "gen" else tidy(a + b)[0]
            out[key] = out.get(key, Fraction(0)) + fa * fb
    return out


def dist_shares(p1: str, p2: str, kind: str) -> dict[str, Fraction]:
    per_gene = [_gene_dist(a, b, kind) for a, b in zip(pairs_of(p1), pairs_of(p2), strict=True)]
    out: dict[str, Fraction] = {}
    for combo in itertools.product(*[d.items() for d in per_gene]):
        out["".join(k for k, _ in combo)] = math.prod((v for _, v in combo), start=Fraction(1))
    return out


# ---------------------------------------------------------------- answers


def ordered_ratio(dist: Mapping[str, Fraction], order: Sequence[str]) -> list[int]:
    present = [dist[c] for c in order if dist.get(c, 0) != 0]
    den = math.lcm(*(p.denominator for p in present))
    ints = [int(p * den) for p in present]
    g = math.gcd(*ints)
    return [i // g for i in ints]


def answer_from(bio: Mapping[str, Any], dist_fn: Any) -> dict[str, Any]:
    """The answer of one genetics task from a distribution function (grid or shares)."""
    p1, p2 = bio["parents"]
    letters = bio["letters"]
    task = bio["task"]
    kind = "gen" if task.endswith("gen") else "phen"
    dist = dist_fn(p1, p2, kind)
    if task.startswith("ratio"):
        ordered = ordered_ratio(dist, class_order(letters, kind))
        return {"ratio": sorted(ordered, reverse=True), "ordered": ordered}
    if task.startswith("prob"):
        return {"probability": qs(dist.get(bio["target"], Fraction(0)))}
    raise ValueError(f"unknown task {task}")


def solve_grid(bio: Mapping[str, Any]) -> dict[str, Any]:
    if bio["task"] == "identify":
        return identify(bio, dist_grid)
    return answer_from(bio, dist_grid)


def solve_shares(bio: Mapping[str, Any]) -> dict[str, Any]:
    if bio["task"] == "identify":
        return identify(bio, dist_shares)
    return answer_from(bio, dist_shares)


def identify(bio: Mapping[str, Any], dist_fn: Any) -> dict[str, Any]:
    """Which candidate parent, crossed with the tester, gives exactly the observed offspring?

    The answer is that cross's offspring distribution by phenotype; it is refused unless exactly
    one candidate matches (the item must have a single right answer).
    """
    observed = {k: Fraction(v) for k, v in bio["observed"].items()}
    matches = []
    for cand in bio["candidates"]:
        dist = dist_fn(cand, bio["tester"], "phen")
        if {k: v for k, v in dist.items() if v} == observed:
            matches.append(dist)
    if len(matches) != 1:
        raise ValueError("observed offspring do not single out one candidate")
    return {"probabilities": {k: qs(v) for k, v in sorted(matches[0].items())}}


def kernel_spec(
    bio: dict[str, Any], ask: str, parents: list[str], target: str | None = None
) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "domain": "genetics",
        "kind": "cross",
        "parents": parents,
        "ask": ask,
        "dominance": {},
        "bio": bio,
    }
    if target is not None:
        spec["target"] = target
    return spec


def describe_class(letters: str, cls: str) -> str:
    """Words for a phenotype class such as Tr: tall stems and wrinkled seeds."""
    parts = [
        TRAITS[letter.upper()].phrase(char.isupper())
        for letter, char in zip(letters, cls, strict=True)
    ]
    return " and ".join(parts)


def intro(letters: str) -> str:
    """The set-up sentence naming the alleles and which is dominant."""
    traits = [TRAITS[c.upper()] for c in letters]
    org = traits[0].organism
    clauses = [
        f"the allele {t.letter.upper()} for {t.phrase(True)} is dominant over "
        f"the allele {t.letter.lower()} for {t.phrase(False)}"
        for t in traits
    ]
    first = f"In a certain {org} species, " + ", and ".join(clauses) + "."
    if len(traits) > 1:
        first += " The two genes are on different chromosomes and are inherited independently."
    return first
