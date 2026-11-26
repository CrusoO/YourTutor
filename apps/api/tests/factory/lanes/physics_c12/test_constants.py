"""The ONE constants table of the lane: pinned, referenced, never typed."""

from fractions import Fraction

import pytest

from app.factory.kernel.exact import Reject
from app.factory.lanes.physics_c12.consts import LOCAL, PHRASE, constant, lane_constants_hash
from app.factory.lanes.physics_c12.models import ALL_MODELS
from app.factory.lanes.physics_c12.quantities import to_si

# Changing a house value changes this hash on purpose: edit the table, then re-pin it in review.
PINNED_HASH = "b35d8905fee032b54e4e4b55820f5062e6e21588c4b633ea04ca57397e8704c9"


def test_the_lane_table_is_pinned():
    assert lane_constants_hash() == PINNED_HASH


def test_school_values_are_what_the_task_says():
    assert constant("g_earth").value == "9.8" and constant("e_charge").value == "1.6e-19"
    assert constant("h_planck").value == "6.63e-34" and constant("c_light").value == "3e8"
    assert constant("eps0").value == "8.85e-12" and constant("k_coulomb").value == "9e9"
    assert to_si(constant("mu0").value, constant("mu0").unit) == Fraction(1256, 10**9)


def test_unknown_constant_is_refused():
    with pytest.raises(Reject):
        constant("not_a_constant")


def test_every_constant_a_model_uses_exists_and_has_stem_words():
    used = {cid for m in ALL_MODELS.values() for cid in m.consts.values()}
    for cid in used:
        constant(cid)
        assert cid in PHRASE
    assert {c.id for c in LOCAL} >= {"k_coulomb", "eps0", "mu0"}
