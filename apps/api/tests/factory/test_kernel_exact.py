from fractions import Fraction

import pytest

from app.factory.kernel.exact import (
    Deadline,
    Reject,
    answer_matches,
    canon,
    canonical_json,
    chash,
    frac,
    rational_sqrt,
    round_half_up,
)
from app.factory.kernel.linalg import nullspace, primitive_integer, rank
from app.factory.kernel.poly import Poly


def test_frac_accepts_exact_forms_only():
    assert frac("0.5") == Fraction(1, 2) == frac("1/2") == frac(" 5e-1 ")
    assert frac(3) == 3 and frac(Fraction(2, 4)) == Fraction(1, 2)
    for bad in (0.5, True, "abc", "1/0x", "1e9999", "", None, "1" * 80):
        with pytest.raises(Reject):
            frac(bad)


def test_canon_is_stable_and_refuses_floats():
    assert canon({"a": ["2.0", 2, "1/2", "x"]}) == {"a": ["2", "2", "1/2", "x"]}
    assert canonical_json({"b": 1, "a": 2}) == '{"a":"2","b":"1"}'
    assert chash({"x": "0.50"}) == chash({"x": "1/2"})
    with pytest.raises(Reject):
        canon({"x": 0.1})


def test_rounding_half_up_and_matching():
    assert round_half_up(Fraction(5, 2), 0) == 3
    assert round_half_up(Fraction(-5, 2), 0) == -3
    assert round_half_up(Fraction(441, 10), 0) == 44
    assert answer_matches(Fraction(441, 10), "44.1") and not answer_matches(Fraction(441, 10), "44")
    assert answer_matches(Fraction(441, 10), "44", dp=0)
    with pytest.raises(Reject):
        round_half_up(Fraction(1), 99)


def test_rational_sqrt():
    assert rational_sqrt(Fraction(9, 4)) == Fraction(3, 2)
    assert rational_sqrt(Fraction(2)) is None and rational_sqrt(Fraction(-1)) is None


def test_deadline_rejects_after_expiry():
    with pytest.raises(Reject):
        Deadline(-1).check()


def test_poly_arithmetic_and_roots():
    p = Poly.from_roots(2, [(3, 1), (Fraction(-1, 2), 1)])
    assert p.c == (Fraction(-3), Fraction(-5), Fraction(2))  # 2x^2 - 5x - 3
    assert p.at(3) == 0 and p.at(Fraction(-1, 2)) == 0 and p.at(0) == -3
    assert (p - p).degree == -1 and (p * Poly([1, 1])).degree == 3
    assert Poly([1, 0, 0]) == Poly([1])
    with pytest.raises(Reject):
        Poly([1] * 20)


def test_linalg_rank_nullspace_primitive():
    m = [[Fraction(x) for x in row] for row in ([2, 0, -2], [0, 2, -1])]  # H2 + O2 -> H2O
    assert rank(m) == 2
    (vec,) = nullspace(m, 3)
    assert primitive_integer(vec) == [2, 1, 2]
    assert primitive_integer([Fraction(1, 2), Fraction(-1, 3)]) == [3, -2]
    with pytest.raises(Reject):
        primitive_integer([Fraction(0)])
