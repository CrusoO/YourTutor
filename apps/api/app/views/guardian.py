"""What a guardian sees: where the child is in each chapter, and what changed this week.

Everything here comes from the child's own events and mastery rows. Nothing ranks or compares
children, there are no scores or streaks, and a week with no practice reads as a calm "nothing
this week", not as a shortfall.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import as_utc
from app.config import settings
from app.db.models import EventRow, ItemRow, MasteryRow, SessionRow, SkillRow, StudentRow
from app.learner.chapters import student_chapter_skills, student_chapters
from app.learner.status import skill_status
from app.player.ladder_log import recompute_ladders
from app.player.runtime import _bkt_and_prereqs, _overlay_skills, load_catalog
from app.registries.locale_resolve import pick_localized_field

WEEK = timedelta(days=7)


def _titles(db: Session, skill_ids: list[str], locale: str) -> dict[str, str]:
    rows = db.scalars(select(SkillRow).where(SkillRow.id.in_(skill_ids))).all()
    return {row.id: pick_localized_field(dict(row.title or {}), locale) or row.id for row in rows}


def levels_at(db: Session, student: StudentRow, when: datetime) -> dict[str, int]:
    """Each skill's ladder level as it stood at `when`, recomputed from the event log."""
    skills = _overlay_skills(db, student)
    params, _ = _bkt_and_prereqs(db, skills)
    catalog = load_catalog(db, allow_draft=settings.allow_draft_content)
    ladders = recompute_ladders(db, student.id, catalog, params, now=when)
    return {sid: ladder.level for sid, ladder in ladders.items()}


def _local_date(moment: datetime, tz: ZoneInfo):
    return as_utc(moment).astimezone(tz).date()


def week_activity(db: Session, student: StudentRow, now: datetime) -> dict[str, Any]:
    """Counts from the last seven days of the child's events. No marks, no comparisons."""
    start = now - WEEK
    tz = ZoneInfo(student.timezone or "UTC")
    sessions = db.scalars(
        select(SessionRow).where(
            SessionRow.student_id == student.id,
            SessionRow.started_at >= start,
            SessionRow.started_at <= now,
            SessionRow.type == "practice",
        )
    ).all()
    session_ids = [s.id for s in sessions]
    answers: list[EventRow] = []
    if session_ids:
        answers = list(
            db.scalars(
                select(EventRow).where(
                    EventRow.session_id.in_(session_ids), EventRow.event_type == "answer"
                )
            )
        )
    item_ids = {e.item_id for e in answers if e.item_id}
    skills: set[str] = set()
    if item_ids:
        skills = {
            skill
            for skill in db.scalars(select(ItemRow.primary_skill).where(ItemRow.id.in_(item_ids)))
            if skill
        }
    days = {_local_date(s.started_at, tz) for s in sessions}
    return {
        "sessions": len(sessions),
        "days_active": len(days),
        "active_minutes": round(sum(s.active_ms for s in sessions) / 60_000),
        "questions_answered": len(answers),
        "skills_practised": sorted(skills),
    }


def week_summary(db: Session, student: StudentRow, now: datetime, locale: str) -> dict[str, Any]:
    """What was learned in the last seven days: skills whose ladder level rose, from real events."""
    before = levels_at(db, student, now - WEEK)
    after = levels_at(db, student, now)
    skill_ids = sorted(set(before) | set(after))
    titles = _titles(db, skill_ids, locale)
    learned = [
        {
            "skill_id": sid,
            "title": titles.get(sid, sid),
            "from_status": skill_status(before.get(sid, 0)),
            "to_status": skill_status(after.get(sid, 0)),
            "from_level": before.get(sid, 0),
            "to_level": after.get(sid, 0),
        }
        for sid in skill_ids
        if after.get(sid, 0) > before.get(sid, 0)
    ]
    activity = week_activity(db, student, now)
    practised = _titles(db, activity["skills_practised"], locale)
    return {
        "start": (now - WEEK).date().isoformat(),
        "end": now.date().isoformat(),
        "learned": learned,
        "practised": [practised[sid] for sid in activity["skills_practised"] if sid in practised],
        **{k: v for k, v in activity.items() if k != "skills_practised"},
    }


def guardian_view(
    db: Session, student: StudentRow, now: datetime, locale: str | None = None
) -> dict[str, Any]:
    """Progress by chapter and skill, plus the week. The guardian picks the language."""
    language = locale or student.home_language or "en"
    chapters = student_chapters(db, student, now)
    detailed = []
    from app.learner.chapters import find_chapter

    for row in chapters["chapters"]:
        entry: dict[str, Any] = dict(row)
        chapter = find_chapter(db, student, row["id"])
        if chapter is not None and row["live"]:
            skills = student_chapter_skills(db, student, chapter, now)["skills"]
            entry["skills"] = [
                {
                    "id": s["id"],
                    "title": s["title"],
                    "level": s["level"],
                    "status": s["status"],
                }
                for s in skills
            ]
        else:
            entry["skills"] = []
        detailed.append(entry)
    started = db.scalars(
        select(MasteryRow).where(MasteryRow.student_id == student.id, MasteryRow.ladder_level > 0)
    ).all()
    return {
        "student": {
            "id": str(student.id),
            "display_name": student.display_name,
            "grade": student.grade,
            "home_language": student.home_language,
        },
        "language": language,
        "chapters": detailed,
        "skills_started": len(started),
        "this_week": week_summary(db, student, now, language),
    }
