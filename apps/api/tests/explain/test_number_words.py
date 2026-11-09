"""Spelled-out numbers become digits, so the answer guard sees them."""

from __future__ import annotations

import pytest

from app.explain.answer_guard import ActiveItem, leaks
from app.explain.number_words import words_to_digits


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("It is twelve.", "It is 12."),
        ("Twelve!", "12!"),
        ("x is negative twenty-one", "x is -21"),
        ("x is minus twenty one", "x is -21"),
        ("a hundred and five apples", "a 105 apples"),
        ("two hundred thousand", "200000"),
        ("a dozen eggs", "a 12 eggs"),
        ("one two three", "1 2 3"),
        ("five and six", "5 and 6"),
        ("twenty one and three", "21 and 3"),
        ("minus the cost", "minus the cost"),
        ("बारह १२ है", "बारह 12 है"),
        ("no numbers here", "no numbers here"),
        ("", ""),
    ],
)
def test_words_to_digits(text: str, expected: str) -> None:
    assert words_to_digits(text) == expected


ACTIVE = ActiveItem("ITEM.G.1", ("12", "x=12"), (), False)


@pytest.mark.parametrize(
    "reply",
    ["It is twelve.", "So x equals Twelve", "The result: a dozen... no, twelve", "x है १२"],
)
def test_the_guard_catches_the_answer_spelled_out(reply: str) -> None:
    assert leaks(reply, ACTIVE)


@pytest.mark.parametrize(
    "reply", ["Count back three steps from fifteen.", "It is twenty-one apples", "Try 2 tens"]
)
def test_the_guard_leaves_other_numbers_alone(reply: str) -> None:
    assert not leaks(reply, ACTIVE)
