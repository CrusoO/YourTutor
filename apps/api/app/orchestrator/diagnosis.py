"""Diagnosis engine (ARCHITECTURE §10): why was the answer wrong? Pure, no I/O.

`classify` runs before any hint or feedback is chosen (R30). First match wins:

1. misconception          the answer equals an authored misconception formula output
2. slip                   skill at ladder >= 4, first attempt on the item, and the answer is inside
                          an authored `slip_patterns` set (sign flip, off by a little, values)
3. prerequisite_gap       the matched misconception remediates a prerequisite, or the answer matches
                          an authored `prereq_signatures` value
4. incomplete_procedure   the answer equals an authored intermediate step value
5. disengagement          three fast answers in a row, or help opened without an attempt three times
6. generic                none of the above

A correct answer is class `none`. The result is stored on the event as `payload.diagnosis`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.content.math_parse import ParseError, expressions_equivalent, parse_math
from app.learner.types import LearnerState
from app.orchestrator.types import CatalogItem, SessionState

CLASSES = (
    "none",
    "misconception",
    "slip",
    "prerequisite_gap",
    "incomplete_procedure",
    "disengagement",
    "generic",
)

SLIP_MIN_LEVEL = 4
FAST_STREAK_LIMIT = 3  # R35
HELP_WITHOUT_ATTEMPT_LIMIT = 3  # R35
DEFAULT_OFF_BY = 1.0

_VAR_PREFIX = re.compile(r"^\s*[a-zA-Z]\s*=\s*(?!=)")


@dataclass(frozen=True)
class Diagnosis:
    kind: str
    detail: str | None = None

    def as_payload(self) -> dict[str, str | None]:
        return {"class": self.kind, "detail": self.detail}


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _value(text: str) -> float | None:
    """A response as a number, accepting `x = 4` style answers. None when it is not one."""
    stripped = _VAR_PREFIX.sub("", text.strip())
    if not stripped:
        return None
    try:
        return float(parse_math(stripped).evalf())
    except (ParseError, TypeError, ValueError):
        return None


def _same_value(left: str, right: str) -> bool:
    a = _VAR_PREFIX.sub("", left.strip())
    b = _VAR_PREFIX.sub("", right.strip())
    if not a or not b:
        return False
    if _squash(a) == _squash(b):
        return True
    return expressions_equivalent(a, b)


def _matches_any(response: str, values: Any) -> str | None:
    for candidate in values:
        if _same_value(response, str(candidate)):
            return str(candidate)
    return None


def _misconception(item: CatalogItem, response: str) -> str | None:
    text = response.strip()
    for mid, answers in item.misconception_rules:
        if text in answers or _matches_any(text, answers) is not None:
            return mid
    return None


def _slip(item: CatalogItem, response: str) -> str | None:
    got = _value(response)
    want = _value(item.answer_sympy)
    for pattern in item.slip_patterns:
        kind = str(pattern.get("kind"))
        if kind == "values" and _matches_any(response, pattern.get("values") or ()) is not None:
            return kind
        if got is None or want is None:
            continue
        if kind == "sign_flip" and want != 0 and abs(got + want) < 1e-9:
            return kind
        if kind == "off_by":
            limit = float(pattern.get("max_distance", DEFAULT_OFF_BY))
            if 0 < abs(got - want) <= limit + 1e-9:
                return kind
    return None


def _prerequisite(
    item: CatalogItem, response: str, matched: str | None, session: SessionState
) -> str | None:
    if matched is not None:
        remedial = session.misconception_remedial.get(matched)
        if remedial and remedial in session.prerequisites.get(item.primary_skill, ()):
            return remedial
    for signature in item.prereq_signatures:
        if _matches_any(response, signature.get("values") or ()) is not None:
            return str(signature.get("skill_id"))
    return None


def classify(
    item: CatalogItem,
    response: str,
    verifier_result: bool,
    learner: LearnerState,
    session: SessionState,
) -> Diagnosis:
    if verifier_result:
        return Diagnosis("none")
    text = response or ""
    matched = _misconception(item, text) if text else None
    if matched is not None:
        remedial = _prerequisite(item, text, matched, session)
        if remedial is not None:
            return Diagnosis("prerequisite_gap", remedial)
        return Diagnosis("misconception", matched)
    ladder = learner.ladders.get(item.primary_skill)
    first_attempt = session.last_wrong_item_id != item.id
    if text and ladder is not None and ladder.level >= SLIP_MIN_LEVEL and first_attempt:
        slip = _slip(item, text)
        if slip is not None:
            return Diagnosis("slip", slip)
    if text:
        remedial = _prerequisite(item, text, None, session)
        if remedial is not None:
            return Diagnosis("prerequisite_gap", remedial)
        step = _matches_any(text, item.intermediate_values)
        if step is not None:
            return Diagnosis("incomplete_procedure", step)
    if session.fast_streak >= FAST_STREAK_LIMIT:
        return Diagnosis("disengagement", "fast_answers")
    if session.help_without_attempt >= HELP_WITHOUT_ATTEMPT_LIMIT:
        return Diagnosis("disengagement", "help_without_attempt")
    return Diagnosis("generic")
