"""Child safety actions: PII stripping, and the one shared distress flow (ARCHITECTURE section 25).

When a student's own words signal distress on any free-text route (Ask, /explain, /explain/chat,
lessons, stories, explain-back, video prompts) the same flow runs:

  1. stop the topic: no model answer is given;
  2. a warm, authored message in the student's language, with the helplines from config;
  3. urgent risk: the open session ends and a flag appears for the guardian (and an alert for the
     teacher or school counsellor when the family shared; none for guests, who have no adult);
  4. LLM chat is paused for that student until the flag is acknowledged or a day passes;
  5. a minimal record: when, which category, which route. Never the words.

Exam stress (risk "concern") gets a gentler support message and a record only: no pause, no flag,
no alert. A child who says their parents will be angry must not be reported to those parents.

Layer 1 is the lexicon (`safety_lexicon`); Layer 2 is an optional classifier (`safety_classifier`).
The tutor never counsels; it only shows authored text.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ask.config import load_safety, message
from app.ask.guard import EMAIL, PHONE, URL, Verdict, screen
from app.auth.consent import has_scope
from app.auth.security import as_utc, now_utc
from app.db.models import SafetyFlagRow, SessionRow, StudentRow, TeacherAlertRow
from app.helplines import helplines_for
from app.registries.paths import config_dir
from app.safety_classifier import (
    SafetyClassifierClient,
    as_detection,
    classify_safely,
    collect_text,
    get_classifier,
    is_moderation,
    run_beside,
)
from app.safety_lexicon import CONCERN, NONE, URGENT, Detection

PAUSE = timedelta(hours=24)
EXAM_STRESS_KIND = "exam_stress"
_UNAVAILABLE_CHECKS = {"kind": "unavailable", "reason": "checks"}


def strip_pii(text: str) -> str:
    """Emails, phone numbers and links replaced before the text is stored or sent anywhere."""
    return URL.sub("[removed]", EMAIL.sub("[removed]", PHONE.sub("[removed]", text)))


# ---- detection ----------------------------------------------------------------------------------


def is_distress(text: str, language: str) -> bool:
    """True when the text is an urgent distress signal (Layer 1 plus the ask.yaml short list)."""
    verdict = screen(text, load_safety(language))
    return verdict.kind == "distress" and verdict.risk == URGENT


def detection_from_verdict(verdict: Verdict) -> Detection:
    return Detection(verdict.risk or URGENT, verdict.category or "distress")


def detection_of(text: str, language: str) -> Detection:
    """Layer 1 as a Detection (urgent, concern or none)."""
    verdict = screen(text, load_safety(language))
    if verdict.kind == "distress":
        return Detection(verdict.risk or URGENT, verdict.category or "distress")
    return Detection(NONE)


def assess_text(
    text: str, language: str, classifier: SafetyClassifierClient | None = None
) -> Detection:
    """Layer 1, then Layer 2 when a classifier is on and Layer 1 found nothing urgent."""
    found = detection_of(text, language)
    if found.risk == URGENT:
        return found
    client = classifier if classifier is not None else get_classifier()
    second = as_detection(classify_safely(text, "input", client))
    if second.risk == URGENT or (second.risk == CONCERN and found.risk == NONE):
        return second
    return found


# ---- the reply the student sees -----------------------------------------------------------------


def _status(language: str) -> str:
    data = yaml.safe_load((config_dir() / "ask.yaml").read_text("utf-8")) or {}
    return str((data.get("message_status") or {}).get(language) or "authored")


def _helplines_for(detection: Detection) -> list[dict[str, Any]]:
    if detection.risk == CONCERN:
        kinds = ("mental_health", "exam_counselling")
    elif detection.category == "abuse":
        kinds = ("child_protection", "mental_health")
    else:
        kinds = ("mental_health", "child_protection")
    return [h.public() for h in helplines_for(kinds)]


def distress_reply(detection: Detection, language: str) -> dict[str, Any]:
    """The authored reply for a detection. Pure: nothing is stored here."""
    concern = detection.risk == CONCERN
    return {
        "kind": "distress",
        "risk": detection.risk,
        "category": detection.category,
        "message": message("distress_support" if concern else "distress", language),
        "helplines": _helplines_for(detection),
        "message_status": _status(language),
    }


def paused_reply(language: str) -> dict[str, Any]:
    return {
        "kind": "distress",
        "risk": "paused",
        "category": "",
        "message": message("distress_paused", language),
        "helplines": _helplines_for(Detection(URGENT, "")),
        "message_status": _status(language),
    }


# ---- the flag, the pause and the record ---------------------------------------------------------


def raise_distress(
    db: Session, student: StudentRow, source: str, now: datetime | None = None
) -> SafetyFlagRow:
    moment = now or now_utc()
    flag = SafetyFlagRow(
        id=uuid.uuid4(),
        student_id=student.id,
        kind="distress",
        source=source,
        created_at=moment,
    )
    db.add(flag)
    for row in db.scalars(
        select(SessionRow).where(SessionRow.student_id == student.id, SessionRow.ended_at.is_(None))
    ):
        row.ended_at = moment
        row.ended_reason = "paused_distress"
        row.resumable = False
    if has_scope(db, student.id, "teacher_share"):
        db.add(
            TeacherAlertRow(
                id=uuid.uuid4(),
                student_id=student.id,
                skill_id="",
                type="distress",
                created_at=moment,
            )
        )
    db.flush()
    return flag


def apply_distress(
    db: Session,
    student: StudentRow,
    route: str,
    detection: Detection,
    now: datetime | None = None,
) -> SafetyFlagRow | None:
    """Store what the shared flow keeps. Urgent: flag, end the session, alert, pause. Concern: a
    record only (an acknowledged row, so it neither pauses nor shows on the guardian page)."""
    moment = now or now_utc()
    category = detection.category or "unknown"
    if detection.risk == URGENT:
        # source reads "<route>:<category>"; it never holds the words.
        return raise_distress(db, student, f"{route}:{category}", moment)
    if detection.risk == CONCERN:
        row = SafetyFlagRow(
            id=uuid.uuid4(),
            student_id=student.id,
            kind=EXAM_STRESS_KIND,
            source=f"{route}:{category}",
            created_at=moment,
            acknowledged_at=moment,
        )
        db.add(row)
        db.flush()
        return row
    return None


def run_distress_flow(
    db: Session,
    student: StudentRow,
    route: str,
    detection: Detection,
    language: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The whole shared flow for a detection: store the record, then return the reply to show."""
    apply_distress(db, student, route, detection, now)
    return distress_reply(detection, language)


