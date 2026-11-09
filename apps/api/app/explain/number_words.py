"""Spell numbers as digits, so the answer guard also catches "twelve" and Devanagari digits.

The leak check compares digits. A reply that says "the result is twelve" would pass it, so the
guard checks the text twice: as written, and with spelled-out English numbers and Devanagari
digits turned into ordinary ones.

Known gap: Hindi and Hinglish number *words* (for example "barah") are not converted. They need a
reviewed word list from a native speaker; until then they are not caught.
"""

from __future__ import annotations

import re

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "dozen": 12,
}  # fmt: skip
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}  # fmt: skip
_SCALES = {"hundred": 100, "thousand": 1000}
_NEGATIVE = {"negative", "minus"}
_DEVANAGARI = str.maketrans("०१२३४५६७८९", "0123456789")
_TOKEN = re.compile(r"[A-Za-z]+|\d+|\s+|[^\sA-Za-z\d]")


def _is_number_word(word: str) -> bool:
    return word in _UNITS or word in _TENS or word in _SCALES


def _value(words: list[str]) -> int:
    """The number a run of number words spells, e.g. ["one", "hundred", "five"] -> 105."""
    total = 0
    current = 0
    for word in words:
        if word in _UNITS:
            current += _UNITS[word]
        elif word in _TENS:
            current += _TENS[word]
        elif word == "hundred":
            current = max(current, 1) * 100
        else:  # thousand
            total += max(current, 1) * 1000
            current = 0
    return total + current


def _joins(prev: str, word: str) -> bool:
    """Can `word` continue a number that so far ends in `prev`? ("twenty" "one", "two" "hundred")"""
    if word in _SCALES:
        return prev in _UNITS or prev in _TENS or (prev == "hundred" and word == "thousand")
    if prev in _TENS:
        return word in _UNITS and 1 <= _UNITS[word] <= 9
    if prev in _SCALES:
        return word in _UNITS or word in _TENS
    return False


def words_to_digits(text: str) -> str:
    """`text` with spelled-out English numbers and Devanagari digits written as digits.

    "x is negative twenty-one" -> "x is -21"; "a hundred and five" -> "105"; "one two three"
    stays three numbers; other words are kept.
    """
    tokens = _TOKEN.findall(text.translate(_DEVANAGARI))
    out: list[str] = []
    i = 0
    while i < len(tokens):
        word = tokens[i].lower()
        sign = ""
        start = i
        if word in _NEGATIVE:
            start = _skip_gap(tokens, i + 1)
            if start >= len(tokens) or not _is_number_word(tokens[start].lower()):
                out.append(tokens[i])
                i += 1
                continue
            sign = "-"
        elif not _is_number_word(word):
            out.append(tokens[i])
            i += 1
            continue
        run = [tokens[start].lower()]
        end = start + 1
        while True:
            nxt = _skip_gap(tokens, end, allow_and=run[-1] in _SCALES)
            if nxt >= len(tokens):
                break
            candidate = tokens[nxt].lower()
            if not (_is_number_word(candidate) and _joins(run[-1], candidate)):
                break
            run.append(candidate)
            end = nxt + 1
        out.append(f"{sign}{_value(run)}")
        i = end
    return "".join(out)


def _skip_gap(tokens: list[str], start: int, *, allow_and: bool = False) -> int:
    """The index after any spaces, a hyphen and (after hundred or thousand) "and"."""
    k = start
    while k < len(tokens):
        piece = tokens[k]
        if piece.isspace() or piece == "-" or (allow_and and piece.lower() == "and"):
            k += 1
            continue
        break
    return k
