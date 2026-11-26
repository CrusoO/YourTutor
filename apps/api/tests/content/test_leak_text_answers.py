"""Answers that are text with commas (chemical names, lists) must not crash the hint-leak check."""

from __future__ import annotations

import pytest

from app.content.leak import hint_leaks_answer


@pytest.mark.parametrize(
    ("hint", "answer", "leaks"),
    [
        ("The name is 2,2-dimethylpropane.", "2,2-dimethylpropane", True),
        ("Count the carbon atoms in the longest chain.", "2,2-dimethylpropane", False),
        ("The first three primes are 2, 3, 5.", "2, 3, 5", True),
        ("Think about the first few primes.", "2, 3, 5", False),
    ],
)
def test_comma_answers_are_compared_as_text(hint: str, answer: str, leaks: bool) -> None:
    assert hint_leaks_answer(hint, answer) is leaks


def test_ordinary_answers_behave_as_before() -> None:
    assert hint_leaks_answer("The value is 12.", "12") is True
    assert hint_leaks_answer("Use 120 as the total.", "12") is False
