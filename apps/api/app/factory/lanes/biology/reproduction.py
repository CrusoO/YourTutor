# ruff: noqa: E501
"""How do Organisms Reproduce models: counting cells, chromosome arithmetic, fragmentation.

Each stem states the rule it needs (every cell splits in two, a gamete has half the chromosomes
of a body cell, every piece grows into a new organism), so the item is arithmetic on a stated
model of reproduction and never asks the learner to recall a fact.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.lanes.biology.common import (
    CHAPTERS,
    Model,
    number_answer,
    numeric_draft,
    words,
)

CH = CHAPTERS["REPRO"]

MISC: dict[str, tuple[str, str]] = {
    "LINEAR_GROWTH": (
        "Treats repeated doubling as adding the same amount each round",
        "You may have added the same number each round. Doubling doubles the whole population each time.",
    ),
    "ONE_ROUND_LESS": (
        "Counts one round too few",
        "You may have stopped one round early. Count every round of division.",
    ),
    "ONE_ROUND_MORE": (
        "Counts one round too many",
        "You may have counted one round too many. Count only the rounds that take place.",
    ),
    "BASE_AND_EXPONENT_SWAPPED": (
        "Squares the number of rounds instead of doubling that many times",
        "You may have squared the number of rounds. Doubling n times means multiplying by 2, n times.",
    ),
    "ADDED_NOT_DOUBLED": (
        "Adds the number of rounds to the cells",
        "You may have added the number of rounds. Each round multiplies the cells by 2.",
    ),
    "TIME_AS_ROUNDS": (
        "Uses the time in minutes as the number of rounds",
        "You may have used the minutes as rounds. Divide the time by the time one round takes.",
    ),
    "BINARY_ASSUMED": (
        "Uses two daughter cells instead of the number given",
        "You may have split each cell into two. This cell splits into more daughter cells at once.",
    ),
    "FACTOR_AS_ROUNDS": (
        "Gives the growth factor as the number of rounds",
        "You may have given how many times larger the culture is. The question asks how many rounds that took.",
    ),
    "HALVED_ONCE": (
        "Divides by two once",
        "You may have divided by two one time. Keep halving until you reach the start.",
    ),
    "FACTOR_TIMES_TIME": (
        "Multiplies the growth factor by the time of one round",
        "You may have used the growth factor as the number of rounds. Count the rounds first.",
    ),
    "TIME_LEFT_OUT": (
        "Gives the number of rounds as the time",
        "You may have stopped at the number of rounds. Multiply by the time of one round.",
    ),
    "GAMETE_DOUBLED": (
        "Doubles the number of chromosomes",
        "You may have doubled it. A gamete has half the chromosomes of a body cell.",
    ),
    "GAMETE_SAME_AS_BODY": (
        "Gives a gamete the same number as a body cell",
        "You may have copied the body number. A gamete has half of it.",
    ),
    "GAMETE_QUARTERED": (
        "Halves the number twice",
        "You may have halved two times. Halve it only once.",
    ),
    "ZYGOTE_AT_GAMETE_NUMBER": (
        "Gives the zygote the number of one gamete",
        "You may have used one gamete's number. A zygote gets the chromosomes of both gametes.",
    ),
    "ZYGOTE_DOUBLED_TWICE": (
        "Doubles the number twice",
        "You may have doubled twice. The zygote has the sum of the two gametes, which is one doubling.",
    ),
    "HALVED_BY_MITOSIS": (
        "Halves the chromosomes at mitosis",
        "You may have halved the number. A cell made by mitosis keeps the same number.",
    ),
    "DOUBLED_BY_MITOSIS": (
        "Doubles the chromosomes at mitosis",
        "You may have doubled the number. A cell made by mitosis keeps the same number.",
    ),
    "PER_CELL_ONLY": (
        "Gives the number in one cell instead of the total",
        "You may have given the number for one cell. The question asks for the total in all the cells.",
    ),
    "CELLS_ONLY": (
        "Gives the number of cells instead of the chromosomes",
        "You may have counted the cells. Multiply by the chromosomes in each cell.",
    ),
    "ROUNDS_MULTIPLIED_NOT_DOUBLED": (
        "Multiplies by the number of rounds",
        "You may have multiplied by the rounds. The cells double at every round.",
    ),
    "SAME_AS_CUTS": (
        "Gives the number of cuts as the number of pieces",
        "You may have counted the cuts. One more piece than cuts is made.",
    ),
    "CUTS_AS_PIECES_MINUS_TWO": (
        "Takes two away from the pieces",
        "You may have taken away too many. One cut fewer than the number of pieces is needed.",
    ),
    "TWO_PIECES_PER_CUT": (
        "Assumes every cut makes two new pieces",
        "You may have doubled the cuts. Each cut adds only one piece.",
    ),
    "PARENT_NOT_COUNTED": (
        "Leaves the original organism out",
        "You may have counted only the new ones. The original organism is still there.",
    ),
    "ADDED_NOT_MULTIPLIED": (
        "Adds where the pieces multiply",
        "You may have added the two numbers of pieces. Every piece is cut again, so multiply.",
    ),
    "FIRST_ROUND_ONLY": (
        "Counts only the first round",
        "You may have stopped after the first round. Each new organism is cut again in the second round.",
    ),
}


def mc(name: str) -> str:
    if name not in MISC:
        raise KeyError(name)
    return f"BIO.MC.REPRO.{name}"


# ---------------------------------------------------------------- FISSION (counting cells)

CELLS = {
    "0": "an amoeba culture",
    "1": "a bacterial culture",
    "2": "a culture of single-celled organisms",
}
LIMIT = 100000


def _fission(params: Mapping[str, str]) -> Any:  # noqa: PLR0911
    variant = params["variant"]
    n, n0, d, k = int(params["n"]), int(params["n0"]), int(params["d"]), int(params["k"])
    culture = CELLS[params["org"]]
    if variant != "multiple_fission" and k != 3:
        return "k_is_not_used_by_this_variant"
    if variant == "multiple_fission" and n > 4:
        return "too_many_rounds_for_multiple_fission"
    if variant not in ("after_time", "time_needed") and d != 20:
        return "d_is_not_used_by_this_variant"
    base = 2 if variant != "multiple_fission" else k
    count = n0 * base**n
    if count > LIMIT:
        return "culture_too_large"
    rule = "Assume that every cell divides into two cells in each round of division, that all the cells divide together, and that no cell dies."
    if variant == "multiple_fission":
        rule = f"Assume that in each round every cell splits into {k} daughter cells at once, that all the cells split together, and that no cell dies."
    start = f"{culture.capitalize()} starts with {n0} cell{'s' if n0 > 1 else ''}."
    bio: dict[str, Any] = {
        "model": "REPRO.FISSION",
        "variant": variant,
        "n0": n0,
        "base": base,
        "rounds": n,
        "d": d,
        "unit": "cells",
    }
    wrongs: list[tuple[str, Any]]
    if variant in ("after_divisions", "multiple_fission"):
        stem = f"{start} {rule} How many cells are there after {n} round{'s' if n > 1 else ''} of division?"
        value, unit = Fraction(count), "cells"
        wrongs = [
            ("LINEAR_GROWTH", n0 * base * n),
            ("ONE_ROUND_LESS", n0 * base ** (n - 1)),
            ("ONE_ROUND_MORE", n0 * base ** (n + 1)),
            ("BASE_AND_EXPONENT_SWAPPED", n0 * n**base),
            ("ADDED_NOT_DOUBLED", n0 + n),
        ]
        if variant == "multiple_fission":
            wrongs.append(("BINARY_ASSUMED", n0 * 2**n))
        hints = [
            "Each round multiplies the number of cells by the same number.",
            "Multiply the starting number of cells by that number once for each round of division.",
            f"There are {words(n)} round{'s' if n > 1 else ''} of division, so the multiplying is done {words(n)} time{'s' if n > 1 else ''}.",
        ]
        coeff, const = Fraction(1), value
    elif variant == "after_time":
        total = n * d
        stem = f"{start} {rule} One round of division takes {d} minutes. How many cells are there after {total} minutes?"
        value, unit = Fraction(count), "cells"
        wrongs = [
            ("TIME_AS_ROUNDS", n0 * total),
            ("LINEAR_GROWTH", n0 * 2 * n),
            ("ONE_ROUND_LESS", n0 * 2 ** (n - 1)),
            ("ONE_ROUND_MORE", n0 * 2 ** (n + 1)),
            ("ADDED_NOT_DOUBLED", n0 + n),
        ]
        hints = [
            "First find how many rounds of division fit into the time.",
            "Divide the total time by the time one round takes, then multiply the cells by 2 once for each round.",
            f"Each round takes {d} minutes.",
        ]
        coeff, const = Fraction(1), value
    elif variant == "divisions_needed":
        if n < 2:
            return "needs_two_or_more_rounds"
        stem = f"{start} {rule} After some rounds there are {count} cells. How many rounds of division took place?"
        value, unit = Fraction(n), "rounds"
        wrongs = [
            ("FACTOR_AS_ROUNDS", Fraction(count, n0)),
            ("ONE_ROUND_LESS", n - 1),
            ("ONE_ROUND_MORE", n + 1),
            ("HALVED_ONCE", Fraction(count, 2 * n0)),
        ]
        hints = [
            "Find how many times larger the culture has become than at the start.",
            "Ask how many times 2 must be multiplied by itself to give that number.",
            "Keep halving the factor until you reach 1, and count the halvings.",
        ]
        coeff, const = Fraction(1), value
        bio["target"] = count
    else:  # time_needed
        if n < 2:
            return "needs_two_or_more_rounds"
        stem = f"{start} {rule} One round of division takes {d} minutes. How many minutes does it take for the culture to reach {count} cells?"
        value, unit = Fraction(n * d), "minutes"
        wrongs = [
            ("FACTOR_TIMES_TIME", Fraction(count, n0) * d),
            ("TIME_LEFT_OUT", n),
            ("ONE_ROUND_LESS", (n - 1) * d),
            ("ONE_ROUND_MORE", (n + 1) * d),
        ]
        hints = [
            "First find how many rounds of division are needed to reach that number of cells.",
            "Then multiply the number of rounds by the time one round takes.",
            f"Each round takes {d} minutes.",
        ]
        coeff, const = Fraction(1), value
        bio["target"] = count
    steps = {
        "after_divisions": [
            f"Each round multiplies the cells by 2, so the cells are multiplied by 2, {n} time{'s' if n > 1 else ''}.",
            f"{n0} x 2 to the power {n} = {count}.",
        ],
        "multiple_fission": [
            f"Each round multiplies the cells by {k}, so the cells are multiplied by {k}, {n} time{'s' if n > 1 else ''}.",
            f"{n0} x {k} to the power {n} = {count}.",
        ],
        "after_time": [
            f"The number of rounds is {n * d} divided by {d}, which is {n}.",
            f"{n0} x 2 to the power {n} = {count}.",
        ],
        "divisions_needed": [
            f"The culture grew by a factor of {count // n0}.",
            f"2 multiplied by itself {n} times gives {count // n0}, so there were {n} rounds.",
        ],
        "time_needed": [
            f"The culture grew by a factor of {count // n0}, which takes {n} rounds.",
            f"{n} rounds of {d} minutes take {n * d} minutes.",
        ],
    }[variant]
    return numeric_draft(
        variant=variant, bio=bio, coeff=coeff, const=const, value=value, unit=unit, stem=stem,
        hints=hints, steps=steps, wrongs=[(a, Fraction(b)) for a, b in wrongs], difficulty=0.45, role="apply",
        prediction="Before you calculate, will the answer be a little more or a lot more than the starting number?",
        features=["exponential_growth"],
    )  # fmt: skip


def solve_fission_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    n0, base, rounds, d, v = (
        int(bio["n0"]),
        int(bio["base"]),
        int(bio["rounds"]),
        int(bio["d"]),
        bio["variant"],
    )
    if v in ("after_divisions", "multiple_fission", "after_time"):
        return number_answer(Fraction(n0 * base**rounds), "cells")
    if v == "divisions_needed":
        factor = int(bio["target"]) // n0
        return number_answer(Fraction(factor.bit_length() - 1), "rounds")
    return number_answer(Fraction((int(bio["target"]) // n0).bit_length() - 1) * d, "minutes")


def solve_fission_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    n0, base, rounds, d, v = (
        int(bio["n0"]),
        int(bio["base"]),
        int(bio["rounds"]),
        int(bio["d"]),
        bio["variant"],
    )
    if v in ("after_divisions", "multiple_fission"):
        cells = n0
        for _ in range(rounds):  # every cell is replaced by `base` cells
            cells = cells - cells + cells * base
        return number_answer(Fraction(cells), "cells")
    if v == "after_time":
        cells, clock = n0, 0
        while clock < rounds * d:  # run the clock minute by minute
            clock += 1
            if clock % d == 0:
                cells *= 2
        return number_answer(Fraction(cells), "cells")
    cells, done = n0, 0
    while cells < int(bio["target"]):
        cells *= 2
        done += 1
    return number_answer(
        Fraction(done if v == "divisions_needed" else done * d),
        "rounds" if v == "divisions_needed" else "minutes",
    )


# ---------------------------------------------------------------- CHROMOSOMES

RULES = "A gamete has half the number of chromosomes of a body cell. A zygote forms when a sperm and an egg join. A cell made by mitosis has the same number of chromosomes as the cell that divided."
ORGS = {
    "0": "a certain insect species",
    "1": "a certain fish species",
    "2": "a certain flowering plant species",
}


def _chromosomes(params: Mapping[str, str]) -> Any:
    variant, m, r = params["variant"], int(params["m"]), int(params["r"])
    org = ORGS[params["org"]]
    if variant != "embryo_total" and r != 2:
        return "r_is_not_used_by_this_variant"
    bio: dict[str, Any] = {"model": "REPRO.CHROMOSOMES", "variant": variant, "m": m, "r": r}
    wrongs: list[tuple[str, Any]]
    if variant == "gamete_n":
        stem = f"{RULES} In {org}, each body cell has {m} chromosomes. How many chromosomes does one gamete have?"
        value = Fraction(m, 2)
        wrongs = [
            ("GAMETE_DOUBLED", 2 * m),
            ("GAMETE_SAME_AS_BODY", m),
            ("GAMETE_QUARTERED", Fraction(m, 4)),
        ]
        hints = [
            "Gametes carry only half of the chromosomes of a body cell.",
            "Halve the number of chromosomes in the body cell.",
            "Halving a number means dividing it by 2.",
        ]
        steps = [f"A gamete has half the chromosomes of a body cell: {m} divided by 2 = {m // 2}."]
    elif variant == "zygote_2n":
        stem = f"{RULES} In {org}, each gamete has {m} chromosomes. How many chromosomes does the zygote have?"
        value = Fraction(2 * m)
        wrongs = [
            ("ZYGOTE_AT_GAMETE_NUMBER", m),
            ("ZYGOTE_DOUBLED_TWICE", 4 * m),
            ("GAMETE_SAME_AS_BODY", 3 * m),
        ]
        hints = [
            "The zygote gets the chromosomes of the sperm and of the egg.",
            "Add the chromosomes that come from the sperm and from the egg.",
            "Both gametes have the same number of chromosomes.",
        ]
        steps = [
            f"The sperm gives {m} chromosomes and the egg gives {m}, so the zygote has {m} + {m} = {2 * m}."
        ]
    elif variant == "after_mitosis":
        stem = f"{RULES} In {org}, a body cell has {2 * m} chromosomes and divides by mitosis. How many chromosomes does each new cell have?"
        value = Fraction(2 * m)
        wrongs = [
            ("HALVED_BY_MITOSIS", m),
            ("DOUBLED_BY_MITOSIS", 4 * m),
            ("GAMETE_QUARTERED", Fraction(m, 2)),
        ]
        hints = [
            "Think about what the rule says about cells made by mitosis.",
            "Compare the new cell with the cell that divided.",
            "The new cells are copies of the cell that divided.",
        ]
        steps = [
            f"A cell made by mitosis has the same number of chromosomes as the cell that divided: {2 * m}."
        ]
    else:
        stem = f"{RULES} In {org}, each gamete has {m} chromosomes. The zygote divides by mitosis {r} times, so that all the cells divide together each time. How many chromosomes are there in total, counting all the cells of the embryo?"
        cells = 2**r
        value = Fraction(2 * m * cells)
        wrongs = [
            ("PER_CELL_ONLY", 2 * m),
            ("CELLS_ONLY", cells),
            ("ROUNDS_MULTIPLIED_NOT_DOUBLED", 2 * m * r),
            ("ZYGOTE_AT_GAMETE_NUMBER", m * cells),
            ("DOUBLED_BY_MITOSIS", 2 * m * 2 * r),
        ]
        hints = [
            "First find the number of chromosomes in the zygote, then the number of cells after the divisions.",
            "All the cells have the same number of chromosomes, so multiply the number of chromosomes in one cell by the number of cells.",
            f"If all the cells divide together, the number of cells doubles {words(r)} time{'s' if r > 1 else ''}.",
        ]
        steps = [
            f"The zygote has {m} + {m} = {2 * m} chromosomes, and every cell made by mitosis keeps that number.",
            f"After {r} rounds there are 2 to the power {r} = {cells} cells.",
            f"The total is {cells} x {2 * m} = {int(value)} chromosomes.",
        ]
    return numeric_draft(
        variant=variant, bio=bio, coeff=Fraction(1), const=value, value=value, unit="chromosomes", stem=stem,
        hints=hints, steps=steps, wrongs=[(a, Fraction(b)) for a, b in wrongs if Fraction(b).denominator == 1],
        difficulty=0.4, role="procedure",
        prediction="Before you calculate, will the number be larger or smaller than the number given?",
        features=["chromosome_number"],
    )  # fmt: skip


def solve_chrom_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    m, r, v = int(bio["m"]), int(bio["r"]), bio["variant"]
    value = {
        "gamete_n": Fraction(m, 2),
        "zygote_2n": Fraction(2 * m),
        "after_mitosis": Fraction(2 * m),
        "embryo_total": Fraction(2 * m * 2**r),
    }[v]
    return number_answer(value, "chromosomes")


def solve_chrom_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    m, r, v = int(bio["m"]), int(bio["r"]), bio["variant"]
    if v == "gamete_n":  # pair the chromosomes up; a gamete takes one of each pair
        body = list(range(m))
        pairs = [body[i : i + 2] for i in range(0, len(body), 2)]
        return number_answer(Fraction(len(pairs)), "chromosomes")
    sperm, egg = list(range(m)), list(range(m))
    zygote = sperm + egg
    if v == "zygote_2n":
        return number_answer(Fraction(len(zygote)), "chromosomes")
    if v == "after_mitosis":
        return number_answer(Fraction(len(list(zygote))), "chromosomes")
    embryo = [len(zygote)]
    for _ in range(r):
        embryo = [c for cell in embryo for c in (cell, cell)]
    return number_answer(Fraction(sum(embryo)), "chromosomes")


# ---------------------------------------------------------------- FRAGMENTS

BODIES = {"0": "a long algal filament", "1": "a flatworm", "2": "a thin green water plant"}


def _fragments(params: Mapping[str, str]) -> Any:
    variant, a, b = params["variant"], int(params["a"]), int(params["b"])
    body = BODIES[params["org"]]
    rule = "Assume that every piece grows into a complete new organism."
    bio: dict[str, Any] = {"model": "REPRO.FRAGMENTS", "variant": variant, "a": a, "b": b}
    if variant != "two_rounds" and b != 2:
        return "b_is_not_used_by_this_variant"
    wrongs: list[tuple[str, Any]]
    if variant == "pieces_from_cuts":
        stem = f"{body.capitalize()} is cut straight across at {a} different places along its length. {rule} How many new organisms can grow?"
        value, unit = Fraction(a + 1), "organisms"
        wrongs = [("SAME_AS_CUTS", a), ("TWO_PIECES_PER_CUT", 2 * a), ("PARENT_NOT_COUNTED", a + 2)]
        hints = [
            "Think about how many pieces one cut makes, and how a second cut changes the number of pieces.",
            "Each new cut divides one piece into two, so it adds one piece to the number you had.",
            "With no cuts there is one piece, the whole organism.",
        ]
        steps = [
            f"With no cut there is 1 piece, and each of the {a} cuts adds 1 piece.",
            f"The number of pieces is 1 + {a} = {a + 1}, and each grows into a new organism.",
        ]
    elif variant == "cuts_for_pieces":
        stem = f"{body.capitalize()} is cut straight across at several places along its length, and this makes {a} pieces. {rule} How many cuts were made?"
        value, unit = Fraction(a - 1), "cuts"
        wrongs = [
            ("SAME_AS_CUTS", a),
            ("CUTS_AS_PIECES_MINUS_TWO", a - 2),
            ("PARENT_NOT_COUNTED", a + 1),
        ]
        hints = [
            "Think about how many pieces one cut makes, and how a second cut changes the number of pieces.",
            "Each cut adds one piece, and with no cuts there is one piece.",
            "The number of cuts is one less than the number of pieces.",
        ]
        steps = [
            f"With no cut there is 1 piece, and each cut adds 1 piece, so {a} pieces need {a - 1} cuts."
        ]
    elif variant == "after_budding":
        stem = f"A hydra has {a} buds, and every bud grows and separates as a new hydra. How many hydras are there altogether, counting the parent?"
        value, unit = Fraction(a + 1), "hydras"
        wrongs = [("PARENT_NOT_COUNTED", a), ("TWO_PIECES_PER_CUT", 2 * a), ("SAME_AS_CUTS", a + 2)]
        hints = [
            "Each bud becomes one new organism, and the parent stays.",
            "Add the new organisms to the parent.",
            "The parent counts as one.",
        ]
        steps = [
            f"The {a} buds give {a} new hydras, and the parent is still there: {a} + 1 = {a + 1}."
        ]
    else:
        stem = f"{body.capitalize()} is cut into {a} pieces. {rule} Later, every one of these new organisms is cut into {b} pieces in the same way. How many organisms can grow from the second round of cutting?"
        value, unit = Fraction(a * b), "organisms"
        wrongs = [
            ("ADDED_NOT_MULTIPLIED", a + b),
            ("FIRST_ROUND_ONLY", a),
            ("PARENT_NOT_COUNTED", a * b + a),
            ("TWO_PIECES_PER_CUT", a * b * 2),
        ]
        hints = [
            "After the first round, there are several organisms, and every one of them is cut again.",
            "Each organism gives the same number of pieces, so combine the two counts by multiplying them.",
            "Count the organisms after the first round, then count the pieces that each of them makes.",
        ]
        steps = [
            f"After the first round there are {a} organisms.",
            f"Each is cut into {b} pieces, so there are {a} x {b} = {a * b} organisms.",
        ]
    return numeric_draft(
        variant=variant, bio=bio, coeff=Fraction(1), const=value, value=value, unit=unit, stem=stem,
        hints=hints, steps=steps, wrongs=[(x, Fraction(y)) for x, y in wrongs], difficulty=0.3, role="procedure",
        prediction="Before you count, will there be more pieces than cuts, or fewer?", features=["regeneration"],
    )  # fmt: skip


def solve_frag_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    a, b, v = int(bio["a"]), int(bio["b"]), bio["variant"]
    value, unit = {
        "pieces_from_cuts": (a + 1, "organisms"), "cuts_for_pieces": (a - 1, "cuts"),
        "after_budding": (a + 1, "hydras"), "two_rounds": (a * b, "organisms"),
    }[v]  # fmt: skip
    return number_answer(Fraction(value), unit)


def solve_frag_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    a, b, v = int(bio["a"]), int(bio["b"]), bio["variant"]
    if v == "cuts_for_pieces":
        pieces, cuts = 1, 0
        while pieces < a:  # make one cut at a time; every cut splits one piece in two
            pieces += 1
            cuts += 1
        return number_answer(Fraction(cuts), "cuts")
    if v == "after_budding":
        hydras = ["parent"]
        for i in range(a):
            hydras.append(f"bud{i}")
        return number_answer(Fraction(len(hydras)), "hydras")
    if v == "pieces_from_cuts":
        parts = [1]
        for _ in range(a):  # each cut adds one piece
            parts.append(1)
        return number_answer(Fraction(len(parts)), "organisms")
    first = [1] * a
    second = [piece for _ in first for piece in [1] * b]
    return number_answer(Fraction(len(second)), "organisms")


REPRO_MODELS: dict[str, Model] = {
    m.id: m
    for m in (
        Model(
            "REPRO.FISSION", "BIO.REPRO.FISSION", CH,
            "Count the cells after rounds of binary or multiple fission",
            "repeated_doubling", "round_by_round_simulation", "bio.doubling_closed_form", "bio.doubling_simulation",
            {"variant": ("after_divisions", "after_time", "divisions_needed", "time_needed", "multiple_fission"),
             "n": ("2", "3", "4", "5", "6", "8"), "n0": ("1", "2", "3", "5", "10"), "d": ("20", "30", "45", "60"),
             "k": ("3", "4", "8"), "org": ("0", "1", "2")},
            _fission, solve_fission_a, solve_fission_b,
        ),
        Model(
            "REPRO.CHROMOSOMES", "BIO.REPRO.CHROMOSOMES", CH,
            "Work out chromosome numbers in gametes, zygotes and dividing cells",
            "stated_rules", "list_the_chromosomes", "bio.chromosome_rules", "bio.chromosome_lists",
            {"variant": ("gamete_n", "zygote_2n", "after_mitosis", "embryo_total"),
             "m": ("4", "6", "8", "10", "12", "14", "16", "20", "24", "30"), "r": ("2", "3", "4"), "org": ("0", "1", "2")},
            _chromosomes, solve_chrom_a, solve_chrom_b,
        ),
        Model(
            "REPRO.FRAGMENTS", "BIO.REPRO.FRAGMENTS", CH,
            "Count the new organisms made by fragmentation, regeneration and budding",
            "counting_pieces", "make_the_cuts_one_by_one", "bio.pieces_closed_form", "bio.pieces_simulation",
            {"variant": ("pieces_from_cuts", "cuts_for_pieces", "after_budding", "two_rounds"),
             "a": ("2", "3", "4", "5", "6", "7", "8", "10"), "b": ("2", "3", "4", "5"), "org": ("0", "1", "2")},
            _fragments, solve_frag_a, solve_frag_b,
        ),
    )
}  # fmt: skip
