"""Pilot metrics (PLAN section 11): aggregates from real events, no names, no per-student rows.

Every number is a count or a share over the whole deployment (or the optional window). Nothing
here ranks or compares children, and the report carries no identifiers. `python -m app.metrics
pilot` prints it; `GET /admin/metrics/pilot` serves it to admins.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import as_utc, now_utc
from app.db.models import (
    ContentGapRow,
    EventRow,
    LlmCallRow,
    MasteryRow,
    SessionRow,
    TeacherAlertRow,
)

INTERVENTION_RULES = frozenset(
    {"R07", "R09", "R31", "R33", "R35"}
)  # hint, reveal, check, probe, break
FINISHED = frozenset({"soft_cap", "hard_cap", "chapter_complete"})


def _share(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def pilot_metrics(db: Session, since: datetime | None = None) -> dict[str, Any]:
    now = now_utc()
    start = since or (now - timedelta(days=3650))
    rows = db.execute(
        select(EventRow, SessionRow)
        .join(SessionRow, EventRow.session_id == SessionRow.id)
        .where(SessionRow.type == "practice", EventRow.created_at >= start)
        .order_by(EventRow.session_id, EventRow.created_at, EventRow.id)
    ).all()

    mistakes = followed = 0
    mix: Counter[str] = Counter()
    first_seen: set[tuple[object, str]] = set()
    hinted: set[tuple[object, str]] = set()
    first_answers = first_unhinted_correct = 0
    days_by_student: dict[object, set[Any]] = defaultdict(set)
    lessons = 0
    for event, session in rows:
        days_by_student[session.student_id].add(as_utc(event.created_at).date())
        key = (event.session_id, event.item_id or "")
        if event.event_type in {"request_help", "request_hint"} and event.item_id:
            hinted.add(key)
        if event.event_type == "continue" and event.state_before == "worked_example":
            lessons += 1
        if event.event_type != "answer" or not event.item_id:
            continue
        if key not in first_seen:
            first_seen.add(key)
            first_answers += 1
            if event.correct and key not in hinted:
                first_unhinted_correct += 1
        if event.correct is False:
            mistakes += 1
            followed += event.rule_id in INTERVENTION_RULES
            diagnosis = (event.payload or {}).get("diagnosis") or {}
            if isinstance(diagnosis, dict) and diagnosis.get("class"):
                mix[str(diagnosis["class"])] += 1

    sessions = db.scalars(
        select(SessionRow).where(SessionRow.type == "practice", SessionRow.started_at >= start)
    ).all()
    ended = [s for s in sessions if s.ended_at is not None]
    week_start = (now - timedelta(days=7)).date()
    recent_days = [len([d for d in days if d >= week_start]) for days in days_by_student.values()]

    mastery = db.scalars(select(MasteryRow)).all()
    started = [m for m in mastery if m.ladder_level > 0]
    days_to_level_4 = _days_to_level_4(db, mastery)

    alerts = db.scalars(
        select(TeacherAlertRow).where(TeacherAlertRow.type == "wheel_spinning")
    ).all()
    calls = db.scalars(select(LlmCallRow).where(LlmCallRow.created_at >= start)).all()
    answered = Counter(c.outcome for c in calls if c.purpose == "answer_doubt")
    used = [c for c in calls if c.outcome in {"llm", "fallback"}]
    gaps = db.scalars(select(ContentGapRow).where(ContentGapRow.created_at >= start)).all()

    return {
        "generated_at": now.isoformat(),
        "window_start": start.isoformat() if since else None,
        "students_with_practice": len(days_by_student),
        "mistakes_with_intervention": {
            "mistakes": mistakes,
            "followed": followed,
            "share": _share(followed, mistakes),
            "target": 0.9,
        },
        "diagnosis_mix": dict(sorted(mix.items())),
        "unhinted_correct_rate": {
            "first_answers": first_answers,
            "unhinted_correct": first_unhinted_correct,
            "share": _share(first_unhinted_correct, first_answers),
        },
        "ladder": {
            "skills_started": len(started),
            "reached_level_4": sum(m.ladder_level >= 4 for m in started),
            "reached_level_7": sum(m.ladder_level >= 7 for m in started),
            "median_days_to_level_4": days_to_level_4,
        },
        "wheel_spinning": {
            "alerts": len(alerts),
            "resolved": sum(a.resolved_at is not None for a in alerts),
            "resolution_share": _share(sum(a.resolved_at is not None for a in alerts), len(alerts)),
            "note": "alerts are only written for students whose family shared with a teacher",
        },
        "engagement": {
            "mean_active_days_last_7": round(statistics.mean(recent_days), 2)
            if recent_days
            else None,
            "sessions": len(sessions),
            "sessions_finished_by_cap_or_chapter": sum(s.ended_reason in FINISHED for s in ended),
            "session_completion_share": _share(
                sum(s.ended_reason in FINISHED for s in ended), len(ended)
            ),
            "lessons_completed": lessons,
        },
        "ask": {
            "calls": sum(answered.values()),
            "by_outcome": dict(sorted(answered.items())),
            "content_gaps": len(gaps),
        },
        "llm": {
            "calls": len(used),
            "fallback_share": _share(sum(c.outcome == "fallback" for c in used), len(used)),
            "tokens_in_per_100_calls": round(100 * sum(c.tokens_in for c in used) / len(used))
            if used
            else None,
            "tokens_out_per_100_calls": round(100 * sum(c.tokens_out for c in used) / len(used))
            if used
            else None,
            "note": "leak, tone and grounding rates come from `python -m app.llm.evals` and "
            "`python -m app.ask.evals`, not from live traffic",
        },
    }


def _days_to_level_4(db: Session, mastery: Sequence[MasteryRow]) -> float | None:
    """Median days from a student's first practice on a skill to the event that earned level 4."""
    spans: list[float] = []
    for row in mastery:
        ids = (row.ladder_evidence or {}).get("4") or []
        if not ids:
            continue
        done = db.scalar(
            select(EventRow.created_at).where(EventRow.client_event_id == _uuid(ids[-1]))
        )
        first = db.scalar(
            select(EventRow.created_at)
            .join(SessionRow, EventRow.session_id == SessionRow.id)
            .where(SessionRow.student_id == row.student_id)
            .order_by(EventRow.created_at)
            .limit(1)
        )
        if done and first:
            spans.append((as_utc(done) - as_utc(first)).total_seconds() / 86_400)
    return round(statistics.median(spans), 2) if spans else None


def _uuid(value: str) -> Any:
    import uuid

    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None
