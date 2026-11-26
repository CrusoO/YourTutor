# ruff: noqa: E501
"""Heredity models: crosses (ratios, probabilities, expected counts, test crosses), gametes, births.

Every model is computed from a closed rule set (Punnett enumeration and the multiplication rule)
and checked by two methods that do not share code with each other or with the kernel. The traits
in the stems are invented; the item never asks the learner to recall a fact about a real species.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.lanes.biology import genetics as g
from app.factory.lanes.biology.common import (
    CHAPTERS,
    Draft,
    Model,
    algebra_spec,
    fr,
    number_answer,
    qs,
    ratio_text,
)

CH = CHAPTERS["HERED"]
MONO_TRAITS = ("T", "R", "Y", "P", "B", "L", "W", "D", "S", "E")
DI_PAIRS = ("TR", "TY", "PT", "PR", "PY", "BL", "TW", "SE", "LE")
MONO_CROSSES = ("HH,Hh", "HH,hh", "Hh,Hh", "Hh,hh", "HH,HH", "hh,hh")
DI_CROSSES = (
    "HhGg,HhGg", "HhGg,hhgg", "HhGg,Hhgg", "HhGg,hhGg", "HHGg,hhgg",
    "HhGG,hhgg", "HhGg,HHGg", "HhGg,HhGG", "Hhgg,hhGg",
)  # fmt: skip

MISC: dict[str, tuple[str, str]] = {
    "GENOTYPE_FOR_PHENOTYPE": (
        "Gives the genotype ratio where the phenotype ratio is asked",
        "You may have counted genotypes. The question asks how many offspring look the same.",
    ),
    "PHENOTYPE_FOR_GENOTYPE": (
        "Gives the phenotype ratio where the genotype ratio is asked",
        "You may have grouped the offspring by appearance. Here each genotype counts on its own.",
    ),
    "ONE_PARENT_GAMETES": (
        "Uses the gametes of one parent only",
        "You may have used the gametes of one parent. Both parents' gametes go into the square.",
    ),
    "EQUAL_SHARES_ASSUMED": (
        "Assumes every class is equally likely",
        "You may have given every class the same share. Count the boxes of the Punnett square instead.",
    ),
    "RATIO_ORDER_REVERSED": (
        "Writes the ratio in the wrong order",
        "You may have written the parts the wrong way round. Follow the order the question asks for.",
    ),
    "TEST_CROSS_RATIO_ASSUMED": (
        "Uses the test cross result for every cross",
        "You may have used the result of a test cross. Work out the boxes for this cross.",
    ),
    "HETEROZYGOTE_LISTED_FIRST": (
        "Lists the heterozygous class first",
        "You may have put the biggest part first. The question gives the order of the classes.",
    ),
    "FIXED_RATIO_ASSUMED": (
        "Uses the result of a different cross",
        "You may have used the result of a cross between two heterozygous parents. Work out this cross.",
    ),
    "RATIOS_ADDED_NOT_MULTIPLIED": (
        "Joins the two single-gene ratios side by side",
        "You may have written one gene's ratio after the other. Independent genes combine by multiplying.",
    ),
    "ONE_GENE_ONLY": (
        "Works out one gene and ignores the other",
        "You may have used one gene only. Both genes are part of the question.",
    ),
    "COMPLEMENT_ASKED": (
        "Gives the chance of the other outcome",
        "You may have answered for the outcome that was not asked. Check which outcome the question names.",
    ),
    "ONE_PARENT_ONLY": (
        "Uses the chance of one gamete only",
        "You may have used the share of one gamete. A cross combines a gamete from each parent.",
    ),
    "ONE_BOX_ONLY": (
        "Counts a single box of the Punnett square",
        "You may have counted one box. Count every box that shows the outcome.",
    ),
    "ODDS_AS_PROBABILITY": (
        "Gives one class divided by the other as a probability",
        "You may have divided one class by the other. A probability divides by all the outcomes.",
    ),
    "GENES_ADDED_NOT_MULTIPLIED": (
        "Adds the chances of the two genes",
        "You may have added the two chances. Independent genes combine by multiplying.",
    ),
    "HOMOZYGOUS_ASSUMED": (
        "Chooses a genotype with fewer heterozygous genes than the offspring show",
        "You may have chosen a genotype that cannot produce every offspring class that appears.",
    ),
    "HETEROZYGOUS_ASSUMED": (
        "Chooses a genotype with more heterozygous genes than the offspring show",
        "You may have chosen a genotype that would produce classes that did not appear.",
    ),
    "WRONG_GENE_HETEROZYGOUS": (
        "Puts the heterozygous gene on the wrong trait",
        "You may have matched the right number of heterozygous genes to the wrong trait.",
    ),
    "SPLIT_EQUALLY": (
        "Splits the offspring equally between the classes",
        "You may have shared the offspring equally. The classes have different shares.",
    ),
    "RATIO_PART_AS_COUNT": (
        "Gives a part of the ratio as the number of offspring",
        "You may have given a ratio number as the count. Scale the share up to the total.",
    ),
    "TOTAL_NOT_SHARED": (
        "Gives all the offspring",
        "You may have given the whole number of offspring. Only one share of them is asked for.",
    ),
    "GAMBLERS_FALLACY": (
        "Thinks earlier births change the next birth",
        "You may have thought a boy is now more likely. Each birth is independent of the earlier ones.",
    ),
    "ORDER_IGNORED": (
        "Counts only one order of births",
        "You may have counted one order. Several orders give the same number of boys.",
    ),
    "FIRST_CHILD_ONLY": (
        "Uses the chance for one child only",
        "You may have used the chance for one birth. The question is about several children.",
    ),
    "SHARE_AS_PROBABILITY": (
        "Gives the share of boys wanted as the probability",
        "You may have divided the number of boys wanted by the number of children.",
    ),
    "HET_COUNT_AS_ANSWER": (
        "Counts the heterozygous genes instead of the types",
        "You may have given the number of heterozygous genes. Each one doubles the number of types.",
    ),
    "LETTERS_COUNTED": (
        "Counts the letters of the genotype",
        "You may have counted letters. Count the different gametes instead.",
    ),
    "ADDED_NOT_MULTIPLIED": (
        "Adds the numbers where they multiply",
        "You may have added. The two parents' choices combine by multiplying.",
    ),
    "TYPES_DOUBLED_PER_GENE": (
        "Doubles the count for every gene",
        "You may have doubled for each gene, even a gene with identical alleles.",
    ),
    "GENES_COUNTED_ONLY": (
        "Counts the genes instead of the classes",
        "You may have counted genes. Count the different outcomes.",
    ),
    "PUNNETT_BOXES_FOR_TYPES": (
        "Gives the number of Punnett square boxes as the number of gamete types",
        "You may have counted boxes. Count the different gametes one parent can make.",
    ),
    "GENOTYPES_FOR_TYPES": (
        "Gives the number of genotypes where the gamete types are asked",
        "You may have counted genotypes. Count the different gametes instead.",
    ),
    "ONE_TYPE_ASSUMED": (
        "Assumes there is only one kind",
        "You may have assumed that all gametes are alike. A gene with different alleles gives different gametes.",
    ),
    "GENOTYPES_FOR_PHENOTYPES": (
        "Counts genotypes where appearances are asked",
        "You may have counted the genotypes. Different genotypes can look the same.",
    ),
    "PHENOTYPES_FOR_GENOTYPES": (
        "Counts appearances where genotypes are asked",
        "You may have counted how the offspring look. Different genotypes can look the same, so there are more genotypes.",
    ),
    "BOXES_FOR_CLASSES": (
        "Gives the number of boxes as the number of classes",
        "You may have counted the boxes. Many boxes can show the same class.",
    ),
    "ALL_COMBINATIONS_ASSUMED": (
        "Assumes every possible class appears",
        "You may have assumed all classes appear. Some are impossible for these parents.",
    ),
}


def mc(name: str) -> str:
    if name not in MISC:
        raise KeyError(name)
    return f"BIO.MC.HERED.{name}"


# ---------------------------------------------------------------- shared helpers


def _rv(ordered: list[int]) -> dict[str, Any]:
    return {"ratio": sorted(ordered, reverse=True), "ordered": ordered}


def _gam_text(parent: str) -> str:
    seen: list[str] = []
    for gamete in g.gamete_list(parent):
        if gamete not in seen:
            seen.append(gamete)
    return seen[0] if len(seen) == 1 else ", ".join(seen[:-1]) + " and " + seen[-1]


def _parents(params: Mapping[str, str], letters: str) -> tuple[str, str]:
    first, second = (g.subst(x, letters) for x in params["cross"].split(","))
    return first, second


def _bio(
    model: str, variant: str, params: Mapping[str, str], letters: str, task: str, **extra: Any
) -> dict[str, Any]:
    p1, p2 = _parents(params, letters)
    return {
        "model": model,
        "variant": variant,
        "parents": [p1, p2],
        "letters": letters,
        "task": task,
        **extra,
    }


def _boxes(p1: str, p2: str) -> int:
    return len(g.gamete_list(p1)) * len(g.gamete_list(p2))


def _counts_text(letters: str, kind: str, p1: str, p2: str) -> str:
    dist = g.dist_grid(p1, p2, kind)
    total = _boxes(p1, p2)
    order = [c for c in g.class_order(letters, kind) if dist.get(c, 0)]
    parts = []
    for c in order:
        label = c if kind == "gen" else g.describe_class(letters, c)
        parts.append(f"{label}: {int(dist[c] * total)}")
    return f"Out of {total} boxes, " + "; ".join(parts) + "."


def _gene_dists(bio: Mapping[str, Any], kind: str = "phen") -> list[dict[str, Fraction]]:
    p1, p2 = bio["parents"]
    return [g.dist_grid(a, b, kind) for a, b in zip(g.pairs_of(p1), g.pairs_of(p2), strict=True)]


def _cross_sentence(p1: str, p2: str, letters: str) -> str:
    noun = g.TRAITS[letters[0].upper()].organism
    a = "An" if noun[0] in "aeiou" else "A"
    return f"{a} {noun} with genotype {p1} is crossed with {a.lower()} {noun} with genotype {p2}."


def _ratio_hints(p1: str, p2: str, ask_word: str) -> list[str]:
    return [
        "Find the gametes each parent can make, then combine them in a Punnett square.",
        f"Count how many boxes of the square show each {ask_word}, then write the counts as a ratio in the order the question gives, in the lowest terms.",
        f"The first parent makes the gametes {_gam_text(p1)}, and the second parent makes the gametes {_gam_text(p2)}.",
    ]


# ---------------------------------------------------------------- MONO_RATIO


def _mono_ratio(params: Mapping[str, str]) -> Draft | str:
    letters = params["trait"]
    variant = params["variant"]
    task = "ratio_phen" if variant == "phen_ratio" else "ratio_gen"
    kind = "phen" if task == "ratio_phen" else "gen"
    bio = _bio("HERED.MONO_RATIO", variant, params, letters, task)
    p1, p2 = bio["parents"]
    dist = g.dist_grid(p1, p2, kind)
    if sum(1 for v in dist.values() if v) < 2:
        return "single_class_is_not_a_ratio"
    order = [c for c in g.class_order(letters, kind) if dist.get(c, 0)]
    answer = g.answer_from(bio, g.dist_grid)
    ordered = answer["ordered"]
    if kind == "phen":
        ask = (
            "What is the ratio of offspring with "
            f"{g.TRAITS[letters].phrase(True)} to offspring with {g.TRAITS[letters].phrase(False)}?"
        )
    else:
        ask = f"What is the ratio of the offspring genotypes {' : '.join(order)}?"
    stem = f"{g.intro(letters)} {_cross_sentence(p1, p2, letters)} {ask}"
    other_kind = "gen" if kind == "phen" else "phen"
    shares = g.dist_shares(p1, p2, other_kind)
    other = g.ordered_ratio(shares, g.class_order(letters, other_kind))
    counts = Counter(g.gamete_list(p1))
    one_parent = [counts[x] // math.gcd(*counts.values()) for x in sorted(counts)]
    wrongs: list[tuple[str, dict[str, Any], str]] = []
    wrongs.append(
        (
            "GENOTYPE_FOR_PHENOTYPE" if kind == "phen" else "PHENOTYPE_FOR_GENOTYPE",
            _rv(other),
            ratio_text(other),
        )
    )
    if len(one_parent) > 1:
        wrongs.append(("ONE_PARENT_GAMETES", _rv(one_parent), ratio_text(one_parent)))
    wrongs.append(("TEST_CROSS_RATIO_ASSUMED", _rv([1, 1]), "1 : 1"))
    rev = list(reversed(ordered))
    wrongs.append(("RATIO_ORDER_REVERSED", _rv(rev), ratio_text(rev)))
    if kind == "gen" and len(ordered) == 3:
        mixed = [ordered[1], ordered[0], ordered[2]]
        wrongs.append(("HETEROZYGOTE_LISTED_FIRST", _rv(mixed), ratio_text(mixed)))
    eq = [1] * len(ordered)
    wrongs.append(("EQUAL_SHARES_ASSUMED", _rv(eq), ratio_text(eq)))
    wrongs.append(("FIXED_RATIO_ASSUMED", _rv([3, 1]), "3 : 1"))
    wrongs.append(("FIXED_RATIO_ASSUMED", _rv([1, 2, 1]), "1 : 2 : 1"))
    wrongs.append(("HETEROZYGOTE_LISTED_FIRST", _rv([2, 1, 1]), "2 : 1 : 1"))
    spec = g.kernel_spec(bio, "phenotype" if kind == "phen" else "genotype", [p1, p2])
    steps = [
        f"The first parent {p1} makes the gametes {_gam_text(p1)}; the second parent {p2} makes the gametes {_gam_text(p2)}.",
        "Pair every gamete of the first parent with every gamete of the second in a Punnett square.",
        _counts_text(letters, kind, p1, p2),
        f"Write the counts in the order asked, in the lowest terms: {ratio_text(ordered)}.",
    ]
    return Draft(
        variant=variant, spec=spec, answer=answer, witness=g.witness_gametes(p1, p2), stem=stem,
        hints=_ratio_hints(p1, p2, "phenotype" if kind == "phen" else "genotype"), steps=steps,
        key_text=ratio_text(ordered), wrongs=wrongs, difficulty=0.3 if kind == "phen" else 0.4,
        role="procedure", prediction="Before you draw the square, which outcome do you expect to be the most common?",
        tokens=[], features=["punnett_square"],
    )  # fmt: skip


# ---------------------------------------------------------------- MONO_PROB

_MONO_PROB = {
    "p_dom": ("phen", "upper", "has {dom}"),
    "p_rec": ("phen", "lower", "has {rec}"),
    "p_het": ("gen", "het", "has the genotype {het}"),
    "p_homdom": ("gen", "hom", "has the genotype {hom}"),
}


def _mono_prob(params: Mapping[str, str]) -> Draft | str:
    letters = params["trait"]
    variant = params["variant"]
    kind, which, phrase = _MONO_PROB[variant]
    up, lo = letters.upper(), letters.lower()
    target = {"upper": up, "lower": lo, "het": up + lo, "hom": up + up}[which]
    bio = _bio(
        "HERED.MONO_PROB",
        variant,
        params,
        letters,
        "prob_phen" if kind == "phen" else "prob_gen",
        target=target,
    )
    p1, p2 = bio["parents"]
    dist = g.dist_grid(p1, p2, kind)
    p = dist.get(target, Fraction(0))
    if p in (0, 1):
        return "probability_is_certain_or_impossible"
    trait = g.TRAITS[letters]
    ask_phrase = phrase.format(
        dom=trait.phrase(True), rec=trait.phrase(False), het=up + lo, hom=up + up
    )
    stem = (
        f"{g.intro(letters)} {_cross_sentence(p1, p2, letters)} "
        f"What is the probability that one offspring, picked at random, {ask_phrase}? Give the answer as a fraction."
    )
    answer = {"probability": qs(p)}
    wrongs: list[tuple[str, dict[str, Any], str]] = []

    def add(name: str, value: Fraction) -> None:
        if 0 <= value <= 1:
            wrongs.append((name, {"probability": qs(value)}, fr(value)))

    add("COMPLEMENT_ASKED", 1 - p)
    add("ODDS_AS_PROBABILITY", p / (1 - p))
    add("ODDS_AS_PROBABILITY", (1 - p) / p)
    add("ONE_PARENT_ONLY", Fraction(1, 2))
    add("ONE_BOX_ONLY", Fraction(1, 4))
    add("FIXED_RATIO_ASSUMED", Fraction(3, 4))
    spec = g.kernel_spec(bio, "phenotype" if kind == "phen" else "genotype", [p1, p2], target)
    steps = [
        f"The first parent {p1} makes the gametes {_gam_text(p1)}; the second parent {p2} makes the gametes {_gam_text(p2)}.",
        _counts_text(letters, kind, p1, p2),
        f"The probability is the number of boxes that show the outcome asked for, divided by all the boxes: {fr(p)}.",
    ]
    hints = [
        "Find the gametes each parent can make, then combine them in a Punnett square.",
        "A probability is the number of boxes that show the outcome asked for, divided by the number of all the boxes.",
        f"The first parent makes the gametes {_gam_text(p1)}, and the second parent makes the gametes {_gam_text(p2)}.",
    ]
    return Draft(
        variant=variant, spec=spec, answer=answer, witness=g.witness_gametes(p1, p2), stem=stem,
        hints=hints, steps=steps, key_text=fr(p), wrongs=wrongs, difficulty=0.35, role="apply",
        prediction="Before you calculate, is the outcome asked for more likely or less likely than the other?",
        tokens=[fr(p)], features=["punnett_square"],
    )  # fmt: skip


# ---------------------------------------------------------------- DI_RATIO


def _gene_ratio(dists: list[dict[str, Fraction]], letters: str, i: int) -> list[int]:
    return g.ordered_ratio(dists[i], g.class_order(letters[i], "phen"))


def _di_ratio(params: Mapping[str, str]) -> Draft | str:
    letters = params["pair"]
    bio = _bio("HERED.DI_RATIO", "phen_ratio", params, letters, "ratio_phen")
    p1, p2 = bio["parents"]
    dist = g.dist_grid(p1, p2, "phen")
    order = [c for c in g.class_order(letters, "phen") if dist.get(c, 0)]
    if len(order) < 2:
        return "single_class_is_not_a_ratio"
    answer = g.answer_from(bio, g.dist_grid)
    ordered = answer["ordered"]
    names = "; ".join(g.describe_class(letters, c) for c in order)
    stem = (
        f"{g.intro(letters)} {_cross_sentence(p1, p2, letters)} "
        f"What is the ratio of offspring in the groups {names}, in that order?"
    )
    d = _gene_dists(bio)
    r1, r2 = _gene_ratio(d, letters, 0), _gene_ratio(d, letters, 1)
    wrongs: list[tuple[str, dict[str, Any], str]] = []
    wrongs.append(("FIXED_RATIO_ASSUMED", _rv([9, 3, 3, 1]), "9 : 3 : 3 : 1"))
    wrongs.append(("TEST_CROSS_RATIO_ASSUMED", _rv([1, 1, 1, 1]), "1 : 1 : 1 : 1"))
    joined = r1 + r2
    wrongs.append(("RATIOS_ADDED_NOT_MULTIPLIED", _rv(joined), ratio_text(joined)))
    if len(r1) > 1:
        wrongs.append(("ONE_GENE_ONLY", _rv(r1), ratio_text(r1)))
    if len(r2) > 1:
        wrongs.append(("ONE_GENE_ONLY", _rv(r2), ratio_text(r2)))
    rev = list(reversed(ordered))
    wrongs.append(("RATIO_ORDER_REVERSED", _rv(rev), ratio_text(rev)))
    eq = [1] * len(ordered)
    wrongs.append(("EQUAL_SHARES_ASSUMED", _rv(eq), ratio_text(eq)))
    wrongs.append(("ALL_COMBINATIONS_ASSUMED", _rv([3, 3, 1, 1]), "3 : 3 : 1 : 1"))
    spec = g.kernel_spec(bio, "phenotype", [p1, p2])
    steps = [
        f"The first parent {p1} makes the gametes {_gam_text(p1)}; the second parent {p2} makes the gametes {_gam_text(p2)}.",
        "Pair every gamete of the first parent with every gamete of the second in a Punnett square.",
        _counts_text(letters, "phen", p1, p2),
        f"Write the counts in the order asked, in the lowest terms: {ratio_text(ordered)}.",
    ]
    hints = [
        "Find the gametes each parent can make, then combine them in a Punnett square.",
        "Count the boxes that show each group of offspring, then write the counts as a ratio in the order the question gives, in the lowest terms.",
        f"The first parent makes the gametes {_gam_text(p1)}, and the second parent makes the gametes {_gam_text(p2)}.",
    ]
    return Draft(
        variant="phen_ratio", spec=spec, answer=answer, witness=g.witness_gametes(p1, p2), stem=stem,
        hints=hints, steps=steps, key_text=ratio_text(ordered), wrongs=wrongs, difficulty=0.6,
        role="procedure", prediction="Before you draw the square, how many boxes will it have?",
        tokens=[], features=["punnett_square", "two_genes"],
    )  # fmt: skip


# ---------------------------------------------------------------- DI_PROB

_DI_PROB = {
    "both_dom": ("phen", "both dominant"),
    "dom_rec": ("phen", "first dominant, second recessive"),
    "rec_dom": ("phen", "first recessive, second dominant"),
    "both_rec": ("phen", "both recessive"),
    "double_het": ("gen", "heterozygous for both genes"),
}


def _di_prob(params: Mapping[str, str]) -> Draft | str:
    letters = params["pair"]
    variant = params["variant"]
    kind, _ = _DI_PROB[variant]
    u1, l1, u2, l2 = letters[0].upper(), letters[0].lower(), letters[1].upper(), letters[1].lower()
    target = {
        "both_dom": u1 + u2,
        "dom_rec": u1 + l2,
        "rec_dom": l1 + u2,
        "both_rec": l1 + l2,
        "double_het": u1 + l1 + u2 + l2,
    }[variant]
    bio = _bio(
        "HERED.DI_PROB",
        variant,
        params,
        letters,
        "prob_phen" if kind == "phen" else "prob_gen",
        target=target,
    )
    p1, p2 = bio["parents"]
    dist = g.dist_grid(p1, p2, kind)
    p = dist.get(target, Fraction(0))
    if p in (0, 1):
        return "probability_is_certain_or_impossible"
    if kind == "phen":
        what = f"shows {g.describe_class(letters, target)}"
    else:
        what = f"has the genotype {target}"
    stem = (
        f"{g.intro(letters)} {_cross_sentence(p1, p2, letters)} "
        f"What is the probability that one offspring, picked at random, {what}? Give the answer as a fraction."
    )
    d = _gene_dists(bio, kind)
    if kind == "phen":
        keys = [target[0], target[1]]
    else:
        keys = [target[0:2], target[2:4]]
    q1, q2 = d[0].get(keys[0], Fraction(0)), d[1].get(keys[1], Fraction(0))
    answer = {"probability": qs(p)}
    wrongs: list[tuple[str, dict[str, Any], str]] = []

    def add(name: str, value: Fraction) -> None:
        if 0 <= value <= 1:
            wrongs.append((name, {"probability": qs(value)}, fr(value)))

    add("ONE_GENE_ONLY", q1)
    add("ONE_GENE_ONLY", q2)
    add("GENES_ADDED_NOT_MULTIPLIED", (q1 + q2) / 2)
    add("GENES_ADDED_NOT_MULTIPLIED", min(q1 + q2, Fraction(1)))
    add("COMPLEMENT_ASKED", 1 - p)
    add("ONE_BOX_ONLY", Fraction(1, 16))
    add(
        "FIXED_RATIO_ASSUMED",
        {
            "both_dom": Fraction(9, 16),
            "dom_rec": Fraction(3, 16),
            "rec_dom": Fraction(3, 16),
            "both_rec": Fraction(1, 16),
            "double_het": Fraction(1, 4),
        }[variant],
    )
    add("ODDS_AS_PROBABILITY", p / (1 - p))
    spec = g.kernel_spec(bio, "phenotype" if kind == "phen" else "genotype", [p1, p2], target)
    steps = [
        f"The first parent {p1} makes the gametes {_gam_text(p1)}; the second parent {p2} makes the gametes {_gam_text(p2)}.",
        "Treat each gene on its own: find the chance of the outcome wanted for the first gene and for the second gene.",
        f"The genes are independent, so multiply the two chances: {fr(q1)} x {fr(q2)} = {fr(p)}.",
    ]
    hints = [
        "The two genes are inherited independently, so each gene can be worked out on its own.",
        "Find the chance of the wanted outcome for the first gene, then for the second gene, then combine the two chances by multiplying.",
        f"The first parent makes the gametes {_gam_text(p1)}, and the second parent makes the gametes {_gam_text(p2)}.",
    ]
    return Draft(
        variant=variant, spec=spec, answer=answer, witness=g.witness_gametes(p1, p2), stem=stem,
        hints=hints, steps=steps, key_text=fr(p), wrongs=wrongs, difficulty=0.65, role="apply",
        prediction="Before you calculate, is the outcome common or rare among the offspring?",
        tokens=[fr(p)], features=["product_rule", "two_genes"],
    )  # fmt: skip


# ---------------------------------------------------------------- TEST_CROSS (identify the tested plant)

_CANDS = ("HHGG", "HHGg", "HhGG", "HhGg")


def _quarter_words(dist: Mapping[str, Fraction], letters: str) -> str:
    order = [c for c in g.class_order(letters, "phen") if dist.get(c, 0)]
    names = [g.describe_class(letters, c) for c in order]
    if len(order) == 1:
        return f"all of the offspring have {names[0]}"
    if len(order) == 2:
        return f"half of the offspring have {names[0]}, while the other half have {names[1]}"
    return "the offspring fall into four equal groups, namely " + "; ".join(names)


def _test_cross(params: Mapping[str, str]) -> Draft | str:
    letters = params["pair"]
    key = g.subst(params["key"], letters)
    cands = [g.subst(c, letters) for c in _CANDS]
    tester = g.subst("hhgg", letters)
    key_dist = g.dist_grid(key, tester, "phen")
    observed = {k: qs(v) for k, v in key_dist.items() if v}
    bio = {
        "model": "HERED.TEST_CROSS", "variant": "identify", "task": "identify", "letters": letters,
        "candidates": cands, "tester": tester, "observed": observed, "parents": [key, tester],
    }  # fmt: skip
    answer = g.solve_grid(bio)
    order = [c for c in g.class_order(letters, "phen") if key_dist.get(c, 0)]
    both = g.describe_class(letters, letters.upper())
    both_rec = g.describe_class(letters, letters.lower())
    noun = g.TRAITS[letters[0].upper()].organism
    art = "an" if noun[0] in "aeiou" else "a"
    stem = (
        f"{g.intro(letters)} {art.capitalize()} {noun} with {both} is test-crossed with {art} {noun} with {both_rec}. "
        f"The result of the test cross is that {_quarter_words(key_dist, letters)}. What is the genotype of the {noun} that was tested?"
    )
    het = _het
    wrongs: list[tuple[str, dict[str, Any], str]] = []
    for cand in cands:
        if cand == key:
            continue
        dist = g.dist_grid(cand, tester, "phen")
        value = {"probabilities": {k: qs(v) for k, v in sorted(dist.items()) if v}}
        if het(cand) < het(key):
            name = "HOMOZYGOUS_ASSUMED"
        elif het(cand) > het(key):
            name = "HETEROZYGOUS_ASSUMED"
        else:
            name = "WRONG_GENE_HETEROZYGOUS"
        wrongs.append((name, value, cand))
    spec = g.kernel_spec(bio, "phenotype", [key, tester])
    steps = [
        f"A test cross uses {art} {noun} with {both_rec}, which can pass on only recessive alleles. Every dominant or recessive form in the offspring therefore shows what the tested {noun} passed on.",
        f"The offspring show {len(order)} different group{'s' if len(order) > 1 else ''}, so the tested {noun} makes {len(order)} different gamete type{'s' if len(order) > 1 else ''}.",
        f"Try each candidate genotype in a Punnett square with {tester}; only {key} gives the groups seen.",
    ]
    hints = [
        "The parent used for the test cross passes on only recessive alleles, so each offspring shows which allele the tested parent passed on.",
        "Count how many different groups of offspring appear. Each heterozygous gene of the tested parent doubles that number.",
        "Check a candidate by writing its gametes and pairing them with the gametes of the other parent in a Punnett square.",
    ]
    return Draft(
        variant="identify", spec=spec, answer=answer, witness=g.witness_gametes(key, tester), stem=stem,
        hints=hints, steps=steps, key_text=key, wrongs=wrongs, difficulty=0.7, role="transfer",
        prediction="Before you decide, how many different gamete types must the tested parent make?",
        tokens=[key], features=["test_cross", "two_genes"],
    )  # fmt: skip


# ---------------------------------------------------------------- COUNTS


def _expected(model_id: str, params: Mapping[str, str], di: bool) -> Draft | str:
    letters = params["t"]
    variant = params["variant"]
    n_total = int(params["N"])
    if (len(letters) == 2) != di:
        return "trait_does_not_fit_model"
    cross = params["cross"]
    if (len(cross.split(",")[0]) == 4) != di:
        return "cross_does_not_fit_model"
    if di:
        u1, l1, u2, l2 = (
            letters[0].upper(),
            letters[0].lower(),
            letters[1].upper(),
            letters[1].lower(),
        )
        target = {"both_dom": u1 + u2, "dom_rec": u1 + l2, "both_rec": l1 + l2}.get(variant)
    else:
        up, lo = letters.upper(), letters.lower()
        target = {"dom": up, "rec": lo}.get(variant)
    if target is None:
        return "variant_does_not_fit_model"
    bio = _bio(model_id, variant, params, letters, "prob_phen", target=target, total=n_total)
    p1, p2 = bio["parents"]
    p = g.dist_grid(p1, p2, "phen").get(target, Fraction(0))
    count = p * n_total
    if p in (0, 1) or count.denominator != 1:
        return "expected_count_is_not_a_whole_number"
    if di:
        what = f"show {g.describe_class(letters, target)}"
        classes = 4
    else:
        what = f"have {g.TRAITS[letters].phrase(target.isupper())}"
        classes = 2
    stem = (
        f"{g.intro(letters)} {_cross_sentence(p1, p2, letters)} "
        f"The cross produces {n_total} offspring. How many of them are expected to {what}?"
    )
    answer = number_answer(count, "offspring")
    wrongs: list[tuple[str, dict[str, Any], str]] = []

    def add(name: str, value: Fraction) -> None:
        if value.denominator == 1 and 0 <= value <= n_total:
            wrongs.append((name, number_answer(value, "offspring"), f"{int(value)} offspring"))

    add("COMPLEMENT_ASKED", n_total - count)
    add("SPLIT_EQUALLY", Fraction(n_total, classes))
    add("ONE_BOX_ONLY", Fraction(n_total, 16 if di else 4))
    add("TOTAL_NOT_SHARED", Fraction(n_total))
    add("RATIO_PART_AS_COUNT", Fraction(p.numerator))
    add("ODDS_AS_PROBABILITY", count / (1 - p))
    add("FIXED_RATIO_ASSUMED", Fraction(n_total * (9 if di else 3), 16 if di else 4))
    spec = algebra_spec("x", Fraction(p.denominator), Fraction(p.numerator * n_total), bio)
    steps = [
        f"The first parent {p1} makes the gametes {_gam_text(p1)}; the second parent {p2} makes the gametes {_gam_text(p2)}.",
        _counts_text(letters, "phen", p1, p2),
        f"The share of offspring wanted is {fr(p)}.",
        f"Multiply the share by the total: {fr(p)} x {n_total} = {int(count)}.",
    ]
    hints = [
        "First find the share of the offspring that show the outcome, using a Punnett square.",
        "Then multiply that share by the total number of offspring to get the expected number.",
        f"The first parent makes the gametes {_gam_text(p1)}, and the second parent makes the gametes {_gam_text(p2)}.",
    ]
    return Draft(
        variant=variant, spec=spec, answer=answer, witness={"values": {"x": qs(count)}}, stem=stem,
        hints=hints, steps=steps, key_text=f"{int(count)} offspring", wrongs=wrongs,
        difficulty=0.55 if di else 0.45, role="apply",
        prediction="Before you calculate, should the answer be more or less than half of the offspring?",
        tokens=[str(int(count))], features=["punnett_square", "scaling"],
    )  # fmt: skip


def _counts_mono(params: Mapping[str, str]) -> Draft | str:
    return _expected("HERED.COUNTS_MONO", params, False)


def _counts_di(params: Mapping[str, str]) -> Draft | str:
    return _expected("HERED.COUNTS_DI", params, True)


def _solve_count(bio: Mapping[str, Any], dist_fn: Any) -> dict[str, Any]:
    p1, p2 = bio["parents"]
    p = dist_fn(p1, p2, "phen").get(bio["target"], Fraction(0))
    return number_answer(p * int(bio["total"]), "offspring")


def solve_count_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    return _solve_count(bio, g.dist_grid)


def solve_count_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    return _solve_count(bio, g.dist_shares)


# ---------------------------------------------------------------- GAMETES (counting classes)

_GAM_VARIANTS = ("gamete_types", "grid_boxes", "phen_classes", "gen_classes")
_PARENTS_SINGLE = ("Hh", "HH", "HhGg", "HHGg", "HhGG", "HHGG")


def _het(parent: str) -> int:
    return sum(1 for p in g.pairs_of(parent) if p[0] != p[1])


def _gametes(params: Mapping[str, str]) -> Draft | str:  # noqa: PLR0911
    letters = params["t"]
    variant = params["variant"]
    if variant == "gamete_types":
        case = params["case"]
        if "," in case:
            return "case_is_a_cross"
        genes = len(case) // 2
        if len(letters) != genes:
            return "trait_does_not_fit_genotype"
        parent = g.subst(case, letters)
        bio = {
            "model": "HERED.GAMETES",
            "variant": variant,
            "parents": [parent],
            "letters": letters,
        }
        answer_val = Fraction(len(set(g.gamete_list(parent))))
        stem = f"{g.intro(letters)} How many different types of gametes can {'an' if g.TRAITS[letters[0]].organism[0] in 'aeiou' else 'a'} {g.TRAITS[letters[0]].organism} with genotype {parent} produce?"
        h = _het(parent)
        wrongs = [
            ("HET_COUNT_AS_ANSWER", Fraction(h)), ("LETTERS_COUNTED", Fraction(len(parent))),
            ("TYPES_DOUBLED_PER_GENE", Fraction(2 * genes)), ("ADDED_NOT_MULTIPLIED", Fraction(2 * h + genes - h)),
            ("ALL_COMBINATIONS_ASSUMED", Fraction(2**genes)), ("PUNNETT_BOXES_FOR_TYPES", Fraction(4**genes)),
            ("GENOTYPES_FOR_TYPES", Fraction(3**genes)), ("ONE_TYPE_ASSUMED", Fraction(1)),
        ]  # fmt: skip
        steps = [
            f"A gamete gets one allele of each gene. The genotype {parent} has {h} heterozygous gene{'s' if h != 1 else ''}.",
            f"Each heterozygous gene gives 2 choices and each homozygous gene gives 1, so multiply the choices: {int(answer_val)}.",
        ]
        hints = [
            "A gamete carries one allele from each gene. Different gametes differ in the alleles they carry.",
            "A gene whose two alleles are the same gives only one choice. A gene whose alleles differ gives two choices.",
            "Write the choices for each gene, then combine the choices of the different genes by multiplying them.",
        ]
        unit = "types"
        eq = (Fraction(1), answer_val)
        key = f"{int(answer_val)}"
    else:
        case = params["case"]
        if "," not in case:
            return "case_is_a_single_parent"
        genes = len(case.split(",")[0]) // 2
        if len(letters) != genes:
            return "trait_does_not_fit_cross"
        p1, p2 = (g.subst(x, letters) for x in case.split(","))
        bio = {
            "model": "HERED.GAMETES",
            "variant": variant,
            "parents": [p1, p2],
            "letters": letters,
        }
        if variant == "grid_boxes":
            g1, g2 = len(set(g.gamete_list(p1))), len(set(g.gamete_list(p2)))
            answer_val = Fraction(g1 * g2)
            stem = (
                f"{g.intro(letters)} {_cross_sentence(p1, p2, letters)} "
                "A Punnett square has one row for each different gamete type of the first parent and one column for each different gamete type of the second parent. How many boxes does it have?"
            )
            wrongs = [
                ("ADDED_NOT_MULTIPLIED", Fraction(g1 + g2)), ("ALL_COMBINATIONS_ASSUMED", Fraction(4**genes)),
                ("LETTERS_COUNTED", Fraction(len(p1) + len(p2))), ("GENES_COUNTED_ONLY", Fraction(genes)),
                ("ONE_PARENT_GAMETES", Fraction(g1 * g1)),
                ("GENOTYPES_FOR_TYPES", Fraction(3**genes)), ("ONE_TYPE_ASSUMED", Fraction(1)),
            ]  # fmt: skip
            steps = [
                f"The first parent {p1} makes {g1} different gamete type{'s' if g1 != 1 else ''}; the second parent {p2} makes {g2}.",
                f"The square has one box for each pair of types: {g1} x {g2} = {g1 * g2}.",
            ]
            hints = [
                "Count the different gamete types of each parent first. A type that repeats counts once.",
                "Each row is paired with each column, so combine the two counts by multiplying.",
                f"The first parent makes the gametes {_gam_text(p1)}, and the second parent makes the gametes {_gam_text(p2)}.",
            ]
            unit = "boxes"
        else:
            kind = "phen" if variant == "phen_classes" else "gen"
            answer_val = Fraction(len([v for v in g.dist_grid(p1, p2, kind).values() if v]))
            word = "different appearances" if kind == "phen" else "different genotypes"
            stem = f"{g.intro(letters)} {_cross_sentence(p1, p2, letters)} How many {word} can the offspring have?"
            full = 2**genes if kind == "phen" else 3**genes
            wrongs = [
                ("ALL_COMBINATIONS_ASSUMED", Fraction(full)), ("GENES_COUNTED_ONLY", Fraction(genes)),
                ("ADDED_NOT_MULTIPLIED", Fraction(2 * genes if kind == "phen" else 3 * genes)),
                ("LETTERS_COUNTED", Fraction(len(p1))),
                ("ONE_PARENT_GAMETES", Fraction(len(set(g.gamete_list(p1))))),
                ("PHENOTYPES_FOR_GENOTYPES" if kind == "gen" else "GENOTYPES_FOR_PHENOTYPES", Fraction(len([v for v in g.dist_grid(p1, p2, "phen" if kind == "gen" else "gen").values() if v]))),
                ("BOXES_FOR_CLASSES", Fraction(len(g.gamete_list(p1)) * len(g.gamete_list(p2)))),
                ("ONE_TYPE_ASSUMED", Fraction(1)),
            ]  # fmt: skip
            steps = [
                _counts_text(letters, kind, p1, p2),
                f"Count the groups that appear at least once: {int(answer_val)}.",
            ]
            hints = [
                "Fill in the Punnett square and look at which outcomes actually appear.",
                "Count each different outcome once, however many boxes show it. An outcome that no box shows does not count.",
                f"The first parent makes the gametes {_gam_text(p1)}, and the second parent makes the gametes {_gam_text(p2)}.",
            ]
            unit = "kinds"
        eq = (Fraction(1), answer_val)
        key = f"{int(answer_val)}"
    answer = number_answer(answer_val)
    _ = unit
    spec = algebra_spec("x", eq[0], eq[1], bio)
    out_wrongs = [
        (n, number_answer(v), str(int(v))) for n, v in wrongs if v.denominator == 1 and v > 0
    ]
    return Draft(
        variant=variant, spec=spec, answer=answer, witness={"values": {"x": qs(answer_val)}}, stem=stem,
        hints=hints, steps=steps, key_text=key, wrongs=out_wrongs, difficulty=0.4, role="procedure",
        prediction="Before you count, should the answer be a small number or a large one?",
        tokens=[key], features=["counting"],
    )  # fmt: skip


def solve_gametes_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    variant = bio["variant"]
    if variant == "gamete_types":
        return number_answer(Fraction(len(set(g.gamete_list(bio["parents"][0])))))
    p1, p2 = bio["parents"]
    if variant == "grid_boxes":
        return number_answer(Fraction(len(set(g.gamete_list(p1))) * len(set(g.gamete_list(p2)))))
    kind = "phen" if variant == "phen_classes" else "gen"
    return number_answer(Fraction(len([v for v in g.dist_grid(p1, p2, kind).values() if v])))


def solve_gametes_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    variant = bio["variant"]
    if variant == "gamete_types":
        return number_answer(Fraction(2 ** _het(bio["parents"][0])))
    p1, p2 = bio["parents"]
    if variant == "grid_boxes":
        return number_answer(Fraction(2 ** (_het(p1) + _het(p2))))
    kind = "phen" if variant == "phen_classes" else "gen"
    count = 1
    for a, b in zip(g.pairs_of(p1), g.pairs_of(p2), strict=True):
        count *= len([v for v in g._gene_dist(a, b, kind).values() if v])
    return number_answer(Fraction(count))


# ---------------------------------------------------------------- SEX_SEQ (births)

ASSUME = (
    "Assume each child is equally likely to be a boy or a girl, whatever the earlier children were."
)


def _sex_seq(params: Mapping[str, str]) -> Draft | str:  # noqa: PLR0911
    variant, n, k = params["variant"], int(params["n"]), int(params["k"])
    two_n = 2**n
    if variant == "exactly_k":
        if not 1 <= k <= n - 1:
            return "k_out_of_range"
        count = math.comb(n, k)
        stem = f"A couple has {n} children. {ASSUME} What is the probability that exactly {k} of the {n} children are boys? Give the answer as a fraction."
        wrong_vals = [
            ("ORDER_IGNORED", Fraction(1, two_n)),
            ("SHARE_AS_PROBABILITY", Fraction(k, n)),
            ("FIRST_CHILD_ONLY", Fraction(1, 2)),
            ("COMPLEMENT_ASKED", 1 - Fraction(count, two_n)),
            ("ADDED_NOT_MULTIPLIED", Fraction(k, two_n)),
        ]
        steps = [
            f"There are 2 equally likely outcomes for each child, so there are {two_n} equally likely birth sequences.",
            f"The number of sequences with exactly {k} boys is the number of ways to choose which {k} of the {n} children are boys: {count}.",
            f"The probability is {count} out of {two_n}: {fr(Fraction(count, two_n))}.",
        ]
        hints = [
            "Each child is a boy or a girl with the same chance, so list the equally likely sequences of births.",
            "Count the sequences that have exactly the number of boys asked for, then divide by the number of all the sequences.",
            "The number of sequences is 2 multiplied by itself once for each child.",
        ]
    elif variant == "all_girls":
        if k != 1:
            return "k_not_used_by_this_variant"
        count = 1
        stem = f"A couple has {n} children. {ASSUME} What is the probability that {'both' if n == 2 else 'all ' + str(n)} children are girls? Give the answer as a fraction."
        wrong_vals = [
            ("FIRST_CHILD_ONLY", Fraction(1, 2)),
            ("SHARE_AS_PROBABILITY", Fraction(1, n)),
            ("GAMBLERS_FALLACY", Fraction(1, 2 * two_n)),
            ("COMPLEMENT_ASKED", 1 - Fraction(1, two_n)),
            ("ADDED_NOT_MULTIPLIED", Fraction(1, 2 * n)),
        ]
        steps = [
            "Each child is a girl with probability 1 out of 2, and the births are independent.",
            f"Multiply the chances for all {n} children: 1 out of {two_n}.",
        ]
        hints = [
            "Each birth is independent of the others, so the chance of a run of births is found by combining the chances of the single births.",
            "Combine the chances of the single births by multiplying them.",
            "The chance for one child being a girl is one half.",
        ]
    elif variant == "next_after_run":
        if k != 1:
            return "k_not_used_by_this_variant"
        count = 1
        stem = f"A couple already has {n} children and all of them are girls. {ASSUME} What is the probability that their next child is a boy? Give the answer as a fraction."
        wrong_vals = [
            ("GAMBLERS_FALLACY", Fraction(1, 2 ** (n + 1))),
            ("GAMBLERS_FALLACY", 1 - Fraction(1, 2**n)),
            ("COMPLEMENT_ASKED", Fraction(1, 2**n)),
            ("SHARE_AS_PROBABILITY", Fraction(1, n + 1)),
            ("ADDED_NOT_MULTIPLIED", Fraction(1, 2 * n)),
        ]
        steps = [
            "The sex of a child does not depend on the sex of the earlier children.",
            "So the chance that the next child is a boy is the chance for one child on its own: 1 out of 2.",
        ]
        hints = [
            "Ask whether the earlier births change the chance for the next birth.",
            "Each birth is independent of the earlier ones.",
            "Only the next child matters, and the earlier children play no part.",
        ]
        two_n = 2
    elif variant == "at_least_one_boy":
        if k != 1:
            return "k_not_used_by_this_variant"
        count = two_n - 1
        stem = f"A couple has {n} children. {ASSUME} What is the probability that at least one of the {n} children is a boy? Give the answer as a fraction."
        wrong_vals = [
            ("COMPLEMENT_ASKED", Fraction(1, two_n)),
            ("FIRST_CHILD_ONLY", Fraction(1, 2)),
            ("SHARE_AS_PROBABILITY", Fraction(1, n)),
            ("ORDER_IGNORED", Fraction(n, two_n)),
            ("ADDED_NOT_MULTIPLIED", Fraction(min(n, 2 * n - 1), 2 * n)),
        ]
        steps = [
            f"The only way to have no boy is for all {n} children to be girls, with probability 1 out of {two_n}.",
            f"So the probability of at least one boy is 1 minus that: {fr(Fraction(count, two_n))}.",
        ]
        hints = [
            "Think about the one outcome that does not count, then use the fact that all the outcomes together have probability 1.",
            "Find the probability that there is no boy at all, and take it away from 1.",
            "No boy at all means every child is a girl.",
        ]
    else:  # both_sexes
        if k != 1 or n < 2:
            return "k_not_used_by_this_variant"
        count = two_n - 2
        stem = f"A couple has {n} children. {ASSUME} What is the probability that there is at least one boy and at least one girl among the {n} children? Give the answer as a fraction."
        wrong_vals = [
            ("COMPLEMENT_ASKED", Fraction(2, two_n)),
            ("ONE_PARENT_ONLY", Fraction(1, 2)),
            ("ORDER_IGNORED", 1 - Fraction(1, two_n)),
            ("SHARE_AS_PROBABILITY", Fraction(1, n)),
            ("ADDED_NOT_MULTIPLIED", Fraction(n - 1, n)),
        ]
        steps = [
            f"The sequences that do not count are the one with all girls and the one with all boys: 2 sequences out of {two_n}.",
            f"So the probability is 1 minus 2 out of {two_n}: {fr(Fraction(count, two_n))}.",
        ]
        hints = [
            "Find the outcomes that fail the condition, then take their probability away from 1.",
            "The condition fails when all the children are of the same sex, which can happen in two ways.",
            "Each of those two ways has the same probability, found by multiplying the single-birth chances.",
        ]
    p = Fraction(count, two_n)
    if p in (0, 1):
        return "probability_is_certain_or_impossible"
    bio = {"model": "HERED.SEX_SEQ", "variant": variant, "n": n, "k": k}
    answer = number_answer(p)
    wrongs = [(name, number_answer(v), fr(v)) for name, v in wrong_vals if 0 < v < 1]
    spec = algebra_spec("x", Fraction(two_n), Fraction(count), bio)
    return Draft(
        variant=variant, spec=spec, answer=answer, witness={"values": {"x": qs(p)}}, stem=stem,
        hints=hints, steps=steps, key_text=fr(p), wrongs=wrongs, difficulty=0.45, role="apply",
        prediction="Before you calculate, is the outcome likely or unlikely?", tokens=[fr(p)],
        features=["independence"],
    )  # fmt: skip


def solve_sex_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    n, k, v = int(bio["n"]), int(bio["k"]), bio["variant"]
    if v == "exactly_k":
        p = Fraction(math.comb(n, k), 2**n)
    elif v == "all_girls":
        p = Fraction(1, 2**n)
    elif v == "next_after_run":
        p = Fraction(1, 2)
    elif v == "at_least_one_boy":
        p = 1 - Fraction(1, 2**n)
    else:
        p = 1 - Fraction(2, 2**n)
    return number_answer(p)


def solve_sex_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    n, k, v = int(bio["n"]), int(bio["k"]), bio["variant"]
    if v == "next_after_run":  # conditional probability by listing sequences of length n + 1
        seqs = list(itertools.product("BG", repeat=n + 1))
        given = [s for s in seqs if all(c == "G" for c in s[:n])]
        return number_answer(Fraction(sum(1 for s in given if s[n] == "B"), len(given)))
    seqs = list(itertools.product("BG", repeat=n))
    tests = {
        "exactly_k": lambda s: s.count("B") == k,
        "all_girls": lambda s: s.count("B") == 0,
        "at_least_one_boy": lambda s: "B" in s,
        "both_sexes": lambda s: "B" in s and "G" in s,
    }
    return number_answer(Fraction(sum(1 for s in seqs if tests[v](s)), len(seqs)))


# ---------------------------------------------------------------- the models

_MONO_BOX_T = MONO_TRAITS
HEREDITY_MODELS: dict[str, Model] = {
    m.id: m
    for m in (
        Model(
            "HERED.MONO_RATIO",
            "BIO.HERED.MONO_RATIO",
            CH,
            "Find the phenotype or genotype ratio of a single-gene cross",
            "punnett_square",
            "product_rule",
            "bio.punnett_grid",
            "bio.allele_shares",
            {"trait": MONO_TRAITS, "cross": MONO_CROSSES, "variant": ("phen_ratio", "gen_ratio")},
            _mono_ratio,
            g.solve_grid,
            g.solve_shares,
        ),
        Model(
            "HERED.MONO_PROB",
            "BIO.HERED.MONO_PROB",
            CH,
            "Find the probability of a trait or genotype in a single-gene cross",
            "punnett_square",
            "product_rule",
            "bio.punnett_grid",
            "bio.allele_shares",
            {"trait": MONO_TRAITS, "cross": MONO_CROSSES, "variant": tuple(_MONO_PROB)},
            _mono_prob,
            g.solve_grid,
            g.solve_shares,
            ("BIO.HERED.MONO_RATIO",),
        ),
        Model(
            "HERED.DI_RATIO",
            "BIO.HERED.DI_RATIO",
            CH,
            "Find the phenotype ratio of a two-gene cross",
            "punnett_square",
            "product_rule",
            "bio.punnett_grid",
            "bio.allele_shares",
            {"pair": DI_PAIRS, "cross": DI_CROSSES},
            _di_ratio,
            g.solve_grid,
            g.solve_shares,
            ("BIO.HERED.MONO_RATIO",),
        ),
        Model(
            "HERED.DI_PROB",
            "BIO.HERED.DI_PROB",
            CH,
            "Find the probability of a combination of traits in a two-gene cross",
            "punnett_square",
            "product_rule",
            "bio.punnett_grid",
            "bio.allele_shares",
            {"pair": DI_PAIRS, "cross": DI_CROSSES, "variant": tuple(_DI_PROB)},
            _di_prob,
            g.solve_grid,
            g.solve_shares,
            ("BIO.HERED.DI_RATIO", "BIO.HERED.MONO_PROB"),
        ),
        Model(
            "HERED.TEST_CROSS",
            "BIO.HERED.TEST_CROSS",
            CH,
            "Work out the genotype of a parent from the offspring of a test cross",
            "punnett_square",
            "product_rule",
            "bio.punnett_grid",
            "bio.allele_shares",
            {"pair": DI_PAIRS, "key": _CANDS},
            _test_cross,
            g.solve_grid,
            g.solve_shares,
            ("BIO.HERED.DI_RATIO",),
        ),
        Model(
            "HERED.COUNTS_MONO",
            "BIO.HERED.COUNTS_MONO",
            CH,
            "Predict how many offspring show a trait in a single-gene cross",
            "punnett_square",
            "product_rule",
            "bio.punnett_grid",
            "bio.allele_shares",
            {
                "t": MONO_TRAITS,
                "cross": MONO_CROSSES,
                "variant": ("dom", "rec"),
                "N": ("40", "80", "160", "200", "400", "800"),
            },
            _counts_mono,
            solve_count_a,
            solve_count_b,
            ("BIO.HERED.MONO_PROB",),
        ),
        Model(
            "HERED.COUNTS_DI",
            "BIO.HERED.COUNTS_DI",
            CH,
            "Predict how many offspring show a pair of traits in a two-gene cross",
            "punnett_square",
            "product_rule",
            "bio.punnett_grid",
            "bio.allele_shares",
            {
                "t": DI_PAIRS,
                "cross": DI_CROSSES,
                "variant": ("both_dom", "dom_rec", "both_rec"),
                "N": ("64", "160", "320", "640", "1600"),
            },
            _counts_di,
            solve_count_a,
            solve_count_b,
            ("BIO.HERED.DI_PROB",),
        ),
        Model(
            "HERED.GAMETES",
            "BIO.HERED.GAMETES",
            CH,
            "Count gamete types, Punnett square boxes and offspring classes",
            "gamete_enumeration",
            "heterozygous_gene_count",
            "bio.gamete_sets",
            "bio.gene_rule",
            {
                "t": (*MONO_TRAITS, *DI_PAIRS),
                "variant": _GAM_VARIANTS,
                "case": (*_PARENTS_SINGLE, "Hh,Hh", "Hh,hh", "HH,Hh", "HH,hh", *DI_CROSSES),
            },
            _gametes,
            solve_gametes_a,
            solve_gametes_b,
            ("BIO.HERED.MONO_RATIO",),
        ),
        Model(
            "HERED.SEX_SEQ",
            "BIO.HERED.SEX_SEQ",
            CH,
            "Find the probability of a pattern of boys and girls among several children",
            "counting_equally_likely",
            "list_every_sequence",
            "bio.counting",
            "bio.listing",
            {
                "variant": (
                    "exactly_k",
                    "all_girls",
                    "next_after_run",
                    "at_least_one_boy",
                    "both_sexes",
                ),
                "n": ("2", "3", "4", "5"),
                "k": ("1", "2", "3", "4"),
            },
            _sex_seq,
            solve_sex_a,
            solve_sex_b,
        ),
    )
}
