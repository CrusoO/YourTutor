"""Language and hint-role lints for rendered items."""

from __future__ import annotations

import re
from collections import defaultdict

_PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
_PAREN_LEFTOVER = re.compile(r"\(([A-Za-z]+(?:\s+[A-Za-z]+)*)\)")
_ADJ_REPEAT = re.compile(r"\b([A-Za-z]{2,})\s+\1\b", re.IGNORECASE)
_TOKEN = re.compile(r"[A-Za-z0-9]+")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_BOTH_SIDES_OF_N = re.compile(r"both sides of\s+-?\d+(?:\.\d+)?(?![x(\d])", re.IGNORECASE)
_TOTAL = re.compile(
    r"(?:together they (?:cost|are)|the whole trip is|add to)\s+"
    r"(-?\d+(?:\.\d+)?)(\s+[A-Za-z]+)?",
    re.IGNORECASE,
)
_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "to",
        "and",
        "or",
        "for",
        "in",
        "on",
        "is",
        "are",
        "be",
        "as",
        "at",
        "by",
        "from",
        "then",
        "than",
        "that",
        "this",
        "with",
        "both",
        "sides",
        "you",
        "do",
        "not",
        "yet",
        "first",
        "after",
        "what",
        "how",
        "will",
        "was",
        "were",
        "has",
        "have",
        "had",
        "it",
        "its",
        "if",
        "into",
        "out",
        "up",
        "so",
        "no",
        "yes",
        "x",
        "n",
        "plus",
        "minus",
        "solve",
        "for",
    }
)


def stem_number_roles(stem: str) -> dict[str, set[str]]:
    roles: dict[str, set[str]] = defaultdict(set)
    for match in re.finditer(r"(?<![A-Za-z0-9])(-?\d+(?:\.\d+)?)(?=x|\()", stem):
        roles[match.group(1)].add("coefficient")
    for match in re.finditer(r"(?<=/)(-?\d+(?:\.\d+)?)", stem):
        roles[match.group(1)].add("divisor")
    for match in _NUM.finditer(stem):
        number = match.group(0)
        after = stem[match.end() : match.end() + 1]
        before = stem[match.start() - 1] if match.start() else ""
        if after in {"x", "("}:
            continue
        if before == "/":
            continue
        roles[number].add("constant")
    return roles


def hint_role_collision(stem: str, hints: list[str]) -> str | None:
    roles = stem_number_roles(stem)
    mentioned: set[str] = set()
    for hint in hints:
        mentioned.update(_NUM.findall(hint))
    for number in mentioned:
        if len(roles.get(number, set())) > 1:
            return number
    return None


def question_unit(stem: str) -> str | None:
    lower = stem.lower()
    if "how many kilometre" in lower or "how many km" in lower:
        return "km"
    if "how many rupee" in lower:
        return "rupees"
    if "how old" in lower or "how many year" in lower:
        return "year"
    return None


def _unit_ok(word: str | None, wanted: str) -> bool:
    token = (word or "").strip().lower()
    if wanted == "km":
        return token in {"km", "kilometre", "kilometres", "kilometer", "kilometers"}
    if wanted == "rupees":
        return token in {"rupee", "rupees"}
    if wanted == "year":
        return token in {"year", "years"}
    return False


def missing_total_unit(stem: str) -> bool:
    wanted = question_unit(stem)
    if wanted is None:
        return False
    for match in _TOTAL.finditer(stem):
        if _unit_ok(match.group(2), wanted):
            return False
    return True


def lint_texts(texts: list[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for text in texts:
        if _PLACEHOLDER.search(text):
            errors.append(f"unresolved placeholder in {text[:80]!r}")
        leftover = _PAREN_LEFTOVER.search(text)
        if leftover:
            errors.append(f"parenthesised leftover word {leftover.group(0)!r}")
        adjacent = _ADJ_REPEAT.search(text)
        if adjacent:
            errors.append(f"repeated adjacent word {adjacent.group(1)!r}")
        tokens = [tok.lower() for tok in _TOKEN.findall(text)]
        for index, token in enumerate(tokens):
            if token in _STOP or token.isdigit():
                continue
            window = tokens[index + 1 : index + 7]
            if token in window:
                warnings.append(f"content word {token!r} repeats within 6 tokens")
                break
    return errors, warnings


def lint_item_texts(*, stem: str, hints: list[str], extras: list[str] | None = None) -> tuple[list[str], list[str]]:
    errors, warnings = lint_texts([stem, *hints, *(extras or [])])
    for hint in hints:
        if _BOTH_SIDES_OF_N.search(hint):
            errors.append(f"hint says 'both sides of N': {hint[:80]!r}")
    collided = hint_role_collision(stem, hints)
    if collided is not None:
        errors.append(f"hint number {collided} fills more than one stem role")
    if missing_total_unit(stem):
        errors.append("question unit is missing from the stem total")
    return errors, warnings
