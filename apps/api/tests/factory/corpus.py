"""Known-good items in every kernel domain: the baseline the fault injector mutates."""

from __future__ import annotations

from typing import Any

from app.content.originality import ReferenceIndex
from app.factory.kernel import kinematics as kin
from app.factory.kernel.stoichiometry import molar_mass, parse_formula
from app.factory.lanes.maths_quadratic import LANE, TEMPLATE
from app.factory.lanes.reference import (
    BalanceBruteForce,
    CrossSympy,
    MassSympy,
    QuadraticFormula,
    RationalRootScan,
    SuvatSympy,
)
from app.factory.registry import ItemContext

HINTS = [
    "Start by listing what the question gives you.",
    "Choose the rule that links those quantities together.",
    "Work through the rule slowly and then check the units.",
]


def _mcq(key: dict, wrong: dict[str, dict]) -> tuple[list[dict[str, Any]], str]:
    options = [{"id": "key", "value": key, "text": "key", "procedure": "correct"}]
    for i, (name, value) in enumerate(wrong.items(), start=1):
        options.append({"id": f"d{i}", "value": value, "text": f"option {i}", "procedure": name})
    return options, "key"


def _ctx(
    item_id: str,
    lane: str,
    spec: dict,
    answer: dict,
    witness: dict,
    stem: str,
    wrong: dict[str, dict],
    tokens: list[str],
    methods: list,
    technique: str,
) -> ItemContext:  # noqa: PLR0913
    options, key = _mcq(answer, wrong)
    return ItemContext(
        item_id=item_id,
        lane=lane,
        spec=spec,
        answer=answer,
        witness=witness,
        stem=stem,
        hints=list(HINTS),
        options=options,
        key_option=key,
        answer_tokens=tokens,
        provenance={"original": True},
        syllabus={
            "grade": 10,
            "chapter_ref": "cbse.10.test.chapter",
            "skill_id": "TEST.SKILL",
            "allowed_methods": [technique],
            "forbidden_content": [],
        },
        methods=methods,
        reference_index=ReferenceIndex(),
    )


def kinematics(
    item_id: str,
    given: dict,
    find: str,
    unit: str,
    dp: int | None,
    value: str,
    wrong: list[str],
    stem: str,
) -> ItemContext:  # noqa: PLR0913
    spec = {
        "domain": "kinematics",
        "kind": "suvat",
        "given": given,
        "find": find,
        "answer_unit": unit,
        "answer_dp": dp,
    }
    full = [c for c in kin._solve(kin._given_si(spec)) if c["t"] >= 0][0]
    answer: dict[str, Any] = {"value": value, "unit": unit}
    if dp is not None:
        answer["dp"] = dp
    options = {f"wrong_{i}": {**answer, "value": w} for i, w in enumerate(wrong)}
    return _ctx(
        item_id,
        "physics",
        spec,
        answer,
        {k: str(v) for k, v in full.items()},
        stem,
        options,
        [value],
        [SuvatSympy()],
        "uniform_accel_eq",
    )


def balance(
    item_id: str, species: list[dict], coeffs: list[int], wrong: list[list[int]]
) -> ItemContext:
    spec = {"domain": "stoichiometry", "kind": "balance", "species": species}
    answer = {"coefficients": coeffs}
    return _ctx(
        item_id,
        "chemistry",
        spec,
        answer,
        {"atom_counts": [parse_formula(s["formula"]) for s in species]},
        "Balance the chemical equation shown in the box.",
        {f"wrong_{i}": {"coefficients": w} for i, w in enumerate(wrong)},
        [str(coeffs[0])],
        [BalanceBruteForce()],
        "balance_by_inspection",
    )


def mass(
    item_id: str,
    species: list[dict],
    coeffs: list[int],
    given: dict,
    target: dict,
    unit: str,
    value: str,
    wrong: list[str],
) -> ItemContext:  # noqa: PLR0913
    spec = {
        "domain": "stoichiometry",
        "kind": "mass",
        "reaction": {"species": species, "coefficients": coeffs},
        "given": given,
        "target": target,
        "answer_unit": unit,
    }
    answer = {"value": value, "unit": unit}
    return _ctx(
        item_id,
        "chemistry",
        spec,
        answer,
        {"molar_masses": [str(molar_mass(s["formula"])) for s in species]},
        "How much product forms from the amount of reactant given?",
        {f"wrong_{i}": {**answer, "value": w} for i, w in enumerate(wrong)},
        [value],
        [MassSympy()],
        "mole_concept",
    )


