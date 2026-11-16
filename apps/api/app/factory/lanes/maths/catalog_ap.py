# ruff: noqa: E501
"""Arithmetic Progressions (chapter 5 of the Class 10 maths book): skills, templates.

Original wording; only the syllabus facts (chapter and topic names) are used as input.
"""

from __future__ import annotations

from typing import Any

from app.factory.lanes.maths.catalog_quad import _c, _r

CHAPTER = "cbse.10.maths.ch05"
P = "MATH.ALG.AP."


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
            "forbidden_content": ["calculus", "geometric_progressions", "infinite_series"],
        },
    }


TEMPLATES: list[dict[str, Any]] = [
    tpl(
        "C10.AP.DIFFERENCE",
        "ap_diff",
        P + "COMMON_DIFFERENCE",
        {"a": _r(-6, 9), "d": _c(-7, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 8, 9), "den": _c(1, 2)},
        1,
        "mcq_direct",
        ["common_difference"],
    ),
    tpl(
        "C10.AP.IDENTIFY",
        "ap_identify",
        P + "IDENTIFY_AP",
        {"a": _r(1, 9), "d": _r(2, 8), "g": _c(2, 3), "brk": _c(-2, -1, 1, 2, 3)},
        1,
        "mcq_direct",
        ["common_difference"],
    ),
    tpl(
        "C10.AP.NTH_TERM",
        "ap_nth",
        P + "NTH_TERM",
        {
            "a": _c(-9, -4, -1, 2, 5, 8, 12, 17),
            "d": _c(-6, -4, -3, -2, 2, 3, 4, 5, 7, 9),
            "n": _c(8, 10, 15, 20, 30),
            "style": _c(0, 1),
        },
        1,
        "mcq_direct",
        ["nth_term_formula"],
    ),
    tpl(
        "C10.AP.WHICH_TERM",
        "ap_which_term",
        P + "POSITION_OF_TERM",
        {
            "a": _c(-8, -3, 2, 5, 9, 14),
            "d": _c(-6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7),
            "n": _c(6, 9, 12, 15, 20, 27, 35),
        },
        2,
        "short_answer_as_mcq",
        ["nth_term_formula"],
    ),
    tpl(
        "C10.AP.TWO_TERMS",
        "ap_two_terms",
        P + "TERMS_FROM_TWO_TERMS",
        {
            "a": _c(-6, -2, 3, 5, 9),
            "d": _c(-4, -2, 3, 5),
            "p": _c(2, 3, 5),
            "gap": _c(1, 2, 4),
            "r": _c(9, 11, 14, 20),
        },
        3,
        "worked_problem_as_mcq",
        ["nth_term_formula"],
    ),
    tpl(
        "C10.AP.SUM_N",
        "ap_sum",
        P + "SUM_FIRST_N",
        {
            "a": _c(-4, -1, 2, 5, 8, 12),
            "d": _c(-5, -3, -2, 2, 3, 4, 5, 7),
            "n": _c(6, 8, 10, 12, 15, 20, 25),
        },
        2,
        "short_answer_as_mcq",
        ["sum_formula"],
    ),
    tpl(
        "C10.AP.SUM_LAST",
        "ap_sum_last",
        P + "SUM_USING_LAST_TERM",
        {
            "a": _c(-6, -2, 1, 4, 9, 13),
            "d": _c(-5, -3, 2, 3, 4, 5, 6, 7),
            "n": _c(8, 11, 14, 18, 23, 30),
        },
        3,
        "worked_problem_as_mcq",
        ["sum_formula"],
    ),
    tpl(
        "C10.AP.N_FROM_SUM",
        "ap_find_n_sum",
        P + "NUMBER_OF_TERMS_FROM_SUM",
        {
            "a": _c(1, 3, 5, 8, 12, 17),
            "d": _c(-3, -2, -1, 1, 2, 3, 4, 5, 6, 8),
            "n": _c(4, 6, 9, 13, 17),
        },
        4,
        "case_based_mcq",
        ["sum_formula"],
    ),
    tpl(
        "C10.AP.TERM_FROM_SUM",
        "ap_term_from_sum",
        P + "TERM_FROM_SUM_FORMULA",
        {
            "A": _r(1, 5),
            "B": _c(-5, -2, 0, 3, 7),
            "k": _c(3, 5, 8, 10, 12, 15),
            "ask": _c("kth", "d"),
        },
        3,
        "worked_problem_as_mcq",
        ["sum_formula"],
    ),
    tpl(
        "C10.AP.WORD_LAST",
        "ap_word",
        P + "MODEL_SITUATION",
        {
            "ctx": _c(0, 1, 2, 3),
            "a": _c(12, 20, 35, 50),
            "d": _c(2, 3, 5, 8),
            "n": _c(8, 12, 18, 24),
            "ask": _c("last"),
        },
        3,
        "worked_problem_as_mcq",
        ["nth_term_formula"],
    ),
    tpl(
        "C10.AP.WORD_TOTAL",
        "ap_word",
        P + "MODEL_SITUATION",
        {
            "ctx": _c(0, 1, 2, 3),
            "a": _c(12, 20, 35, 50),
            "d": _c(2, 3, 5, 8),
            "n": _c(8, 12, 18, 24),
            "ask": _c("total"),
        },
        4,
        "case_based_mcq",
        ["sum_formula"],
    ),
    tpl(
        "C10.AP.MULTIPLES",
        "ap_multiples",
        P + "SUM_OF_MULTIPLES",
        {
            "m": _c(3, 4, 5, 6, 7, 8, 9, 11, 12),
            "i": _c(1, 3, 6, 9),
            "cnt": _c(8, 12, 20, 30),
            "e1": _c(0, 2),
            "e2": _c(0, 1),
        },
        3,
        "worked_problem_as_mcq",
        ["sum_formula"],
    ),
]

