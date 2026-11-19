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

from dataclasses import dataclass

from app.content.answer_match import matches_any as _matches_any
from app.content.answer_match import value_of as _value
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


@dataclass(frozen=True)
class Diagnosis:
    kind: str
    detail: str | None = None

    def as_payload(self) -> dict[str, str | None]:
        return {"class": self.kind, "detail": self.detail}


def _misconceptions(item: CatalogItem, response: str) -> list[str]:
    """Every authored misconception whose output equals the response (order of authoring)."""
    text = response.strip()
    return [
        mid
        for mid, answers in item.misconception_rules
        if text in answers or _matches_any(text, answers) is not None
    ]


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


def find_causes(
    item: CatalogItem, response: str, session: SessionState, *, slip_allowed: bool
) -> tuple[Diagnosis, ...]:
    """Every cause that could explain a wrong response, most authoritative first.

    The order is the diagnosis precedence: a matched misconception (or the prerequisite it
    remediates), then a slip, then a prerequisite signature, then an intermediate step value.
    `classify` takes the first; the reason model weighs them all.
    """
    text = (response or "").strip()
    if not text:
        return ()
    found: list[Diagnosis] = []
    matched = _misconceptions(item, text)
    for mid in matched:
        remedial = _prerequisite(item, text, mid, session)
        found.append(
            Diagnosis("prerequisite_gap", remedial)
            if remedial is not None
            else Diagnosis("misconception", mid)
        )
    if slip_allowed:
        slip = _slip(item, text)
        if slip is not None:
            found.append(Diagnosis("slip", slip))
    if not matched:
        remedial = _prerequisite(item, text, None, session)
        if remedial is not None:
            found.append(Diagnosis("prerequisite_gap", remedial))
    step = _matches_any(text, item.intermediate_values)
    if step is not None:
        found.append(Diagnosis("incomplete_procedure", step))
    return tuple(found)


def slip_allowed(item: CatalogItem, learner: LearnerState, session: SessionState) -> bool:
    """A slip is only believed for a skilled learner on the first try at an item."""
    ladder = learner.ladders.get(item.primary_skill)
    first_attempt = session.last_wrong_item_id != item.id
    return ladder is not None and ladder.level >= SLIP_MIN_LEVEL and first_attempt


def classify(
    item: CatalogItem,
    response: str,
    verifier_result: bool,
    learner: LearnerState,
    session: SessionState,
) -> Diagnosis:
    if verifier_result:
        return Diagnosis("none")
    causes = find_causes(
        item, response or "", session, slip_allowed=slip_allowed(item, learner, session)
    )
    if causes:
        return causes[0]
    if session.fast_streak >= FAST_STREAK_LIMIT:
        return Diagnosis("disengagement", "fast_answers")
    if session.help_without_attempt >= HELP_WITHOUT_ATTEMPT_LIMIT:
        return Diagnosis("disengagement", "help_without_attempt")
    return Diagnosis("generic")
