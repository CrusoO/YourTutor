"""Check a lesson quiz's marked answer with the maths verifier, not the model's say-so.

A generated lesson names which option is right. Where the question is plain arithmetic or one
equation in one unknown, this module solves it with the same allowlist parser the practice
verifier uses and compares the result with the options:

- verified   exactly one option has the solved value, and it is the option the model marked;
- conflict   the options and the solved value disagree with the mark (or with each other): the
             block is dropped, because either the quiz or the mark is wrong;
- unverified the question is not something the solver can read (a concept, a word problem, more
             than one equation), so the block is kept and marked as not machine-checked.

It never overrides the mark: a question that merely mentions an equation (say, "what is 3x when
3x + 5 = 17?") must not flip a right answer to a wrong one, so any doubt is a dropped block, not
a changed one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

import sympy

from app.content.math_parse import ParseError, parse_math
from app.content.stem_solve import Unsolvable, solve_extracted

Status = Literal["verified", "conflict", "unverified"]

MAX_SPAN_CHARS = 60
_TOKEN_OK = re.compile(r"[\dA-Za-z.+\-*/^×÷−=()]+")
_LETTER_RUN = re.compile(r"[A-Za-z]{2,}")
_TRAILING = ".,;:?!"
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_OPERATOR = re.compile(r"[+\-*/^×÷−=]")


@dataclass(frozen=True)
class Verdict:
    status: Status
    detail: str = ""


def _mathy(token: str) -> bool:
    return bool(_TOKEN_OK.fullmatch(token)) and not _LETTER_RUN.search(token)


def math_spans(text: str) -> list[str]:
    """Runs of consecutive maths-looking words that hold a digit and an operator or "=".

    "Solve 3x + 5 = 20 for x." -> ["3x + 5 = 20"]. Prose words break a run.
    """
    spans: list[str] = []
    run: list[str] = []

    def close() -> None:
        span = " ".join(run)
        if (
            run
            and re.search(r"\d", span)
            and _OPERATOR.search(span)
            and len(span) <= MAX_SPAN_CHARS
        ):
            spans.append(span)
        run.clear()

    for raw in text.split():
        token = raw.rstrip(_TRAILING)
        if token and _mathy(token):
            run.append(token)
            if raw != token:  # a sentence ended here
                close()
        else:
            close()
    close()
    return spans


def _value(text: str) -> sympy.Expr | None:
    """What an option or an expression is worth as a number, or None if it is not a plain value."""
    cleaned = text.strip().rstrip(_TRAILING)
    if not cleaned or not all(_mathy(t) for t in cleaned.split()):
        return None
    try:
        value = parse_math(cleaned)
    except (ParseError, ValueError, TypeError):
        return None
    return None if value.free_symbols else value


def _solved(question: str) -> sympy.Expr | None:
    """The one value the question's single equation or sum comes to, or None."""
    spans = math_spans(question)
    if len(spans) != 1:
        return None
    # Every number in the question must be part of what is solved: "3/4 of 8" has an 8 left over,
    # so reading only "3/4" would wrongly call the right answer wrong.
    if sorted(_NUMBER.findall(question)) != sorted(_NUMBER.findall(spans[0])):
        return None
    try:
        return solve_extracted(spans[0])
    except (Unsolvable, ParseError, ValueError, TypeError, NotImplementedError):
        return None


def verify_choice(question: str, options: list[str], marked: int) -> Verdict:
    """Compare the marked option with the question's solved value. See the module docstring."""
    solved = _solved(question)
    if solved is None:
        return Verdict("unverified", "no single sum or equation in the question")
    values = [_value(option) for option in options]
    if sum(v is not None for v in values) < 2:
        return Verdict("unverified", "the options are not plain values")
    matches = [i for i, v in enumerate(values) if v is not None and sympy.simplify(v - solved) == 0]
    if len(matches) == 1 and matches[0] == marked:
        return Verdict("verified")
    if not matches and 0 <= marked < len(values) and values[marked] is None:
        return Verdict(
            "unverified", "the marked option is not a value (for example 'none of these')"
        )
    return Verdict("conflict", f"solved {solved}; options matching: {matches}; marked: {marked}")
