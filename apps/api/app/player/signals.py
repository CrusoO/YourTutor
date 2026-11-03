"""What the player records about an answer beyond right or wrong, and what it says back.

Everything here is pure except `record_misconception_hit`, which writes one row.

- Confidence ("sure" or "unsure"): the learner's own rating, given before the answer is judged.
  It is the only way to tell a confident error from a guess, so it is stored but the live
  policy does not read it yet.
- Answer time: taken from the client but checked, because a wrong type or a negative number
  would otherwise reach the rules that treat very fast answers as disengagement.
- The diagnosis shown to the learner: only the classes that explain a wrong answer, never in a
  diagnostic or checkpoint session (those give no feedback), and never the authored internals.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ItemRow, MisconceptionHitRow, MisconceptionRow
from app.orchestrator.diagnosis import CLASSES
from app.orchestrator.types import SessionState

CONFIDENCE = frozenset({"sure", "unsure"})
ASSESSMENT_SESSIONS = frozenset({"diagnostic", "checkpoint"})
# Classes that explain *why* an answer was wrong ("generic" and "disengagement" do not).
EXPLAINABLE = frozenset({"misconception", "slip", "prerequisite_gap", "incomplete_procedure"})
CORRECTION_EVENT = "diagnosis_correction"


def clean_signals(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """The payload with confidence and answer time made safe. Unusable values are dropped."""
    cleaned = dict(payload)
    confidence = cleaned.get("confidence")
    if event_type != "answer" or not isinstance(confidence, str) or confidence not in CONFIDENCE:
        cleaned.pop("confidence", None)
    latency = cleaned.get("latency_ms")
    if isinstance(latency, bool) or not isinstance(latency, (int, float)) or latency < 0:
        cleaned.pop("latency_ms", None)
    else:
        cleaned["latency_ms"] = int(latency)
    return cleaned


def clean_correction(payload: dict[str, Any]) -> dict[str, Any]:
    """The learner's "that's not why": the class they disagreed with, if it is a known one."""
    diagnosed = payload.get("diagnosed")
    return {"diagnosed": diagnosed} if isinstance(diagnosed, str) and diagnosed in CLASSES else {}


def public_diagnosis(
    event_type: str, state: SessionState, extras: dict[str, Any], misconception_id: str | None
) -> dict[str, Any] | None:
    """What to show the learner about the answer just given, or None when nothing helps."""
    diagnosis = state.last_diagnosis
    if event_type != "answer" or not diagnosis:
        return None
    if extras.get("assessment") or state.session_type in ASSESSMENT_SESSIONS:
        return None
    kind = diagnosis.get("class")
    if kind not in EXPLAINABLE:
        return None
    shown: dict[str, Any] = {"class": kind}
    if kind == "misconception" and misconception_id:
        shown["misconception_id"] = misconception_id
    return shown


def record_misconception_hit(
    session: Session,
    student_id: uuid.UUID,
    event_type: str,
    state: SessionState,
    misconception_id: str | None,
    item_id: str | None,
    now: datetime,
) -> bool:
    """Write one row when an answer matched a known misconception; says whether it did.

    Both foreign keys are checked first: an unknown id must never break the answer that caused it.
    """
    diagnosis = state.last_diagnosis
    if event_type != "answer" or not diagnosis or diagnosis.get("class") != "misconception":
        return False
    if not misconception_id or not item_id:
        return False
    if (
        session.get(MisconceptionRow, misconception_id) is None
        or session.get(ItemRow, item_id) is None
    ):
        return False
    session.add(
        MisconceptionHitRow(
            id=uuid.uuid4(),
            student_id=student_id,
            misconception_id=misconception_id,
            item_id=item_id,
            created_at=now,
        )
    )
    return True
