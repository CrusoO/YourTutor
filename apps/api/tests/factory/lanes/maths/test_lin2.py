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
