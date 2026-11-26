# ruff: noqa: E501
"""Our Environment models: energy flow with the ten percent law, trophic levels, accumulation.

The ten percent law is stated inside every stem as an assumption, so each item is arithmetic on
numbers it gives. Chains are fixed lists of organisms; a trophic level is a position in the list
under the definition stated in the stem. Nothing needs recall.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.lanes.biology.common import (
    CHAPTERS,
    Draft,
    Model,
    algebra_spec,
    dec,
    num_text,
    number_answer,
    numeric_draft,
    qs,
    words,
)

CH = CHAPTERS["ENV"]

MISC: dict[str, tuple[str, str]] = {
    "TEN_PERCENT_ONCE": (
        "Applies the ten percent step only once",
        "You may have taken ten percent one time. Every step along the chain takes ten percent of what the level before it had.",
    ),
    "NINETY_PERCENT_PASSED": (
        "Passes on ninety percent instead of ten percent",
        "You may have kept ninety percent at each step. Only ten percent passes to the next level.",
    ),
    "ONE_TRANSFER_TOO_MANY": (
        "Counts one transfer too many",
        "You may have counted the levels instead of the steps between them. The first level has no step before it.",
    ),
    "ONE_TRANSFER_TOO_FEW": (
        "Counts one transfer too few",
        "You may have missed a step between two levels. Count each move up the chain.",
    ),
    "ENERGY_MULTIPLIED_UP": (
        "Multiplies where the energy shrinks",
        "You may have multiplied the energy as you went up the chain. Each level has less energy than the one before.",
    ),
    "ENERGY_DIVIDED_BACK": (
        "Divides where the energy must grow",
        "You may have divided as you went back down the chain. The earlier levels hold more energy.",
    ),
    "ENERGY_LOST_FOR_PASSED": (
        "Gives the energy lost instead of the energy passed on",
        "You may have given the part that is lost. Check which amount the question asks for.",
    ),
    "ENERGY_PASSED_FOR_LOST": (
        "Gives the energy passed on instead of the energy lost",
        "You may have given the part that moves on. Check which amount the question asks for.",
    ),
    "PERCENT_LEFT_AS_TEN": (
        "Uses ten percent as the energy lost",
        "You may have taken ten percent as the loss. Ten percent is what passes on, and the rest is lost.",
    ),
    "FIRST_STEP_ONLY": (
        "Counts the loss of the first step only",
        "You may have counted the loss at one step. The loss builds up over every step.",
    ),
    "ENERGY_AT_LEVEL_GIVEN": (
        "Gives the energy left at the level instead of the loss",
        "You may have given the energy that remains. The question asks how much was lost on the way.",
    ),
    "FRACTION_FOR_PERCENT": (
        "Writes the share as a fraction of one, not a percentage",
        "You may have left the share as a number below 1. Multiply by 100 for a percentage.",
    ),
    "LEVEL_USED_AS_CONSUMER_ORDER": (
        "Uses the level number as the consumer order",
        "You may have used the level number as the consumer order. The producer is level 1, so the first consumer is at level 2.",
    ),
    "CHAIN_LENGTH_GIVEN": (
        "Gives the length of the chain instead of the position asked",
        "You may have given how many organisms there are. The question asks about one organism in the chain.",
    ),
    "COUNTS_PRODUCER_AS_CONSUMER": (
        "Counts the producer as a consumer",
        "You may have counted the producer. A producer makes its own food and is not a consumer.",
    ),
    "ORDER_TOO_LOW": (
        "Chooses the consumer one place too early",
        "You may have counted from the wrong end of the chain.",
    ),
    "ORDER_TOO_HIGH": (
        "Chooses the consumer one place too late",
        "You may have counted one place too far along the chain.",
    ),
    "ORGANISM_COUNT_FOR_CONSUMERS": (
        "Counts every organism as a consumer",
        "You may have counted all the organisms. The first one is the producer.",
    ),
    "ORGANISMS_FOR_STEPS": (
        "Counts organisms instead of the steps between them",
        "You may have counted the organisms. Each step joins two neighbours, so there is one fewer.",
    ),
    "ADDED_NOT_MULTIPLIED": (
        "Adds where the amount is multiplied",
        "You may have added the factor at each step. The amount is multiplied by the factor at each step.",
    ),
    "ONE_STEP_ONLY": (
        "Applies the factor once",
        "You may have used the factor one time. It applies at every step up the chain.",
    ),
    "FACTOR_USED_ONCE_PER_LEVEL": (
        "Applies the factor once for every level, counting the first",
        "You may have used one step too many. The first level has no step before it.",
    ),
    "DIVIDED_NOT_MULTIPLIED": (
        "Divides where the amount grows",
        "You may have divided. The amount grows by the factor at each step up the chain.",
    ),
    "MULTIPLIED_NOT_DIVIDED": (
        "Multiplies where the amount must shrink back",
        "You may have multiplied when going back to the earlier level. Going back down the chain divides.",
    ),
}

CHAINS: tuple[tuple[str, ...], ...] = (
    ("grass", "grasshopper", "frog", "snake", "hawk"),
    ("algae", "water snail", "small fish", "heron"),
    ("wheat", "mouse", "snake", "eagle"),
    ("phytoplankton", "zooplankton", "small fish", "large fish", "seabird"),
    ("grass", "deer", "tiger"),
    ("leaves", "caterpillar", "small bird", "hawk"),
)
TEN = "Assume that only 10 percent of the energy at one trophic level passes to the next level."


def mc(name: str) -> str:
    if name not in MISC:
        raise KeyError(name)
    return f"BIO.MC.ENV.{name}"


def _chain(params: Mapping[str, str]) -> tuple[str, ...]:
    return CHAINS[int(params["chain"])]


def _chain_text(chain: tuple[str, ...]) -> str:
    return ", ".join(chain[:-1]) + " and " + chain[-1] if len(chain) > 1 else chain[0]


def _chain_arrows(chain: tuple[str, ...]) -> str:
    return " → ".join(chain)


# ---------------------------------------------------------------- TEN_PERCENT


def _ten(params: Mapping[str, str]) -> Draft | str:  # noqa: PLR0911
    variant, unit = params["variant"], params["unit"]
    chain = _chain(params)
    e0, lvl = Fraction(params["e0"]), int(params["n"])
    if lvl > len(chain):
        return "chain_is_too_short_for_the_level"
    if variant != "level_from_level" and params["m"] != "1":
        return "m_is_not_used_by_this_variant"
    org = chain[lvl - 1]
    first = chain[0]
    steps_n = lvl - 1
    if variant == "level_n":
        down, given, steps_n = True, e0, lvl - 1
        if steps_n < 2:
            return "needs_two_or_more_steps"
        value = e0 / 10**steps_n
        stem = f"In the food chain {_chain_arrows(chain)}, the {first} captures {num_text(e0, unit)} of energy. {TEN} How much energy reaches the {org}?"
        hints = [
            "Each step along the food chain keeps one tenth of the energy of the level before it.",
            "Count the steps from the first level to the level asked about, then apply the one tenth for every step.",
            f"Going from the first level to level {words(lvl)} takes {words(steps_n)} steps.",
        ]
        wrongs = [
            ("TEN_PERCENT_ONCE", e0 / 10), ("NINETY_PERCENT_PASSED", e0 * Fraction(9, 10) ** steps_n),
            ("ONE_TRANSFER_TOO_MANY", e0 / 10 ** (steps_n + 1)), ("ONE_TRANSFER_TOO_FEW", e0 / 10 ** (steps_n - 1)),
            ("ENERGY_MULTIPLIED_UP", e0 * 10),
        ]  # fmt: skip
    elif variant == "next_level":
        if lvl >= len(chain):
            return "no_next_level"
        down, given, steps_n = True, e0, 1
        value = e0 / 10
        nxt = chain[lvl]
        stem = f"In the food chain {_chain_arrows(chain)}, the {org} holds {num_text(e0, unit)} of energy. {TEN} How much energy passes to the {nxt}?"
        hints = [
            "Only one tenth of the energy of a level passes to the next level.",
            "Find one tenth of the energy held by the organism, and you have the energy that passes on.",
            "One tenth of a number is the number divided by 10.",
        ]
        wrongs = [
            ("ENERGY_LOST_FOR_PASSED", e0 - value), ("NINETY_PERCENT_PASSED", e0 * Fraction(9, 10)),
            ("ENERGY_MULTIPLIED_UP", e0 * 10), ("ONE_TRANSFER_TOO_MANY", e0 / 100),
        ]  # fmt: skip
    elif variant == "producer_from_top":
        if steps_n < 1:
            return "needs_one_or_more_steps"
        down, steps_n = False, lvl - 1
        top = e0 / 10**steps_n
        if top.denominator != 1:
            return "given_energy_is_not_whole"
        given, value = top, e0
        stem = f"In the food chain {_chain_arrows(chain)}, the {org} receives {num_text(top, unit)} of energy. {TEN} How much energy did the {first} capture?"
        hints = [
            "Going up the chain, each level holds one tenth of the level before it, so going back down the chain each level holds ten times more.",
            "Count the steps between the first level and the organism named, then undo one tenth for each step.",
            f"The {org} is {words(steps_n)} step{'s' if steps_n > 1 else ''} above the {first}.",
        ]
        wrongs = [
            ("ENERGY_DIVIDED_BACK", top / 10), ("TEN_PERCENT_ONCE", top * 10),
            ("ONE_TRANSFER_TOO_MANY", top * 10 ** (steps_n + 1)), ("ONE_TRANSFER_TOO_FEW", top * 10 ** (steps_n - 1)),
            ("ENERGY_LOST_FOR_PASSED", e0 - top),
        ]  # fmt: skip
    else:  # level_from_level
        m = int(params["m"])
        if not 1 <= m < lvl:
            return "levels_not_in_order"
        steps_n = lvl - m
        down, given = True, e0
        value = e0 / 10**steps_n
        stem = f"In the food chain {_chain_arrows(chain)}, the {chain[m - 1]} holds {num_text(e0, unit)} of energy. {TEN} How much energy reaches the {org}?"
        hints = [
            "Each step along the food chain keeps one tenth of the energy of the level before it.",
            "Count the steps from the organism that holds the energy to the organism that receives it.",
            f"From the {chain[m - 1]} to the {org} takes {words(steps_n)} step{'s' if steps_n > 1 else ''}.",
        ]
        wrongs = [
            ("TEN_PERCENT_ONCE", e0 / 10), ("NINETY_PERCENT_PASSED", e0 * Fraction(9, 10) ** steps_n),
            ("ONE_TRANSFER_TOO_MANY", e0 / 10 ** (steps_n + 1)), ("ONE_TRANSFER_TOO_FEW", e0 / 10 ** max(steps_n - 1, 0)),
            ("ENERGY_MULTIPLIED_UP", e0 * 10**steps_n),
        ]  # fmt: skip
    if value.denominator != 1 or given.denominator != 1:
        return "energies_are_not_whole_numbers"
    bio = {
        "model": "ENV.TEN_PERCENT",
        "variant": variant,
        "given": qs(given),
        "transfers": steps_n,
        "direction": "down" if down else "up",
        "unit": unit,
    }
    coeff, const = (Fraction(10**steps_n), given) if down else (Fraction(1), given * 10**steps_n)
    steps = [
        f"Count the steps along the chain: {steps_n}.",
        f"Each step {'keeps one tenth of' if down else 'was one tenth of'} the energy, so {'divide' if down else 'multiply'} by 10 for each step: {num_text(given, unit)} {'divided' if down else 'multiplied'} by 10, {steps_n} time{'s' if steps_n > 1 else ''}.",
        f"The energy is {num_text(value, unit)}.",
    ]
    return numeric_draft(
        variant=variant, bio=bio, coeff=coeff, const=const, value=value, unit=unit, stem=stem,
        hints=hints, steps=steps, wrongs=wrongs, difficulty=0.35 + 0.05 * min(steps_n, 3), role="apply",
        prediction="Before you calculate, should the answer be larger or smaller than the energy given?",
        features=["ten_percent_law"],
    )  # fmt: skip


def solve_ten_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    given, n = Fraction(bio["given"]), int(bio["transfers"])
    value = given * Fraction(1, 10) ** n if bio["direction"] == "down" else given * 10**n
    return number_answer(value, bio["unit"])


def solve_ten_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    energy = Fraction(bio["given"])
    for _ in range(int(bio["transfers"])):
        if bio["direction"] == "down":
            lost = energy * 9 / 10  # nine tenths are lost at the step, the rest passes on
            energy = energy - lost
        else:
            energy = energy / (Fraction(1, 10))  # undo the step: the level was one tenth of this
    return number_answer(energy, bio["unit"])


# ---------------------------------------------------------------- ENERGY_LOST


def _lost(params: Mapping[str, str]) -> Draft | str:
    variant, unit = params["variant"], params["unit"]
    e0, n = Fraction(params["e0"]), int(params["n"])
    chain = _chain(params)
    if n > len(chain):
        return "chain_is_too_short_for_the_level"
    first, org = chain[0], chain[n - 1]
    if variant == "percent_reaching" and (params["e0"] != _E0[0] or unit != "J"):
        return "energy_is_not_used_by_this_variant"
    if variant == "lost_one_step":
        if n >= len(chain):
            return "no_next_level"
        steps_n = 1
        value = e0 * Fraction(9, 10)
        stem = f"In the food chain {_chain_arrows(chain)}, the {org} holds {num_text(e0, unit)} of energy. {TEN} How much energy is lost when energy passes from the {org} to the {chain[n]}?"
        hints = [
            "The energy that passes on is one tenth, so the rest is lost.",
            "Take the energy that passes on away from the energy the organism holds, or find nine tenths of it directly.",
            "Nine tenths of a number is the number divided by 10 and then multiplied by 9.",
        ]
        wrongs = [
            ("ENERGY_PASSED_FOR_LOST", e0 / 10),
            ("PERCENT_LEFT_AS_TEN", e0 / 10),
            ("NINETY_PERCENT_PASSED", e0 * Fraction(9, 10) ** 2),
            ("ENERGY_MULTIPLIED_UP", e0 * 10),
            ("ONE_TRANSFER_TOO_MANY", e0 * Fraction(99, 100)),
        ]
        unit_out = unit
        given = e0
        down_kind = "lost_one"
    elif variant == "lost_total":
        steps_n = n - 1
        if steps_n < 2:
            return "needs_two_or_more_steps"
        reaches = e0 / 10**steps_n
        value = e0 - reaches
        stem = f"In the food chain {_chain_arrows(chain)}, the {first} captures {num_text(e0, unit)} of energy. {TEN} How much energy is lost in total before energy reaches the {org}?"
        hints = [
            "The energy lost is the energy captured at the start minus the energy that reaches the organism.",
            "First find the energy that reaches the organism, by taking one tenth for each step.",
            f"Going from the first level to level {words(n)} takes {words(steps_n)} steps.",
        ]
        wrongs = [
            ("ENERGY_AT_LEVEL_GIVEN", reaches),
            ("FIRST_STEP_ONLY", e0 * Fraction(9, 10)),
            ("ENERGY_PASSED_FOR_LOST", e0 / 10),
            ("ONE_TRANSFER_TOO_MANY", e0 - e0 / 10 ** (steps_n + 1)),
        ]
        unit_out = unit
        given = e0
        down_kind = "lost_total"
    else:  # percent_reaching
        steps_n = n - 1
        if steps_n < 1:
            return "needs_one_or_more_steps"
        value = Fraction(100, 10**steps_n)
        stem = f"In the food chain {_chain_arrows(chain)}, {TEN[0].lower() + TEN[1:]} What percentage of the energy captured by the {first} reaches the {org}?"
        hints = [
            "A percentage is a share out of 100, so start from 100 percent at the first level.",
            "Take one tenth of the share for each step along the chain.",
            f"Going from the first level to level {words(n)} takes {words(steps_n)} step{'s' if steps_n > 1 else ''}.",
        ]
        wrongs = [
            ("ONE_TRANSFER_TOO_MANY", Fraction(100, 10 ** (steps_n + 1))),
            ("ONE_TRANSFER_TOO_FEW", Fraction(100, 10 ** (steps_n - 1))),
            ("FRACTION_FOR_PERCENT", Fraction(1, 10**steps_n)),
            ("TEN_PERCENT_ONCE", Fraction(10)),
            ("NINETY_PERCENT_PASSED", 100 * Fraction(9, 10) ** steps_n),
        ]
        unit_out = "percent"
        given = Fraction(100)
        down_kind = "percent"
    if down_kind != "percent" and (e0.denominator != 1 or value.denominator != 1):
        return "energies_are_not_whole_numbers"
    bio = {
        "model": "ENV.ENERGY_LOST",
        "variant": variant,
        "given": qs(given),
        "transfers": steps_n,
        "kind": down_kind,
        "unit": unit_out,
    }
    if down_kind == "percent":
        coeff, const = Fraction(10**steps_n), Fraction(100)
    elif down_kind == "lost_one":
        coeff, const = Fraction(10), 9 * e0
    else:
        coeff, const = Fraction(10**steps_n), e0 * (10**steps_n - 1)
    if down_kind == "lost_one":
        steps = [
            f"One tenth passes on, so nine tenths are lost: 9 x {num_text(e0, unit)} divided by 10.",
            f"The energy lost is {num_text(value, unit)}.",
        ]
    elif down_kind == "lost_total":
        left = e0 / 10**steps_n
        steps = [
            f"The energy reaching the {org} is {num_text(left, unit)}, because one tenth is kept at each of the {steps_n} steps.",
            f"The energy lost is {num_text(e0, unit)} minus {num_text(left, unit)}, which is {num_text(value, unit)}.",
        ]
    else:
        steps = [
            f"Start with 100 percent and take one tenth {steps_n} time{'s' if steps_n > 1 else ''}.",
            f"The share that reaches the {org} is {num_text(value, 'percent')}.",
        ]
    return numeric_draft(
        variant=variant, bio=bio, coeff=coeff, const=const, value=value, unit=unit_out, stem=stem,
        hints=hints, steps=steps, wrongs=wrongs, difficulty=0.5, role="apply",
        prediction="Before you calculate, will most of the energy be lost or passed on?",
        features=["ten_percent_law"],
    )  # fmt: skip


def solve_lost_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    given, n, kind = Fraction(bio["given"]), int(bio["transfers"]), bio["kind"]
    if kind == "lost_one":
        value = given * Fraction(9, 10)
    elif kind == "lost_total":
        value = given * (1 - Fraction(1, 10) ** n)
    else:
        value = given * Fraction(1, 10) ** n
    return number_answer(value, bio["unit"])


def solve_lost_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    kind, n = bio["kind"], int(bio["transfers"])
    start = Fraction(bio["given"])
    energy, lost = start, Fraction(0)
    for _ in range(n):
        passed = energy / 10
        lost += energy - passed
        energy = passed
    value = {"lost_one": lost, "lost_total": lost, "percent": energy}[kind]
    return number_answer(value, bio["unit"])


# ---------------------------------------------------------------- TROPHIC (positions in a chain)

KINDS = (
    "producer",
    "primary consumer",
    "secondary consumer",
    "tertiary consumer",
    "quaternary consumer",
)
DEFINITION = "A producer is at trophic level 1. A primary consumer eats the producer, a secondary consumer eats a primary consumer, a tertiary consumer eats a secondary consumer, and so on."


def _trophic(params: Mapping[str, str]) -> Draft | str:  # noqa: PLR0911
    variant, chain = params["variant"], _chain(params)
    size = len(chain)
    pos = int(params["pos"])
    bio: dict[str, Any] = {
        "model": "ENV.TROPHIC",
        "variant": variant,
        "chain": list(chain),
        "target": pos,
    }
    arrows = _chain_arrows(chain)
    if variant == "level_of":
        if pos < 1 or pos > size:
            return "position_outside_chain"
        value = Fraction(pos)
        stem = f"{DEFINITION} In the food chain {arrows}, at which trophic level is the {chain[pos - 1]}? Each organism in the chain is eaten by the next one."
        wrongs = [
            ("ORDER_TOO_LOW", pos - 1),
            ("ORDER_TOO_HIGH", pos + 1),
            ("CHAIN_LENGTH_GIVEN", size),
            ("ORDER_TOO_HIGH", pos + 2),
            ("ORDER_TOO_LOW", pos - 2),
        ]
        hints = [
            "Number the organisms in the chain starting from the producer, which is level 1.",
            "Each organism in the chain is eaten by the next one, so the level goes up by one at each step along the chain.",
            "Count along the chain until you reach the organism named in the question.",
        ]
        steps = [
            f"The producer, {chain[0]}, is level 1; each organism after it is one level higher.",
            f"The {chain[pos - 1]} is organism number {pos} in the chain, so it is at level {pos}.",
        ]
        key_unit, text_fn, unit = "level", (lambda v: f"level {int(v)}"), ""
    elif variant == "organism_at":
        if not 2 <= pos <= size:
            return "position_outside_chain"
        order = pos - 1
        value = Fraction(pos)
        stem = f"{DEFINITION} In the food chain {arrows}, which organism is the {KINDS[order]}? Each organism in the chain is eaten by the next one."
        wrongs = [
            ("LEVEL_USED_AS_CONSUMER_ORDER", order),
            ("ORDER_TOO_HIGH", pos + 1),
            ("ORDER_TOO_LOW", pos - 2),
            ("ORDER_TOO_HIGH", pos + 2),
            ("CHAIN_LENGTH_GIVEN", size),
        ]
        hints = [
            "A consumer order counts from the first animal that eats the producer, not from the producer itself.",
            "The primary consumer is the organism right after the producer, the secondary consumer is the one after that, and so on.",
            "Count the consumers along the chain, leaving the producer out of the count.",
        ]
        steps = [
            f"The producer is {chain[0]}. Each consumer comes after it in the chain.",
            f"The {KINDS[order]} is consumer number {order}, which is organism number {pos} in the chain: the {chain[pos - 1]}.",
        ]
        key_unit, text_fn, unit = (
            "name",
            (lambda v: chain[int(v) - 1] if 1 <= int(v) <= size else ""),
            "",
        )
    elif variant == "kind_of":
        if not 1 <= pos <= size:
            return "position_outside_chain"
        value = Fraction(pos)
        stem = f"{DEFINITION} In the food chain {arrows}, the {chain[pos - 1]} is which of the following? Each organism in the chain is eaten by the next one."
        wrongs = [
            ("LEVEL_USED_AS_CONSUMER_ORDER", pos + 1),
            ("ORDER_TOO_LOW", pos - 1),
            ("ORDER_TOO_HIGH", pos + 2),
            ("ORDER_TOO_LOW", pos - 2),
        ]
        hints = [
            "Find the organism in the chain and count how many places it is after the producer.",
            "The organism right after the producer is the first kind of consumer, the next one is the second kind, and so on.",
            "The producer itself is not a consumer.",
        ]
        steps = [
            f"The {chain[pos - 1]} is organism number {pos} in the chain, so it is at level {pos}.",
            f"The kind that matches level {pos} is the {KINDS[pos - 1]}.",
        ]
        key_unit, text_fn, unit = (
            "kind",
            (lambda v: KINDS[int(v) - 1] if 1 <= int(v) <= len(KINDS) else ""),
            "",
        )
    else:  # count variants use pos as unused (0)
        if pos != 1:
            return "position_not_used_by_this_variant"
        what = {
            "n_levels": ("How many trophic levels does this chain have?", size),
            "n_consumers": ("How many organisms in this chain are consumers?", size - 1),
            "n_steps": (
                "Energy passes from one organism to the next along this chain. How many times is energy passed on?",
                size - 1,
            ),
        }[variant]
        value = Fraction(what[1])
        stem = f"{DEFINITION} Look at the food chain {arrows}. {what[0]} Each organism in the chain is eaten by the next one."
        wrongs = [
            ("ORGANISM_COUNT_FOR_CONSUMERS", size),
            ("COUNTS_PRODUCER_AS_CONSUMER", size - 1),
            ("ORGANISMS_FOR_STEPS", size),
            ("ONE_TRANSFER_TOO_FEW", size - 2),
            ("ONE_TRANSFER_TOO_MANY", size + 1),
        ]
        hints = [
            "List the organisms in the chain from the producer onwards.",
            "Decide which of the organisms count for what the question asks, and which do not.",
            "The producer is the first organism and every other organism is a consumer.",
        ]
        steps = [
            f"There are {size} organisms in the chain, one at each level.",
            f"The producer is not a consumer, and there is one transfer between each pair of neighbours. The answer is {int(value)}.",
        ]
        key_unit, text_fn, unit = "count", (lambda v: str(int(v))), ""
        bio["target"] = 1
    _ = key_unit
    if value <= 0:
        return "answer_not_positive"
    options: list[tuple[str, dict[str, Any], str]] = []
    top = {"level_of": size, "organism_at": size, "kind_of": len(KINDS)}.get(variant, size + 1)
    for name, raw in wrongs:
        v = Fraction(raw)
        if 1 <= v <= top and v != value and text_fn(v):
            options.append((name, number_answer(v, unit), text_fn(v)))
    spec = algebra_spec("x", Fraction(1), value, bio)
    return Draft(
        variant=variant, spec=spec, answer=number_answer(value, unit), witness={"values": {"x": qs(value)}},
        stem=stem, hints=hints, steps=steps, key_text=text_fn(value), wrongs=options, difficulty=0.3,
        role="procedure", prediction="Before you count, which end of the chain is the producer?",
        tokens=[text_fn(value)], features=["food_chain"],
    )  # fmt: skip


def solve_trophic_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    chain, pos, v = bio["chain"], int(bio["target"]), bio["variant"]
    value = {"n_levels": len(chain), "n_consumers": len(chain) - 1, "n_steps": len(chain) - 1}.get(
        v, pos
    )
    return number_answer(Fraction(value))


def solve_trophic_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    chain, v = list(bio["chain"]), bio["variant"]
    level = {chain[0]: 1}  # walk the chain: each organism is one level above the one it eats
    for prey, predator in zip(chain, chain[1:], strict=False):
        level[predator] = level[prey] + 1
    if v == "n_levels":
        value = max(level.values())
    elif v == "n_consumers":
        value = sum(1 for lv in level.values() if lv > 1)
    elif v == "n_steps":
        value = len(chain) - 1
    else:
        value = level[chain[int(bio["target"]) - 1]]
    return number_answer(Fraction(value))


# ---------------------------------------------------------------- CONC_CHAIN (accumulation)


def _conc(params: Mapping[str, str]) -> Draft | str:
    variant, chain = params["variant"], _chain(params)
    c0, f, n = Fraction(params["c0"]), int(params["f"]), int(params["n"])
    if n > len(chain) or n < 2:
        return "level_outside_chain"
    steps_n = n - 1
    org, first = chain[n - 1], chain[0]
    base = (
        "A chemical that organisms cannot break down is passed along a food chain. "
        f"At each step up the chain, its concentration in the body becomes {f} times as large."
    )
    if variant == "forward":
        value, given, up = c0 * f**steps_n, c0, True
        stem = f"{base} In the food chain {_chain_arrows(chain)}, the {first} contains {num_text(c0, 'ppm')} of the chemical. What is the concentration in the {org}?"
        hints = [
            "The concentration is multiplied by the same factor at every step up the chain.",
            "Count the steps from the first organism to the organism asked about, then multiply by the factor once for each step.",
            f"The {org} is {words(steps_n)} step{'s' if steps_n > 1 else ''} above the {first}.",
        ]
        wrongs = [
            ("ADDED_NOT_MULTIPLIED", c0 + f * steps_n),
            ("ONE_STEP_ONLY", c0 * f),
            ("FACTOR_USED_ONCE_PER_LEVEL", c0 * f**n),
            ("ONE_TRANSFER_TOO_FEW", c0 * f ** (steps_n - 1)),
            ("DIVIDED_NOT_MULTIPLIED", c0 / f**steps_n),
        ]
        coeff, const = Fraction(1), c0 * f**steps_n
    else:
        top = c0 * f**steps_n
        value, given, up = c0, top, False
        stem = f"{base} In the food chain {_chain_arrows(chain)}, the {org} contains {num_text(top, 'ppm')} of the chemical. What is the concentration in the {first}?"
        hints = [
            "Going back down the chain undoes the multiplying, so divide by the factor for each step.",
            "Count the steps between the two organisms, then divide by the factor once for each step.",
            f"The {org} is {words(steps_n)} step{'s' if steps_n > 1 else ''} above the {first}.",
        ]
        wrongs = [
            ("MULTIPLIED_NOT_DIVIDED", top * f**steps_n),
            ("ONE_STEP_ONLY", top / f),
            ("FACTOR_USED_ONCE_PER_LEVEL", top / f**n),
            ("ONE_TRANSFER_TOO_FEW", top / f ** (steps_n - 1)),
            ("ADDED_NOT_MULTIPLIED", top - f * steps_n),
        ]
        coeff, const = Fraction(f**steps_n), top
    bio = {
        "model": "ENV.CONC_CHAIN",
        "variant": variant,
        "given": qs(given),
        "factor": f,
        "transfers": steps_n,
        "direction": "up" if up else "down",
        "unit": "ppm",
    }
    steps = [
        f"There {'is' if steps_n == 1 else 'are'} {steps_n} step{'s' if steps_n > 1 else ''} between the two organisms.",
        f"The factor {f} is used once for each step: {num_text(given, 'ppm')} {'multiplied' if up else 'divided'} by {f}, {steps_n} time{'s' if steps_n > 1 else ''}.",
        f"The concentration is {num_text(value, 'ppm')}.",
    ]
    return numeric_draft(
        variant=variant, bio=bio, coeff=coeff, const=const, value=value, unit="ppm", stem=stem,
        hints=hints, steps=steps, wrongs=wrongs, difficulty=0.5, role="apply",
        prediction="Before you calculate, will the concentration be larger or smaller than the one given?",
        features=["accumulation"],
    )  # fmt: skip


def solve_conc_a(bio: Mapping[str, Any]) -> dict[str, Any]:
    given, f, n = Fraction(bio["given"]), int(bio["factor"]), int(bio["transfers"])
    return number_answer(given * f**n if bio["direction"] == "up" else given / f**n, bio["unit"])


def solve_conc_b(bio: Mapping[str, Any]) -> dict[str, Any]:
    value = Fraction(bio["given"])
    for _ in range(int(bio["transfers"])):
        value = (
            value * int(bio["factor"]) if bio["direction"] == "up" else value / int(bio["factor"])
        )
    return number_answer(value, bio["unit"])


_E0 = ("20", "200", "1000", "2000", "5000", "20000", "50000", "100000", "1000000")
ENV_MODELS: dict[str, Model] = {
    m.id: m
    for m in (
        Model(
            "ENV.TEN_PERCENT", "BIO.ENV.TEN_PERCENT", CH,
            "Use the ten percent law to find the energy at a trophic level",
            "ten_percent_closed_form", "step_by_step_transfer", "bio.ten_closed_form", "bio.ten_stepwise",
            {"variant": ("level_n", "next_level", "producer_from_top", "level_from_level"), "chain": tuple(str(i) for i in range(len(CHAINS))),
             "e0": _E0, "n": ("2", "3", "4", "5"), "m": ("1", "2", "3"), "unit": ("J", "kJ")},
            _ten, solve_ten_a, solve_ten_b,
        ),
        Model(
            "ENV.ENERGY_LOST", "BIO.ENV.ENERGY_LOST", CH,
            "Find the energy lost, or the share that reaches a level, along a food chain",
            "ten_percent_closed_form", "step_by_step_transfer", "bio.lost_closed_form", "bio.lost_stepwise",
            {"variant": ("lost_one_step", "lost_total", "percent_reaching"), "chain": tuple(str(i) for i in range(len(CHAINS))),
             "e0": _E0, "n": ("2", "3", "4", "5"), "unit": ("J", "kJ")},
            _lost, solve_lost_a, solve_lost_b, ("BIO.ENV.TEN_PERCENT",),
        ),
        Model(
            "ENV.TROPHIC", "BIO.ENV.TROPHIC", CH,
            "Find the trophic level, consumer order or number of levels in a food chain",
            "chain_position", "walk_the_chain", "bio.chain_index", "bio.chain_walk",
            {"variant": ("level_of", "organism_at", "kind_of", "n_levels", "n_consumers", "n_steps"),
             "chain": tuple(str(i) for i in range(len(CHAINS))), "pos": ("1", "2", "3", "4", "5")},
            _trophic, solve_trophic_a, solve_trophic_b,
        ),
        Model(
            "ENV.CONC_CHAIN", "BIO.ENV.CONC_CHAIN", CH,
            "Find how the concentration of a chemical builds up along a food chain",
            "repeated_multiplication", "step_by_step_transfer", "bio.conc_closed_form", "bio.conc_stepwise",
            {"variant": ("forward", "backward"), "chain": tuple(str(i) for i in range(len(CHAINS))),
             "c0": ("0.5", "1", "2", "3", "4", "0.1"), "f": ("2", "3", "5", "10"), "n": ("2", "3", "4", "5")},
            _conc, solve_conc_a, solve_conc_b, ("BIO.ENV.TEN_PERCENT",),
        ),
    )
}  # fmt: skip
_ = dec