# ---- guarding a model route ---------------------------------------------------------------------


def guarded_llm_route(
    db: Session,
    student_id: uuid.UUID,
    route: str,
    prompt: str,
    language: str,
    call: Callable[[], dict[str, Any]],
    classifier: SafetyClassifierClient | None = None,
) -> dict[str, Any]:
    """Run an explain route's `call` under the shared flow.

    - A student whose chat is paused gets the paused message and no model call.
    - The service's own Layer 1 check answers with kind "distress" before any model call; that
      result is recorded here and enriched.
    - With the classifier on, it runs beside `call` on the prompt; a hit discards the answer. It
      then checks the reply text; a hit replaces the reply with an "unavailable" result.
    """
    student = db.get(StudentRow, student_id)
    if student is None:
        return call()
    if is_paused(db, student_id):
        return paused_reply(language)
    client = classifier if classifier is not None else get_classifier()
    found, result = run_beside(prompt, call, client)
    if result.get("kind") == "distress":
        detection = Detection(
            str(result.get("risk") or URGENT), str(result.get("category") or "distress")
        )
        return run_distress_flow(db, student, route, detection, language)
    second = as_detection(found)
    if second.risk != NONE:
        return run_distress_flow(db, student, route, second, language)
    if is_moderation(found):
        return {"kind": "refused", "reason": "moderation", "message": message("refused", language)}
    if client is not None and result.get("kind") not in {"unavailable", "empty", "refused"}:
        out = classify_safely(collect_text(result), "output", client)
        if as_detection(out).risk != NONE or is_moderation(out):
            return dict(_UNAVAILABLE_CHECKS)
    return result


# ---- state --------------------------------------------------------------------------------------


def open_flags(db: Session, student_id: uuid.UUID) -> list[SafetyFlagRow]:
    return list(
        db.scalars(
            select(SafetyFlagRow)
            .where(SafetyFlagRow.student_id == student_id, SafetyFlagRow.acknowledged_at.is_(None))
            .order_by(SafetyFlagRow.created_at)
        )
    )


def is_paused(db: Session, student_id: uuid.UUID, now: datetime | None = None) -> bool:
    moment = now or now_utc()
    return any(moment - as_utc(f.created_at) < PAUSE for f in open_flags(db, student_id))


def acknowledge(db: Session, student_id: uuid.UUID, flag_id: uuid.UUID) -> bool:
    flag = db.get(SafetyFlagRow, flag_id)
    if flag is None or flag.student_id != student_id or flag.acknowledged_at is not None:
        return False
    flag.acknowledged_at = now_utc()
    for alert in db.scalars(
        select(TeacherAlertRow).where(
            TeacherAlertRow.student_id == student_id,
            TeacherAlertRow.type == "distress",
            TeacherAlertRow.resolved_at.is_(None),
        )
    ):
        alert.resolved_at = flag.acknowledged_at
    return True
