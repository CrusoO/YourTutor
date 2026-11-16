# ruff: noqa: E501
"""Quadratic Equations (chapter 4 of the Class 10 maths book): skills, misconceptions, templates.

Everything here is original wording written for this product. Only the syllabus FACTS (chapter and
topic names) are used as input.
"""

from __future__ import annotations

from typing import Any

CHAPTER = "cbse.10.maths.ch04"
P = "MATH.ALG.QUAD."


def tpl(
    short: str, family: str, skill: str, box: dict[str, Any], marks: int, kind: str,
    allowed: list[str], forbidden: list[str] | None = None,
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
            "forbidden_content": forbidden or ["calculus", "complex_numbers", "cubic_equations"],
        },
    }


def _r(lo: int, hi: int) -> dict[str, int]:
    return {"min": lo, "max": hi}


def _c(*vals: Any) -> dict[str, list[Any]]:
    return {"choices": list(vals)}


TEMPLATES: list[dict[str, Any]] = [
    tpl(
        "C10.QUAD.STD_FORM",
        "std_form",
        P + "STANDARD_FORM",
        {
            "a": _c(1, 2),
            "r1": _r(-3, 3),
            "r2": _r(-3, 3),
            "e": _c(-2, 3),
            "f": _c(-4, 3),
            "ask": _c("b", "c"),
        },
        1,
        "mcq_direct",
        ["standard_form"],
    ),
    tpl(
        "C10.QUAD.FACTOR_MONIC",
        "solve_factor",
        P + "SOLVE_FACTORISE_MONIC",
        {"a": _c(1), "p1": _r(-9, 9), "q1": _c(1), "p2": _r(-9, 9), "q2": _c(1)},
        2,
        "short_answer_as_mcq",
        ["factorise_quadratic"],
    ),
    tpl(
        "C10.QUAD.FACTOR_GENERAL",
        "solve_factor",
        P + "SOLVE_FACTORISE_GENERAL",
        {"a": _c(1, 2), "p1": _r(-5, 5), "q1": _c(1, 2, 3), "p2": _r(-5, 5), "q2": _c(1, 2, 3)},
        3,
        "worked_problem_as_mcq",
        ["factorise_quadratic"],
    ),
    tpl(
        "C10.QUAD.PURE",
        "incomplete_pure",
        P + "SOLVE_INCOMPLETE",
        {"a": _r(1, 4), "r": _r(1, 9), "form": _c(0, 1), "neg": _c(0, 1)},
        1,
        "mcq_direct",
        ["square_root_method"],
    ),
    tpl(
        "C10.QUAD.COMMON_X",
        "incomplete_x",
        P + "SOLVE_INCOMPLETE",
        {"a": _r(1, 4), "r": _c(-9, -7, -5, -4, -3, -2, 2, 3, 4, 5, 6, 8, 9), "form": _c(0, 1)},
        2,
        "short_answer_as_mcq",
        ["common_factor"],
    ),
    tpl(
        "C10.QUAD.FORMULA_RATIONAL",
        "formula_rational",
        P + "SOLVE_FORMULA",
        {"a": _c(1, 2, 3), "p1": _r(-7, 7), "q1": _c(1, 2), "p2": _r(-7, 7), "q2": _c(1, 2)},
        3,
        "worked_problem_as_mcq",
        ["quadratic_formula"],
    ),
    tpl(
        "C10.QUAD.FORMULA_SURD",
        "formula_surd",
        P + "SOLVE_FORMULA",
        {"a": _c(1, 2, 3), "b": _r(-8, 8), "c": _r(-8, 8)},
        3,
        "worked_problem_as_mcq",
        ["quadratic_formula"],
    ),
    tpl(
        "C10.QUAD.DISCRIMINANT",
        "discriminant",
        P + "DISCRIMINANT",
        {"a": _c(-3, -2, -1, 1, 2, 3, 4), "b": _r(-5, 5), "c": _r(-5, 5)},
        1,
        "mcq_direct",
        ["discriminant"],
    ),
    tpl(
        "C10.QUAD.NATURE",
        "nature",
        P + "NATURE_OF_ROOTS",
        {"a": _c(-3, -2, -1, 1, 2, 3), "b": _r(-6, 6), "c": _r(-6, 6)},
        2,
        "short_answer_as_mcq",
        ["discriminant", "completing_square"],
    ),
    tpl(
        "C10.QUAD.K_MIDDLE",
        "find_k_middle",
        P + "FIND_PARAMETER_FOR_ROOTS",
        {"a": _r(1, 5), "g": _r(1, 5)},
        3,
        "worked_problem_as_mcq",
        ["discriminant"],
    ),
    tpl(
        "C10.QUAD.K_LEAD",
        "find_k_lead",
        P + "FIND_PARAMETER_FOR_ROOTS",
        {"c": _c(-6, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 8), "g": _r(1, 5)},
        3,
        "worked_problem_as_mcq",
        ["discriminant"],
    ),
    tpl(
        "C10.QUAD.FORM_FROM_ROOTS",
        "form_from_roots",
        P + "FORM_FROM_ROOTS",
        {"a": _c(1, 2, 3), "r1": _r(-5, 5), "r2": _r(-5, 5)},
        2,
        "short_answer_as_mcq",
        ["sum_and_product_of_roots", "factor_theorem"],
    ),
    tpl(
        "C10.QUAD.COMPLETE_SQUARE",
        "complete_square",
        P + "COMPLETE_SQUARE",
        {"h": _c(-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6), "c": _r(-9, 9), "ask": _c("p", "q")},
        2,
        "short_answer_as_mcq",
        ["complete_the_square"],
    ),
    tpl(
        "C10.QUAD.CHECK_ROOT",
        "check_root",
        P + "CHECK_ROOT",
        {"a": _c(1, 2, 3), "r1": _r(-6, 6), "r2": _r(-6, 6), "which": _c(0, 1)},
        1,
        "mcq_direct",
        ["substitution"],
    ),
    tpl(
        "C10.QUAD.WORD_NUMBERS",
        "word_consecutive",
        P + "MODEL_NUMBERS",
        {"s": _c(1, 2), "n": _r(2, 25)},
        3,
        "worked_problem_as_mcq",
        ["model_with_quadratic"],
    ),
    tpl(
        "C10.QUAD.WORD_RECT",
        "word_rectangle",
        P + "MODEL_GEOMETRY",
        {"d": _r(1, 10), "w": _r(3, 24), "ask": _c("breadth", "length"), "rate": _c(0)},
        3,
        "worked_problem_as_mcq",
        ["model_with_quadratic"],
    ),
    tpl(
        "C10.QUAD.WORD_RECT_COST",
        "word_rectangle",
        P + "MODEL_GEOMETRY",
        {"d": _r(1, 10), "w": _r(3, 24), "ask": _c("cost"), "rate": _c(10, 20, 25)},
        4,
        "case_based_mcq",
        ["model_with_quadratic"],
    ),
    tpl(
        "C10.QUAD.WORD_TRIANGLE",
        "word_triangle",
        P + "MODEL_GEOMETRY",
        {"x": _r(3, 110), "d": _r(1, 40), "ask": _c("shorter", "longer")},
        4,
        "case_based_mcq",
        ["model_with_quadratic"],
    ),
    tpl(
        "C10.QUAD.WORD_MOTION",
        "word_motion",
        P + "MODEL_MOTION",
        {
            "v": _c(20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80),
            "s": _c(5, 10, 15, 20),
            "t": _c(1, 2),
            "ask": _c("usual", "faster"),
        },
        4,
        "case_based_mcq",
        ["model_with_quadratic"],
    ),
]

