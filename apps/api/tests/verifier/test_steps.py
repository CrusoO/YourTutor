"""Pure step checker: per-line states and the final verdict (no database, no network)."""

from __future__ import annotations

import pytest

from app.verifier.steps import (
    HINT_SIGN_READ,
    OK,
    SKIPPED,
    UNREADABLE,
    WRONG_STEP,
    check_steps,
)

Q = "x^2 - 7x + 10 = 0"


def states(question: str, lines: list[str]) -> list[str]:
    return [r.state for r in check_steps(question, lines).lines]


def test_right_path() -> None:
    lines = ["(x-2)(x-5)=0", "x-2=0 or x-5=0", "x=2 or x=5"]
    report = check_steps(Q, lines)
    assert [r.state for r in report.lines] == [OK, OK, OK]
    assert report.verdict == "correct"


def test_sign_flip_path_is_wrong_and_named() -> None:
    report = check_steps(Q, ["(x-2)(x-5)=0", "x-2=0 or x-5=0", "x=-2 or x=-5"])
    assert [r.state for r in report.lines] == [OK, OK, WRONG_STEP]
    assert report.lines[2].hint_key == HINT_SIGN_READ
    assert report.verdict == "wrong"


def test_single_factor_sign_flip() -> None:
    report = check_steps("x - 5 = 0", ["x = -5"])
    assert report.lines[0].state == WRONG_STEP
    assert report.lines[0].hint_key == HINT_SIGN_READ
    assert check_steps("x - 5 = 0", ["x = 5"]).lines[0].state == OK


@pytest.mark.parametrize(
    ("question", "lines", "expected", "verdict"),
    [
        (Q, ["x^2 - 7x = -10"], [OK], "not_final"),  # moving a term across, sign kept right
        (Q, ["x^2 - 7x = 10"], [WRONG_STEP], "not_final"),  # moved without flipping
        (Q, ["(x-2)(x-5)"], [OK], "not_final"),  # an expression equal to the left side
        (Q, ["2x^2 - 14x + 20 = 0"], [OK], "not_final"),  # scaled: same roots
        (Q, ["(x+2)(x+5)=0"], [WRONG_STEP], "not_final"),
        (Q, ["x = 2"], [WRONG_STEP], "wrong"),  # a root lost
        (Q, ["x = 2 or x = 5"], [OK], "correct"),
        (Q, ["x = 5, x = 2"], [OK], "correct"),
        (Q, ["x = 2 or 5"], [OK], "correct"),
        ("x^2 - 6x + 9 = 0", ["(x-3)^2 = 0", "x = 3"], [OK, OK], "correct"),
        ("x^2 - 6x + 9 = 0", ["(x-3)(x-3)=0", "x=3 or x=3"], [OK, OK], "correct"),
        ("2x^2 - 5x + 2 = 0", ["(2x-1)(x-2)=0", "x = 1/2 or x = 2"], [OK, OK], "correct"),
        ("2x^2 - 5x + 2 = 0", ["x = 0.5 or x = 2"], [OK], "correct"),
        ("x^2 + 4 = 0", ["x^2 = -4", "no real roots"], [OK, OK], "correct"),
        ("x^2 + 4 = 0", ["x = 2"], [WRONG_STEP], "wrong"),
        ("x^2 = 9", ["x = ±3"], [OK], "correct"),
        ("x^2 = 9", ["x = 3 or x = −3"], [OK], "correct"),  # U+2212
        ("x^2 = 9", ["x = 3 or x = –3"], [OK], "correct"),  # U+2013
        ("x^2 = 9", ["x² = 9"], [OK], "not_final"),
        (Q, ["x(x-7) = -10"], [OK], "not_final"),  # implicit multiplication
        (Q, ["x^2 - 7 x + 10 = 0"], [OK], "not_final"),
    ],
)
def test_cases(question: str, lines: list[str], expected: list[str], verdict: str) -> None:
    report = check_steps(question, lines)
    assert [r.state for r in report.lines] == expected
    assert report.verdict == verdict


def test_dash_variants_are_the_same_line() -> None:
    forms = ["x^2 \u2212 7x + 10 = 0", "x^2 \u2013 7x + 10 = 0", "x^2 - 7x + 10 = 0"]
    assert [states(Q, [f]) for f in forms] == [[OK]] * 3


def test_unreadable_is_not_wrong_and_blocks_later_claims() -> None:
    report = check_steps(Q, ["(x-2)(x-5)=0", "hello there", "x=-2 or x=-5", "x = 2 or x = 5"])
    assert [r.state for r in report.lines] == [OK, UNREADABLE, SKIPPED, SKIPPED]
    assert all(r.hint_key is None for r in report.lines)
    # the final answer is still judged on its own, so a right answer is recognised
    assert report.verdict == "correct"


def test_unreadable_never_counts_as_a_mistake() -> None:
    for junk in ["???", "x = ", "3 +", "sqrt(4)", "x = y", "1/0 = x", "a b c", "x=1=2"]:
        report = check_steps(Q, [junk])
        assert report.lines[0].state == UNREADABLE, junk
        assert report.lines[0].hint_key is None


def test_blank_lines_are_skipped() -> None:
    assert states(Q, ["", "  ", "x = 2 or x = 5"]) == [SKIPPED, SKIPPED, OK]


def test_a_wrong_line_does_not_become_the_baseline() -> None:
    assert states(Q, ["x = -2 or x = -5", "x = 2 or x = 5"]) == [WRONG_STEP, OK]


def test_power_bombs_are_refused_not_computed() -> None:
    for bomb in ["9^9^9 = x", "x^99999 = 0", "2^(9^9) = x"]:
        assert states(Q, [bomb]) == [UNREADABLE]


def test_unsupported_question() -> None:
    report = check_steps("x + y = 3", ["x = 1"])
    assert not report.supported and report.verdict == "unchecked"
    assert check_steps("not an equation", ["x"]).supported is False


def test_irrational_roots_are_unchecked_not_wrong() -> None:
    assert check_steps("x^2 - 2 = 0", ["x = 1"]).verdict == "unchecked"


def test_deterministic() -> None:
    lines = ["(x-2)(x-5)=0", "x=-2 or x=-5", "junk!", "x=2 or x=5"]
    first = check_steps(Q, lines)
    assert all(check_steps(Q, lines) == first for _ in range(5))
    assert first.as_dict() == check_steps(Q, lines).as_dict()


def test_verdict_for_empty_input() -> None:
    assert check_steps(Q, []).verdict == "none"
    assert check_steps(Q, [" "]).verdict == "none"