def cross(
    item_id: str, parents: list[str], ask: str, probs: dict[str, str], wrong: list[dict]
) -> ItemContext:
    from app.factory.kernel import genetics as kgen

    spec = {"domain": "genetics", "kind": "cross", "parents": parents, "ask": ask}
    answer = {"probabilities": probs}
    return _ctx(
        item_id,
        "biology",
        spec,
        answer,
        {"gametes": [sorted(kgen.gametes(p)) for p in parents]},
        "Two parent plants are crossed. What fraction of the offspring has each outcome?",
        {f"wrong_{i}": {"probabilities": w} for i, w in enumerate(wrong)},
        ["3"],
        [CrossSympy()],
        "punnett_square",
    )


def _sp(formula: str, side: str) -> dict:
    return {"formula": formula, "side": side}


def quadratic(a: int, r1: int, r2: int) -> ItemContext:
    ctx = LANE.render(TEMPLATE, {"a": a, "r1": r1, "r2": r2})
    ctx.reference_index = ReferenceIndex()
    ctx.methods = [QuadraticFormula(), RationalRootScan()]
    return ctx


def corpus() -> list[ItemContext]:
    g = {"const": "g_earth"}
    return [
        quadratic(1, -2, 3),
        quadratic(2, 1, 4),
        quadratic(3, -5, -1),
        quadratic(1, -7, 6),
        kinematics(
            "K.fall",
            {"u": {"value": "0", "unit": "m/s"}, "a": g, "t": {"value": "3", "unit": "s"}},
            "s",
            "m",
            1,
            "44.1",
            ["45", "88.2", "29.4"],
            "A stone is dropped and falls for a short time.",
        ),
        kinematics(
            "K.car",
            {
                "u": {"value": "36", "unit": "km/h"},
                "a": {"value": "2", "unit": "m/s^2"},
                "t": {"value": "5", "unit": "s"},
            },
            "v",
            "km/h",
            0,
            "72",
            ["20", "7.2", "36"],
            "A car speeds up steadily along a straight road.",
        ),
        kinematics(
            "K.brake",
            {
                "u": {"value": "0", "unit": "m/s"},
                "v": {"value": "20", "unit": "m/s"},
                "s": {"value": "100", "unit": "m"},
            },
            "a",
            "m/s^2",
            None,
            "2",
            ["4", "1/2", "200"],
            "A cyclist gets up to speed over a measured stretch.",
        ),
        balance(
            "B.water",
            [_sp("H2", "L"), _sp("O2", "L"), _sp("H2O", "R")],
            [2, 1, 2],
            [[1, 1, 1], [4, 2, 4], [2, 1, 1]],
        ),
        balance(
            "B.rust",
            [_sp("Fe", "L"), _sp("O2", "L"), _sp("Fe2O3", "R")],
            [4, 3, 2],
            [[2, 3, 2], [4, 3, 1], [8, 6, 4]],
        ),
        balance(
            "B.propane",
            [_sp("C3H8", "L"), _sp("O2", "L"), _sp("CO2", "R"), _sp("H2O", "R")],
            [1, 5, 3, 4],
            [[1, 3, 3, 4], [2, 10, 6, 8], [1, 5, 4, 3]],
        ),
        mass(
            "M.water",
            [_sp("H2", "L"), _sp("O2", "L"), _sp("H2O", "R")],
            [2, 1, 2],
            {"index": 0, "quantity": "mass", "value": "4", "unit": "g"},
            {"index": 2, "quantity": "mass"},
            "g",
            "36",
            ["18", "72", "9"],
        ),
        mass(
            "M.lime",
            [_sp("CaCO3", "L"), _sp("CaO", "R"), _sp("CO2", "R")],
            [1, 1, 1],
            {"index": 0, "quantity": "mass", "value": "50", "unit": "g"},
            {"index": 1, "quantity": "moles"},
            "mol",
            "1/2",
            ["1", "1/4", "50"],
        ),
        cross(
            "G.mono",
            ["Aa", "Aa"],
            "phenotype",
            {"A": "3/4", "a": "1/4"},
            [{"A": "1/2", "a": "1/2"}, {"A": "1/4", "a": "3/4"}, {"A": "1"}],
        ),
        cross(
            "G.di",
            ["AaBb", "AaBb"],
            "phenotype",
            {"AB": "9/16", "Ab": "3/16", "aB": "3/16", "ab": "1/16"},
            [
                {"AB": "1/4", "Ab": "1/4", "aB": "1/4", "ab": "1/4"},
                {"AB": "3/4", "ab": "1/4"},
                {"AB": "9/16", "Ab": "3/16", "ab": "4/16"},
            ],
        ),
        cross(
            "G.test",
            ["Aa", "aa"],
            "genotype",
            {"Aa": "1/2", "aa": "1/2"},
            [{"Aa": "1/4", "aa": "3/4"}, {"AA": "1/2", "aa": "1/2"}, {"Aa": "1"}],
        ),
    ]