# (skill suffix, title, grade_band, prerequisites, misconception ids)
SKILLS: list[tuple[str, str, list[int], list[str], list[str]]] = [
    (
        "STANDARD_FORM",
        "Rewrite a quadratic equation in standard form and read its coefficients",
        [9, 10],
        [
            "MATH.ALG.INVERSE_OPERATIONS",
            "MATH.ALG.EXPAND_BRACKETS",
            "MATH.ARITH.INTEGERS.OPERATIONS",
        ],
        [
            "MC.QUAD.STD_RHS_IGNORED",
            "MC.QUAD.STD_TERM_ADDED",
            "MC.QUAD.STD_SIGN_NEGATED",
            "MC.QUAD.STD_COEFF_POSITION_MIXED",
        ],
    ),
    (
        "CHECK_ROOT",
        "Test whether a number is a root by substituting it",
        [9, 10],
        ["MATH.ALG.SUBSTITUTE", "MATH.ARITH.INTEGERS.OPERATIONS"],
        [
            "MC.QUAD.CHECK_SIGN_FLIPPED",
            "MC.QUAD.CHECK_CONSTANT_TERM_USED",
            "MC.QUAD.CHECK_ONE_OFF",
            "MC.QUAD.CHECK_COEFFICIENT_USED",
        ],
    ),
    (
        "SOLVE_INCOMPLETE",
        "Solve quadratics with no constant term or no x term",
        [9, 10],
        ["MATH.ALG.QUAD.STANDARD_FORM", "MATH.ARITH.SQUARES_ROOTS", "MATH.ALG.INVERSE_OPERATIONS"],
        [
            "MC.QUAD.PURE_PLUS_ONLY",
            "MC.QUAD.PURE_FORGOT_SQRT",
            "MC.QUAD.PURE_MULTIPLIED_NOT_DIVIDED",
            "MC.QUAD.PURE_NO_REAL_ROOTS",
            "MC.QUAD.PURE_SIGN_IGNORED",
            "MC.QUAD.PURE_ONE_NEGATIVE_ROOT",
            "MC.QUAD.PURE_ONE_POSITIVE_ROOT",
            "MC.QUAD.PURE_ZERO_ROOT",
            "MC.QUAD.DIVIDED_BY_X_LOST_ROOT",
            "MC.QUAD.ONE_FACTOR_ONLY",
            "MC.QUAD.FACTOR_SIGN_SLIP",
            "MC.QUAD.SECOND_ROOT_SIGN_ONLY",
        ],
    ),
    (
        "SOLVE_FACTORISE_MONIC",
        "Solve a quadratic with leading coefficient 1 by factorising",
        [9, 10],
        [
            "MATH.ALG.QUAD.STANDARD_FORM",
            "MATH.ALG.FACTORISE_COMMON",
            "MATH.ALG.LIN1.SOLVE_TWO_STEP",
        ],
        [
            "MC.QUAD.FACTOR_SIGN_READ",
            "MC.QUAD.FACTOR_ONE_SIGN",
            "MC.QUAD.FACTOR_ONE_ROOT_ONLY",
            "MC.QUAD.FACTOR_SUM_PRODUCT_CONFUSED",
        ],
    ),
    (
        "SOLVE_FACTORISE_GENERAL",
        "Solve a quadratic with leading coefficient above 1 by splitting the middle term",
        [10],
        ["MATH.ALG.QUAD.SOLVE_FACTORISE_MONIC"],
        [
            "MC.QUAD.FACTOR_SIGN_READ",
            "MC.QUAD.BRACKET_COEFF_IGNORED",
            "MC.QUAD.BRACKET_COEFF_INVERTED",
            "MC.QUAD.FACTOR_ONE_ROOT_ONLY",
            "MC.QUAD.FACTOR_ONE_SIGN",
        ],
    ),
    (
        "COMPLETE_SQUARE",
        "Complete the square on a quadratic expression",
        [10],
        ["MATH.ALG.QUAD.STANDARD_FORM", "MATH.ALG.EXPAND_BRACKETS"],
        [
            "MC.QUAD.CS_SIGN_OF_HALF",
            "MC.QUAD.CS_NOT_HALVED",
            "MC.QUAD.CS_SQUARED_INSTEAD",
            "MC.QUAD.CS_ADDED_NOT_SUBTRACTED",
            "MC.QUAD.CS_NOT_SQUARED",
            "MC.QUAD.CS_SIGN_SWAPPED",
        ],
    ),
    (
        "DISCRIMINANT",
        "Compute the discriminant from the three coefficients",
        [10],
        ["MATH.ALG.QUAD.STANDARD_FORM", "MATH.ARITH.INTEGERS.OPERATIONS"],
        [
            "MC.QUAD.DISC_SIGN_OF_4AC",
            "MC.QUAD.DISC_FORGOT_FOUR",
            "MC.QUAD.DISC_DOUBLED_B",
            "MC.QUAD.DISC_NEGATIVE_B_SQUARED",
        ],
    ),
    (
        "SOLVE_FORMULA",
        "Solve a quadratic with the quadratic formula",
        [10],
        ["MATH.ALG.QUAD.DISCRIMINANT", "MATH.ARITH.SQUARES_ROOTS", "MATH.NUM.SURDS_SIMPLIFY"],
        [
            "MC.QUAD.FORMULA_B_SIGN",
            "MC.QUAD.FORMULA_FORGOT_2A",
            "MC.QUAD.FORMULA_DIVIDE_ONE_TERM",
            "MC.QUAD.FORMULA_FORGOT_A",
            "MC.QUAD.FORMULA_DISC_SIGN",
        ],
    ),
    (
        "NATURE_OF_ROOTS",
        "Decide the nature of the roots from the discriminant",
        [10],
        ["MATH.ALG.QUAD.DISCRIMINANT"],
        [
            "MC.QUAD.NATURE_DISC_SIGN_REVERSED",
            "MC.QUAD.NATURE_ZERO_ONLY_TESTED",
            "MC.QUAD.NATURE_EQUAL_ROOTS_MISSED",
            "MC.QUAD.NATURE_ZERO_DISC_NO_ROOTS",
            "MC.QUAD.NATURE_ONE_REAL_ONE_NOT",
        ],
    ),
    (
        "FIND_PARAMETER_FOR_ROOTS",
        "Find the unknown coefficient that gives equal roots",
        [10],
        ["MATH.ALG.QUAD.NATURE_OF_ROOTS", "MATH.ALG.LIN1.SOLVE_TWO_STEP"],
        [
            "MC.QUAD.K_POSITIVE_ONLY",
            "MC.QUAD.K_FORGOT_SQRT",
            "MC.QUAD.K_FORGOT_FACTOR_FOUR",
            "MC.QUAD.K_ONE_SIGN_PAIR",
            "MC.QUAD.K_SIGN",
            "MC.QUAD.K_HALF_FACTOR",
            "MC.QUAD.K_INVERTED",
        ],
    ),
    (
        "FORM_FROM_ROOTS",
        "Build a quadratic equation from its roots",
        [10],
        ["MATH.ALG.EXPAND_BRACKETS", "MATH.ALG.QUAD.SOLVE_FACTORISE_MONIC"],
        [
            "MC.QUAD.FORM_SUM_SIGN",
            "MC.QUAD.FORM_PRODUCT_SIGN",
            "MC.QUAD.SUM_PRODUCT_CONFUSED",
            "MC.QUAD.FORM_BOTH_SIGNS_FLIPPED",
        ],
    ),
    (
        "MODEL_NUMBERS",
        "Model a number problem with a quadratic equation and choose the valid root",
        [10],
        ["MATH.ALG.QUAD.SOLVE_FACTORISE_MONIC", "MATH.ALG.LIN1.WORD_PROBLEMS"],
        [
            "MC.QUAD.WORD_LARGER_REPORTED",
            "MC.QUAD.WORD_NEGATIVE_ROOT_KEPT",
            "MC.QUAD.WORD_SETUP_WRONG_DIFFERENCE",
            "MC.QUAD.WORD_SUM_USED_FOR_PRODUCT",
        ],
    ),
    (
        "MODEL_GEOMETRY",
        "Model an area or right-triangle problem with a quadratic equation",
        [10],
        [
            "MATH.ALG.QUAD.SOLVE_FACTORISE_MONIC",
            "MATH.GEO.PYTHAGORAS_USE",
            "MATH.ALG.LIN1.WORD_PROBLEMS",
        ],
        [
            "MC.QUAD.WORD_LENGTH_REPORTED",
            "MC.QUAD.WORD_NEGATIVE_ROOT_KEPT",
            "MC.QUAD.WORD_SEMIPERIMETER_FOR_SIDE",
            "MC.QUAD.WORD_BREADTH_REPORTED",
            "MC.QUAD.WORD_DIFFERENCE_ADDED_TWICE",
            "MC.QUAD.WORD_HALF_PERIMETER",
            "MC.QUAD.WORD_AREA_NOT_PERIMETER",
            "MC.QUAD.WORD_LENGTH_AS_BREADTH",
            "MC.QUAD.WORD_FORGOT_FINAL_STEP",
            "MC.QUAD.WORD_OTHER_SIDE_REPORTED",
            "MC.QUAD.WORD_HYPOTENUSE_MINUS_DIFFERENCE",
            "MC.QUAD.WORD_SIDES_SUMMED",
        ],
    ),
    (
        "MODEL_MOTION",
        "Model a speed and time problem with a quadratic equation",
        [10],
        ["MATH.ALG.QUAD.SOLVE_FACTORISE_MONIC", "MATH.ARITH.SPEED_DISTANCE_TIME"],
        [
            "MC.QUAD.WORD_OTHER_SPEED_REPORTED",
            "MC.QUAD.WORD_NEGATIVE_ROOT_KEPT",
            "MC.QUAD.WORD_INCREASE_SUBTRACTED",
            "MC.QUAD.WORD_INCREASE_ONLY",
        ],
    ),
]
