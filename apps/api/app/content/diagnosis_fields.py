"""Draft values for the G2 item fields, derived from an item's own solution steps.

These are machine drafts for a teacher to edit: they are English-only text with the usual reviewer
placeholders for the other languages, and they stay in items with `status: draft`. The step hints
contain no numbers at all, so they cannot leak the answer; the validator checks that anyway.
"""

from __future__ import annotations

import re
from typing import Any

from app.content.math_parse import ParseError, parse_math
from app.content.schema import Item, ItemType

NE = "<Nepali — to be filled by reviewer>"
AS = "<Assamese — to be filled by reviewer>"

_ORDINALS = (
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "tenth",
)
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_TERM = re.compile(r"-?\d+(?:\.\d+)?([a-zA-Z])\b")  # 3x -> "the x term"
_WORD = re.compile(r"[A-Za-z]{2,}")
_VAR_PREFIX = re.compile(r"^\s*[a-zA-Z]\s*=\s*")

MIN_MS = 2000
MAX_MS = 8000


def _loc(en: str) -> dict[str, str]:
    return {"en": en, "ne": NE, "as": AS}


def _ordinal(index: int) -> str:
    return _ORDINALS[index] if index < len(_ORDINALS) else "next"


def _step_hint(index: int, text: str, last: bool) -> str:
    where = _ordinal(index)
    if last:
        return (
            f"Almost there. Use the equation from the step before to find the value, "
            f"then check it in the original question ({where} step)."
        )
    if "=" in text:
        if index == 0:
            return (
                f"In the {where} step, turn the question into an equation using the numbers given."
            )
        return (
            f"In the {where} step, write the equation you get after the step before. "
            "Use the numbers from the question."
        )
    masked = _TERM.sub(r"the \1 term", text.strip())
    masked, count = _NUMBER.subn("the number", masked)
    if count >= 2:  # a bare calculation: say what to do, not what it equals
        return f"In the {where} step, do this part of the calculation on your own."
    return f"In the {where} step: {masked}"


def _numeric(text: str) -> bool:
    try:
        parse_math(_VAR_PREFIX.sub("", text.strip())).evalf()
    except (ParseError, TypeError, ValueError):
        return False
    return not _VAR_PREFIX.sub("", text.strip()).isalpha()


def _intermediate_values(item: Item) -> list[str]:
    final = {item.answer.sympy.strip(), *(a.strip() for a in item.answer.accept)}
    out: list[str] = []
    for step in item.solution_steps[:-1]:
        text = step.en.strip().rstrip(".")
        if "=" not in text or _WORD.search(text):  # only bare equations, not sentences
            continue
        left, _, right = text.partition("=")
        right = right.strip()
        candidates = [text]
        try:
            number = float(parse_math(right).evalf())
            candidates.append(str(int(number)) if number.is_integer() else str(number))
        except (ParseError, TypeError, ValueError):
            pass
        for candidate in candidates:
            if candidate and candidate not in final and candidate not in out and left.strip():
                out.append(candidate)
    return out


def draft_fields(item: Item) -> dict[str, Any]:
    """Draft the five G2 item fields (step hints, restate, slips, intermediates, min time)."""
    steps = item.solution_steps
    step_hints = [_loc(_step_hint(i, step.en, i == len(steps) - 1)) for i, step in enumerate(steps)]
    restate = (
        f"Let's read the question again, slowly: {item.stem.en} "
        "What are you asked to find? What do you already know?"
    )
    numeric = item.type != ItemType.mcq and _numeric(item.answer.sympy)
    slips: list[dict[str, Any]] = (
        [{"kind": "sign_flip"}, {"kind": "off_by", "max_distance": 1}] if numeric else []
    )
    ms = max(MIN_MS, min(MAX_MS, 1200 + 45 * len(item.stem.en)))
    return {
        "step_hints": step_hints,
        "hint_restate": _loc(restate),
        "slip_patterns": slips,
        "intermediate_values": _intermediate_values(item),
        "min_plausible_ms": ms,
    }
