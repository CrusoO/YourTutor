# ruff: noqa: E501
"""Pair of Linear Equations in Two Variables (chapter 3 of the Class 10 maths book): skills, templates.

Original wording; only the syllabus facts (chapter and topic names) are used as input.
"""

from __future__ import annotations

from typing import Any

from app.factory.lanes.maths.catalog_quad import _c

CHAPTER = "cbse.10.maths.ch03"
P = "MATH.ALG.PAIR."
SOLVE_PAIR = "MATH.ALG.LIN2.SOLVE_PAIR"


def tpl(
    short: str, family: str, skill: str, box: dict[str, Any], marks: int, kind: str,
    allowed: list[str],
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
            "chapter_ref": CHAPTER,
            "skill_id": skill,
            "allowed_methods": allowed,
            "forbidden_content": ["calculus", "quadratic_equations", "three_variables"],
        },
    }


TEMPLATES: list[dict[str, Any]] = [
    tpl(
        "C10.PAIR.GRAPH_POINT",
        "lin_graph_point",
        P + "GRAPH_MEETING_POINT",
        {
            "x": _c(-3, -1, 2, 4),
            "y": _c(-4, -2, 1, 3, 5),
            "ma": _c(-2, -1, 1, 2),
            "mb": _c(-3, -1, 1, 3),
            "wide": _c(0, 1),
            "first": _c(0, 1),
        },
        2,
        "short_answer_as_mcq",
        ["intersection_of_lines"],
    ),
    tpl(
        "C10.PAIR.GRAPH_TYPE",
        "lin_graph_type",
        P + "SOLUTION_TYPE",
        {
            "kind": _c("one", "none", "infinite"),
            "a1": _c(1, 2, 3),
            "b1": _c(-3, -2, 2, 5),
            "c1": _c(2, 3, -4),
            "m": _c(-2, 2, 3),
            "d": _c(1, -2),
        },
        1,
        "mcq_direct",
        ["consistency_conditions"],
    ),
    tpl(
        "C10.PAIR.SUBST_FORM",
        "lin_subst_form",
        P + "SUBSTITUTION",
        {
            "x": _c(-3, -1, 2, 4),
            "y": _c(-4, -2, 1, 3),
            "m": _c(-2, -1, 1, 3),
            "a": _c(1, 2, 3),
            "b": _c(2, -1, -3),
            "ask": _c("pair", "sum"),
        },
        2,
        "short_answer_as_mcq",
        ["substitution"],
    ),
    tpl(
        "C10.PAIR.SUBST_GENERAL",
        "lin_subst_general",
        P + "SUBSTITUTION",
        {
            "x": _c(-2, 1, 3),
            "y": _c(-3, 2, 4),
            "unit": _c(0, 1),
            "s1": _c(1, -1),
            "q": _c(2, 3, -2),
            "a": _c(2, 3, -1),
            "b": _c(-1, 2, 3),
        },
        3,
        "worked_problem_as_mcq",
        ["substitution"],
    ),
    tpl(
        "C10.PAIR.ELIM_DIRECT",
        "lin_elim_direct",
        P + "ELIMINATION",
        {
            "x": _c(-2, 1, 3, 4),
            "y": _c(-3, 2, 5),
            "e": _c(0, 1),
            "pe": _c(2, 3, 4),
            "sgn": _c(1, -1),
            "q1": _c(2, 3, -4),
            "q2": _c(-3, 5),
        },
        2,
        "short_answer_as_mcq",
        ["elimination"],
    ),
    tpl(
        "C10.PAIR.ELIM_ONE",
        "lin_elim_one",
        P + "ELIMINATION",
        {
            "x": _c(-2, 3),
            "y": _c(-3, 1, 4),
            "e": _c(0, 1),
            "pe": _c(1, 2),
            "m": _c(2, 3, -2, -3),
            "q1": _c(2, -3),
            "q2": _c(5, -4, 7),
            "swap": _c(0, 1),
        },
        3,
        "worked_problem_as_mcq",
        ["elimination"],
    ),
    tpl(
        "C10.PAIR.ELIM_BOTH",
        "lin_elim_both",
        P + "ELIMINATION",
        {
            "x": _c(-2, 1, 3),
            "y": _c(-3, 2, 4),
            "e": _c(0, 1),
            "a1": _c(2, 3, -3),
            "a2": _c(3, 4, 5, -2),
            "q1": _c(2, -3, 5),
            "q2": _c(3, -4),
        },
        3,
        "worked_problem_as_mcq",
        ["elimination"],
    ),
    tpl(
        "C10.PAIR.CROSS_SOLVE",
        "lin_cross_solve",
        P + "CROSS_MULTIPLICATION",
        {
            "x": _c(-3, 2, 4),
            "y": _c(-2, 1, 5),
            "a1": _c(1, 2, 3),
            "b1": _c(2, -3),
            "a2": _c(3, -2, 4),
            "b2": _c(1, -1, 3),
        },
        3,
        "worked_problem_as_mcq",
        ["cross_multiplication"],
    ),
    tpl(
        "C10.PAIR.CROSS_SETUP",
        "lin_cross_setup",
        P + "CROSS_MULTIPLICATION",
        {
            "which": _c("p", "q", "r"),
            "a1": _c(2, -3),
            "b1": _c(2, -3, 4),
            "c1": _c(-5, 3, 6),
            "a2": _c(3, -2, 4),
            "b2": _c(1, -1, 5),
            "c2": _c(-7, 2, 9),
        },
        2,
        "short_answer_as_mcq",
        ["cross_multiplication"],
    ),
]

# (skill suffix, title, grade_band, prerequisites, misconceptions: filled in from the families)
SKILLS: list[tuple[str, str, list[int], list[str], list[str]]] = [
    (
        "GRAPH_MEETING_POINT",
        "Find where two lines meet from points listed on each line",
        [10],
        [SOLVE_PAIR],
        [],
    ),
    (
        "SOLUTION_TYPE",
        "Decide from the coefficients whether a pair of lines meets once, never or everywhere",
        [10],
        [SOLVE_PAIR, P + "GRAPH_MEETING_POINT"],
        [],
    ),
    (
        "SUBSTITUTION",
        "Solve a pair of linear equations by substitution",
        [10],
        [SOLVE_PAIR, "MATH.ALG.SUBSTITUTE"],
        [],
    ),
    (
        "ELIMINATION",
        "Solve a pair of linear equations by elimination",
        [10],
        [SOLVE_PAIR, "MATH.ALG.INVERSE_OPERATIONS"],
        [],
    ),
    (
        "CROSS_MULTIPLICATION",
        "Solve a pair of linear equations with the ratio formula",
        [10],
        [P + "SUBSTITUTION", P + "ELIMINATION"],
        [],
    ),
]
