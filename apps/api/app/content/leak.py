from __future__ import annotations

from app.content.math_parse import expressions_equivalent, find_numbers, normalize


def hint_leaks_answer(hint: str, forbidden: str) -> bool:
    """True if hint level 1–2 contains the answer or an equivalent value."""
    hay = normalize(hint)
    needle = normalize(forbidden)
    if needle and needle in hay:
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
        if num in hint_numbers and expressions_equivalent(num, num):
            # A shared number is a leak only when it equals the whole answer.
            if expressions_equivalent(num, forbidden):
                return True
    return False