# (skill suffix, title, grade_band, prerequisites, misconceptions)
SKILLS: list[tuple[str, str, list[int], list[str], list[str]]] = [
    (
        "COMMON_DIFFERENCE",
        "Find the common difference of a list with a constant step",
        [9, 10],
        ["MATH.NUM.PATTERNS_RULES", "MATH.ARITH.INTEGERS.OPERATIONS"],
        [
            "MC.AP.DIFF_SIGN_REVERSED",
            "MC.AP.DIFF_AS_RATIO",
            "MC.AP.DIFF_FIRST_TERM_GIVEN",
            "MC.AP.DIFF_SKIPPED_TERM",
            "MC.AP.DIFF_LAST_TERM_GIVEN",
        ],
    ),
    (
        "IDENTIFY_AP",
        "Decide whether a list of numbers is an arithmetic progression",
        [10],
        ["MATH.ALG.AP.COMMON_DIFFERENCE"],
        [
            "MC.AP.RATIO_FOR_DIFFERENCE",
            "MC.AP.CHECKED_TWO_TERMS_ONLY",
            "MC.AP.DIFFERENCES_INCREASING_ACCEPTED",
        ],
    ),
    (
        "NTH_TERM",
        "Use the rule for the nth term of an AP",
        [10],
        ["MATH.ALG.AP.COMMON_DIFFERENCE", "MATH.ALG.SUBSTITUTE"],
        [
            "MC.AP.NTH_N_FOR_N_MINUS_1",
            "MC.AP.NTH_D_ADDED_NOT_MULTIPLIED",
            "MC.AP.NTH_SIGN_OF_D_FLIPPED",
            "MC.AP.NTH_FIRST_TERM_DROPPED",
            "MC.AP.NTH_OFF_BY_ONE_LOW",
        ],
    ),
    (
        "POSITION_OF_TERM",
        "Find which term of an AP equals a given number",
        [10],
        ["MATH.ALG.AP.NTH_TERM", "MATH.ALG.INVERSE_OPERATIONS", "MATH.ALG.LIN1.SOLVE_TWO_STEP"],
        [
            "MC.AP.FIND_N_FORGOT_PLUS_ONE",
            "MC.AP.FIND_N_OVERCOUNT",
            "MC.AP.FIND_N_DIFFERENCE_NOT_DIVIDED",
            "MC.AP.FIND_N_VALUE_OVER_DIFFERENCE",
        ],
    ),
    (
        "TERMS_FROM_TWO_TERMS",
        "Find a term of an AP when two other terms are known",
        [10],
        ["MATH.ALG.AP.NTH_TERM", "MATH.ALG.LIN2.SOLVE_PAIR"],
        [
            "MC.AP.TWO_TERMS_DIFF_NOT_DIVIDED",
            "MC.AP.TWO_TERMS_STARTED_FROM_GIVEN_TERM",
            "MC.AP.NTH_N_FOR_N_MINUS_1",
            "MC.AP.DIFF_SIGN_REVERSED",
        ],
    ),
    (
        "SUM_FIRST_N",
        "Add the first n terms of an AP",
        [10],
        ["MATH.ALG.AP.NTH_TERM"],
        [
            "MC.AP.SUM_FORGOT_HALF",
            "MC.AP.SUM_N_FOR_N_MINUS_1",
            "MC.AP.SUM_NO_DOUBLE_A",
            "MC.AP.SUM_AS_NTH_TERM",
        ],
    ),
    (
        "SUM_USING_LAST_TERM",
        "Add an AP when its first and last terms are known",
        [10],
        ["MATH.ALG.AP.POSITION_OF_TERM", "MATH.ALG.AP.SUM_FIRST_N"],
        [
            "MC.AP.SUM_COUNT_FORGOT_PLUS_ONE",
            "MC.AP.SUM_FORGOT_HALF",
            "MC.AP.SUM_LAST_TERM_AS_COUNT",
            "MC.AP.SUM_FORGOT_COUNT_AND_HALF",
        ],
    ),
    (
        "NUMBER_OF_TERMS_FROM_SUM",
        "Find the number of terms that give a stated sum",
        [10],
        ["MATH.ALG.AP.SUM_FIRST_N", "MATH.ALG.QUAD.SOLVE_FACTORISE_MONIC"],
        ["MC.AP.SUMN_OTHER_ROOT_KEPT", "MC.AP.SUMN_OFF_BY_ONE", "MC.AP.SUMN_DIVIDED_BY_FIRST_TERM"],
    ),
    (
        "TERM_FROM_SUM_FORMULA",
        "Recover a term or the difference from a formula for the sum",
        [10],
        ["MATH.ALG.AP.SUM_FIRST_N", "MATH.ALG.SUBSTITUTE"],
        [
            "MC.AP.TERM_IS_SUM",
            "MC.AP.TERM_FROM_SUM_AVERAGE",
            "MC.AP.TERM_FROM_SUM_WRONG_INDEX",
            "MC.AP.TERM_FROM_SUM_NEXT_SUM",
            "MC.AP.D_FROM_SUM_COEFF_NOT_DOUBLED",
            "MC.AP.D_FROM_SUM_FIRST_TERM",
            "MC.AP.D_FROM_SUM_SECOND_TERM",
            "MC.AP.D_FROM_SUM_LINEAR_COEFF",
        ],
    ),
    (
        "MODEL_SITUATION",
        "Model a real situation with an AP and answer a question about it",
        [10],
        ["MATH.ALG.AP.NTH_TERM", "MATH.ALG.AP.SUM_FIRST_N"],
        [
            "MC.AP.WORD_TOTAL_REPORTED",
            "MC.AP.WORD_LAST_REPORTED",
            "MC.AP.NTH_N_FOR_N_MINUS_1",
            "MC.AP.NTH_OFF_BY_ONE_LOW",
            "MC.AP.NTH_D_ADDED_NOT_MULTIPLIED",
            "MC.AP.SUM_FORGOT_HALF",
            "MC.AP.SUM_N_FOR_N_MINUS_1",
            "MC.AP.SUM_NO_DOUBLE_A",
        ],
    ),
    (
        "SUM_OF_MULTIPLES",
        "Add all the multiples of a number inside a range",
        [10],
        ["MATH.ALG.AP.SUM_USING_LAST_TERM"],
        [
            "MC.AP.COUNT_FORGOT_PLUS_ONE",
            "MC.AP.ENDPOINTS_USED_NOT_MULTIPLES",
            "MC.AP.SUM_FORGOT_HALF",
            "MC.AP.MULTIPLES_STARTED_FROM_FIRST",
        ],
    ),
]
