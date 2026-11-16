# ruff: noqa: E501
"""Exact arithmetic in Q(sqrt2, sqrt3): the lane's own number type."""

from fractions import Fraction

import pytest

from app.factory.lanes.maths.surd import S, fmt, sqrt_of


def test_basis_products_and_inverse():
    r2, r3 = sqrt_of(2), sqrt_of(3)
    assert r2 * r2 == 2 and r3 * r3 == 3 and r2 * r3 == S(0, 0, 0, 1)
    assert S(0, 0, 0, 1) * S(0, 0, 0, 1) == 6
    assert r3 * (1 / r3) == 1
    x = S(1, 1, 1, 1)
    assert x * x.inverse() == 1


def test_division_rationalises():
    assert fmt(S(1) / sqrt_of(3)) == "√3/3"
    assert fmt(S(10) / (sqrt_of(3) - 1)) == "5 + 5√3"


def test_formatting_is_canonical():
    assert fmt(S(0)) == "0"
    assert fmt(S(-3)) == "-3"
    assert fmt(S(0, 0, 10)) == "10√3"
    assert fmt(S(Fraction(1, 2), 0, Fraction(-1, 2))) == "1/2 - √3/2"
    assert fmt(S(0, 0, 0, 1)) == "√6"


@pytest.mark.parametrize("n", [0, 4, 8, 12, 18, 24])
def test_sqrt_of_inside_the_field(n):
    value = sqrt_of(n)
    assert value * value == n


def test_sqrt_outside_the_field_refuses():
    with pytest.raises(ValueError):
        sqrt_of(5)
    with pytest.raises(ValueError):
        sqrt_of(-1)


def test_inverse_of_zero_raises():
    with pytest.raises(ZeroDivisionError):
        S(0).inverse()
