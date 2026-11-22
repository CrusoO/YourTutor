# ruff: noqa: E501
"""Pair of Linear Equations in Two Variables lane: misconception table, reference solvers, families."""

from app.factory.lanes.maths.misconceptions import TEXT
from app.factory.lanes.maths.misconceptions_pair import PAIR_TEXT


def test_pair_table_is_merged_and_well_formed():
    assert len(PAIR_TEXT) >= 30
    assert set(PAIR_TEXT) <= set(TEXT)
    for mc, (title, why) in PAIR_TEXT.items():
        assert mc.startswith("MC.PAIR.") and mc == mc.upper()
        assert len(title) > 5 and len(why) > 15
        for word in ("CBSE", "NCERT"):
            assert word not in title + why


def test_the_required_slips_are_named():
    names = " ".join(PAIR_TEXT)
    for idea in (
        "ELIM_SIGN_SLIP",  # sign slip when eliminating
        "ELIM_ADD_NOT_SUBTRACT",  # adding instead of subtracting
        "ONE_VARIABLE_ONLY",  # solving for only one variable
        "XY_SWAPPED",  # mixing up x and y
        "ELIM_DIVIDED_ONE_TERM",  # dividing only one term
        "WORD_",  # mis-set word-problem equation
    ):
        assert idea in names


# ---------------------------------------------------------------- reference solvers

from fractions import Fraction  # noqa: E402

import pytest  # noqa: E402

from app.factory.lanes.maths.reference import lin2 as ref  # noqa: E402

F = Fraction


@pytest.mark.parametrize(
    "raw, want",
    [
        ([[2, 3, 12], [1, -1, 1]], (F(3), F(2))),
        ([[1, 0, 4], [2, 1, 3]], (F(4), F(-5))),  # a zero coefficient
        ([[0, 2, 6], [3, -1, 0]], (F(1), F(3))),
        ([[2, 4, 3], [4, -2, 1]], (F(1, 2), F(1, 2))),  # simple fractions
    ],
)
def test_every_solver_agrees_with_hand_values(raw, want):
    pair = ref.eqs(raw)
    for name, solver in ref.SOLVERS.items():
        assert solver(pair) == want, name


def test_solvers_refuse_a_singular_pair():
    pair = ref.eqs([[1, 2, 3], [2, 4, 6]])
    for name, solver in ref.SOLVERS.items():
        with pytest.raises(ValueError):
            solver(pair)
        assert name


@pytest.mark.parametrize(
    "raw, kind",
    [
        ([[1, 2, 3], [3, 7, 4]], "one"),
        ([[1, 2, 3], [2, 4, 9]], "none"),
        ([[1, 2, 3], [3, 6, 9]], "infinite"),
        ([[2, -3, 5], [-4, 6, -10]], "infinite"),
        ([[2, -3, 5], [-4, 6, 7]], "none"),
    ],
)
def test_three_classifiers_agree(raw, kind):
    pair = ref.eqs(raw)
    assert ref.kind_ratios(pair) == ref.kind_sympy(pair) == ref.kind_gauss(pair) == kind


def test_determinants_two_ways():
    for a, b, c, d in [(1, 2, 3, 4), (0, 5, 2, 7), (0, 0, 1, 1), (3, -2, -6, 4)]:
        vals = [F(v) for v in (a, b, c, d)]
        assert ref.det2(*vals) == ref.det2_sympy(*vals) == a * d - b * c


def test_scan_needs_exactly_one_grid_point():
    with pytest.raises(ValueError):
        ref.scan_pair(ref.eqs([[1, 0, 1000], [0, 1, 2]]))  # solution outside the grid
