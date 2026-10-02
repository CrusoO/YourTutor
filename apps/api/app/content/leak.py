from __future__ import annotations

import re

from app.content.math_parse import expressions_equivalent, find_numbers, normalize

_NUMERIC = re.compile(r"-?\d+(?:\.\d+)?$")


def _contains_token(hay: str, needle: str) -> bool:
    """True when needle appears as its own token, not as a substring of 10 or alone."""
    if not needle:
        return False
    if _NUMERIC.fullmatch(needle):
        return bool(re.search(rf"(?<![\d.]){re.escape(needle)}(?![\d.])", hay))
    return bool(re.search(rf"(?<![A-Za-z]){re.escape(needle)}(?![A-Za-z])", hay))


def hint_leaks_answer(hint: str, forbidden: str) -> bool:
    """True if hint level 1–2 contains the answer or an equivalent value."""
    hay = normalize(hint)
    needle = normalize(forbidden)
    if _contains_token(hay, needle):
        return True
    if expressions_equivalent(hint, forbidden):
        return True
    try:
        answer_numbers = set(find_numbers(forbidden))
    except Exception:  # noqa: BLE001
        answer_numbers = set()
    if not answer_numbers:
        return False
    hint_numbers = set(find_numbers(hint))
    for num in answer_numbers:
        if num in hint_numbers and expressions_equivalent(num, forbidden):
            return True
    return False
