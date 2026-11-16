# ruff: noqa: E501
"""Trigonometry: Introduction to Trigonometry (ch 9), Trigonometric Identities (ch 10, one skill)
and Heights and Distances (ch 11, the book's older name is Some Applications of Trigonometry).

Original wording; only the syllabus facts (chapter and topic names) are used as input.
"""

from __future__ import annotations

from typing import Any

from app.factory.lanes.maths.catalog_quad import _c, _r

INTRO = "cbse.10.maths.ch09"
IDENT = "cbse.10.maths.ch10"
HD = "cbse.10.maths.ch11"


def tpl(
    short: str, family: str, skill: str, chapter: str, box: dict[str, Any], marks: int,
    kind: str, allowed: list[str],
) -> dict[str, Any]:  # fmt: skip
    return {
        "id": f"TPL.{short}",
        "short": short,
        "schema": "factory-template/1",
        "lane": "maths_c10",
        "family": family,
        "family_version": "1",
        "skill_id": skill,
        "box": box,
        "form": {"marks": marks, "kind": kind},
        "syllabus": {
            "grade": 10,
            "chapter_ref": chapter,
            "skill_id": skill,
            "allowed_methods": allowed,
            "forbidden_content": [
                "calculus",
                "inverse_trig_functions",
                "radians",
                "calculator_values",
            ],
        },
    }


_TRIPLE = {"m": _r(2, 6), "n": _r(1, 5)}

TEMPLATES: list[dict[str, Any]] = [
    tpl(
        "C10.TRIG.RATIOS_TRIANGLE",
        "tri_ratios",
        "MATH.TRIG.RATIOS_FROM_TRIANGLE",
        INTRO,
        {
            **_TRIPLE,
            "k": _c(1, 2, 3),
            "swap": _c(0, 1),
            "ratio": _c("sin", "cos", "tan"),
            "which": _c(0, 1),
        },
        2,
        "short_answer_as_mcq",
        ["trig_ratio_definition"],
    ),
    tpl(
        "C10.TRIG.TABLE_VALUES",
        "tri_table",
        "MATH.TRIG.STANDARD_ANGLE_VALUES",
        INTRO,
        {
            "f1": _c("sin", "cos", "tan"),
            "x": _c(0, 30, 45, 60, 90),
            "op": _c("+", "-", "*", "/"),
            "f2": _c("sin", "cos", "tan"),
            "y": _c(0, 30, 45, 60, 90),
            "pw": _c(1, 2),
        },
        2,
        "short_answer_as_mcq",
        ["trig_table"],
    ),
    tpl(
        "C10.TRIG.COMPLEMENT",
        "tri_complement",
        "MATH.TRIG.COMPLEMENTARY_ANGLES",
        INTRO,
        {
            "kind": _c("ratio", "product", "difference", "sumsq", "secratio"),
            "x": _c(8, 12, 17, 23, 28, 34, 37, 52, 56, 63, 71, 76),
        },
        1,
        "mcq_direct",
        ["complementary_angles"],
    ),
    tpl(
        "C10.TRIG.FROM_RATIO",
        "tri_from_ratio",
        "MATH.TRIG.RATIO_FROM_RATIO",
        IDENT,
        {
            **_TRIPLE,
            "swap": _c(0, 1),
            "given": _c("sin", "cos", "tan"),
            "ask": _c("sin", "cos", "tan"),
        },
        2,
        "short_answer_as_mcq",
        ["trig_identities"],
    ),
    tpl(
        "C10.TRIG.HD_HEIGHT",
        "hd_height",
        "MATH.TRIG.HD.HEIGHT_FROM_DISTANCE",
        HD,
        {"ang": _c(30, 45, 60), "k": _r(1, 12), "kind": _c("surd", "rational"), "ctx": _r(0, 4)},
        2,
        "short_answer_as_mcq",
        ["special_angle_ratios"],
    ),
    tpl(
        "C10.TRIG.HD_DISTANCE",
        "hd_distance",
        "MATH.TRIG.HD.DISTANCE_FROM_HEIGHT",
        HD,
        {"ang": _c(30, 45, 60), "k": _r(1, 12), "kind": _c("surd", "rational"), "ctx": _r(0, 4)},
        2,
        "short_answer_as_mcq",
        ["special_angle_ratios"],
    ),
    tpl(
        "C10.TRIG.HD_LADDER",
        "hd_ladder",
        "MATH.TRIG.HD.LADDER_AND_WALL",
        HD,
        {
            "ang": _c(30, 60),
            "k": _r(1, 12),
            "ask": _c("reach", "foot", "length_reach", "length_foot"),
        },
        3,
        "worked_problem_as_mcq",
        ["special_angle_ratios"],
    ),
    tpl(
        "C10.TRIG.HD_DEPRESSION",
        "hd_depression",
        "MATH.TRIG.HD.ANGLE_OF_DEPRESSION",
        HD,
        {"ang": _c(30, 45, 60), "k": _r(1, 10), "ask": _c("distance", "height"), "ctx": _r(0, 3)},
        3,
        "worked_problem_as_mcq",
        ["special_angle_ratios"],
    ),
    tpl(
        "C10.TRIG.HD_TWO",
        "hd_two_positions",
        "MATH.TRIG.HD.TWO_POSITIONS",
        HD,
        {"pair": _c(0, 1, 2), "k": _r(1, 10), "dir": _c(0, 1)},
        4,
        "case_based_mcq",
        ["special_angle_ratios"],
    ),
]

