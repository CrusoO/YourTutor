"""Ask input safety and the current-item guard (ARCHITECTURE section 12.3). Pure.

Order: clean the question (length, personal details), then check distress, injection and
moderation, then the current-item guard. Student text is data; none of these checks follow it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ask.config import SafetyLists
from app.llm.rules import LlmRules, default_rules

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")
URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
NUMBER = re.compile(r"\d+(?:\.\d+)?")
MATH_TOKEN = re.compile(r"^[a-z]$|^[\d()+\-*/^.=a-z]*[\d()+\-*/^.=][\d()+\-*/^.=a-z]*$")


@dataclass(frozen=True)
class Cleaned:
    text: str
    pii_removed: bool
    too_long: bool
    empty: bool


def clean_question(raw: str, max_chars: int) -> Cleaned:
    text = " ".join(raw.split())
    if not text:
        return Cleaned("", False, False, True)
    if len(text) > max_chars:
        return Cleaned(text[:max_chars], False, True, False)
    stripped = URL.sub("[removed]", EMAIL.sub("[removed]", PHONE.sub("[removed]", text)))
    return Cleaned(stripped, stripped != text, False, False)


@dataclass(frozen=True)
class Verdict:
    kind: str  # ok | distress | injection | moderation
    detail: str = ""


def screen(text: str, lists: SafetyLists, rules: LlmRules | None = None) -> Verdict:
    rules = rules or default_rules()
    lowered = text.lower()
    if any(term in lowered for term in lists.distress_terms):
        return Verdict("distress")
    for pattern in lists.injection_patterns:
        if re.search(pattern, lowered):
            return Verdict("injection", pattern)
    if any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in rules.blocked_terms):
        return Verdict("moderation")
    return Verdict("ok")


def _numbers(text: str) -> set[str]:
    return set(NUMBER.findall(text))


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def _equations(stem: str) -> list[str]:
    """Each equation in the stem with the words around it dropped, spaces removed."""
    out: list[str] = []
    for part in re.split(r"[.?!;,](?!\d)\s", stem.lower()):
        if "=" not in part:
            continue
        kept = [t for t in part.split() if MATH_TOKEN.match(t)]
        piece = "".join(kept)
        if "=" in piece and len(piece) >= 3:
            out.append(piece)
    return out


def targets_current_item(question: str, item_stem: str | None, lists: SafetyLists) -> str | None:
    """Why this question is about the item being practised (None: it is a general question).

    Three signals: the question contains an equation from the stem; it repeats two or more of the
    stem's numbers; or it asks for the answer of "this" while an item is on screen.
    """
    if not item_stem:
        return None
    asked, stem = question.lower(), item_stem.lower()
    for equation in _equations(stem):
        if equation in _compact(asked):
            return "stem_expression"
    shared = _numbers(stem) & _numbers(asked)
    if len(shared) >= 2:
        return "stem_numbers"
    if any(phrase in asked for phrase in lists.solve_intent_phrases):
        return "solve_intent"
    return None