# (skill id, title, grade_band, prerequisites)
SKILLS: list[tuple[str, str, list[int], list[str]]] = [
    (
        "MATH.TRIG.RATIOS_FROM_TRIANGLE",
        "Write sine, cosine and tangent of an angle from the sides of a right triangle",
        [10],
        [
            "MATH.GEO.PYTHAGORAS_USE",
            "MATH.GEO.RIGHT_TRIANGLE_SIDES",
            "MATH.ARITH.FRACTIONS_SIMPLIFY",
        ],
    ),
    (
        "MATH.TRIG.STANDARD_ANGLE_VALUES",
        "Evaluate expressions with the exact ratios of 0, 30, 45, 60 and 90 degrees",
        [10],
        [
            "MATH.TRIG.RATIOS_FROM_TRIANGLE",
            "MATH.NUM.SURDS_SIMPLIFY",
            "MATH.ARITH.FRACTIONS_SIMPLIFY",
        ],
    ),
    (
        "MATH.TRIG.COMPLEMENTARY_ANGLES",
        "Use the ratios of complementary angles to simplify an expression",
        [10],
        ["MATH.TRIG.RATIOS_FROM_TRIANGLE"],
    ),
    (
        "MATH.TRIG.RATIO_FROM_RATIO",
        "Find the other ratios of an acute angle from one ratio",
        [10],
        ["MATH.TRIG.RATIOS_FROM_TRIANGLE", "MATH.GEO.PYTHAGORAS_USE"],
    ),
    (
        "MATH.TRIG.HD.HEIGHT_FROM_DISTANCE",
        "Find a height from a distance and an angle of elevation",
        [10],
        ["MATH.TRIG.STANDARD_ANGLE_VALUES", "MATH.ALG.INVERSE_OPERATIONS"],
    ),
    (
        "MATH.TRIG.HD.DISTANCE_FROM_HEIGHT",
        "Find a distance or shadow length from a height and an angle",
        [10],
        ["MATH.TRIG.HD.HEIGHT_FROM_DISTANCE", "MATH.NUM.SURDS_SIMPLIFY"],
    ),
    (
        "MATH.TRIG.HD.LADDER_AND_WALL",
        "Solve ladder-against-a-wall problems with sine and cosine",
        [10],
        ["MATH.TRIG.HD.HEIGHT_FROM_DISTANCE"],
    ),
    (
        "MATH.TRIG.HD.ANGLE_OF_DEPRESSION",
        "Use the angle of depression by moving it into the triangle",
        [10],
        ["MATH.TRIG.HD.DISTANCE_FROM_HEIGHT", "MATH.GEO.ALTERNATE_ANGLES"],
    ),
    (
        "MATH.TRIG.HD.TWO_POSITIONS",
        "Find a height from two angles of elevation along a line",
        [10],
        ["MATH.TRIG.HD.DISTANCE_FROM_HEIGHT", "MATH.ALG.LIN1.SOLVE_TWO_STEP"],
    ),
]
