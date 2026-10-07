"""Chapter map and skill path for the student app (ARCHITECTURE §5, §11.3).

Status comes from the mastery ladder only (`app.learner.status`). Nothing here blocks a student:
"unlocked" is a visual hint, and a chapter is refused only when it is coming soon.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import (
    ChapterRow,
    MasteryRow,
    OverlayRow,
    ReviewCardRow,
    SkillRow,
    StudentRow,
)
from app.learner.status import (
    CAN_DO_IT,
    NOT_STARTED,
    SOLID,
    chapter_status,
    review_overdue,
    skill_status,
)
from app.registries.locale_resolve import pick_localized_field

COMING_SOON = "coming_soon"
CAN_DO_IT_LEVEL = 4


@dataclass(frozen=True)
class ChapterSummary:
    id: str
    title: str
    live: bool
    status: str
    skills_total: int = 0
    skills_can_do_it: int = 0
    overlay_id: str = ""


def recommend_chapter(rows: Sequence[ChapterSummary]) -> str | None:
    """Exactly one chapter, or None when nothing can be started.

    The first live chapter that is not Solid; when every live chapter is Solid, the first live one
    (a revisit). A review-due chapter counts as not Solid.
    """
    live = [row for row in rows if row.live]
    if not live:
        return None
    for row in live:
        if row.status != SOLID:
            return row.id
    return live[0].id


def skill_path(skills: Sequence[tuple[str, int, bool]]) -> list[dict[str, Any]]:
    """Per-skill status for `(skill_id, ladder_level, review_overdue)` in path order.

    A skill is *unlocked* (visual only) when it is first or the previous skill is Can do it or
    better. `current` marks the first skill that is not yet Can do it.
    """
    out: list[dict[str, Any]] = []
    previous_done = True
    found_current = False
    for skill_id, level, overdue in skills:
        status = skill_status(level, review_overdue=overdue)
        done = level >= CAN_DO_IT_LEVEL
        current = not done and not found_current
        found_current = found_current or current
        out.append(
            {
                "id": skill_id,
                "level": level,
                "status": status,
                "unlocked": previous_done,
                "current": current,
            }
        )
        previous_done = done
    return out


def _is_live(overlay: OverlayRow | None) -> bool:
    if overlay is None or not (overlay.skill_ids or []):
        return False
    return bool(overlay.live) or settings.allow_draft_content


def _mastery_levels(
    session: Session, student_id: uuid.UUID, skill_ids: Sequence[str], now: datetime
) -> list[tuple[str, int, bool]]:
    if not skill_ids:
        return []
    levels = {
        row.skill_id: row.ladder_level
        for row in session.scalars(
            select(MasteryRow).where(
                MasteryRow.student_id == student_id, MasteryRow.skill_id.in_(list(skill_ids))
            )
        )
    }
    due = {
        row.skill_id: row.due_at
        for row in session.scalars(
            select(ReviewCardRow).where(
                ReviewCardRow.student_id == student_id,
                ReviewCardRow.skill_id.in_(list(skill_ids)),
            )
        )
    }
    return [
        (sid, levels.get(sid, 0), review_overdue(due.get(sid), now) if sid in levels else False)
        for sid in skill_ids
    ]


def _chapter_rows(session: Session, student: StudentRow) -> list[ChapterRow]:
    return list(
        session.scalars(
            select(ChapterRow)
            .where(ChapterRow.book_id == student.book_id)
            .order_by(ChapterRow.position, ChapterRow.id)
        )
    )


def _summary(
    session: Session, student: StudentRow, chapter: ChapterRow, locale: str, now: datetime
) -> ChapterSummary:
    overlay = session.get(OverlayRow, chapter.overlay_id)
    title = pick_localized_field(dict(chapter.titles or {}), locale) or chapter.chapter_key
    live = _is_live(overlay)
    skills = list(overlay.skill_ids or []) if overlay else []
    rows = _mastery_levels(session, student.id, skills, now)
    statuses = [skill_status(level, review_overdue=overdue) for _, level, overdue in rows]
    return ChapterSummary(
        id=chapter.id,
        title=title,
        live=live,
        status=chapter_status(statuses) if live else COMING_SOON,
        skills_total=len(skills),
        skills_can_do_it=sum(1 for _, level, _ in rows if level >= CAN_DO_IT_LEVEL),
        overlay_id=chapter.overlay_id,
    )


def student_chapters(session: Session, student: StudentRow, now: datetime) -> dict[str, Any]:
    locale = student.home_language or "en"
    summaries = [
        _summary(session, student, ch, locale, now) for ch in _chapter_rows(session, student)
    ]
    recommended = recommend_chapter(summaries)
    live_skills: list[str] = []
    for summary in summaries:
        overlay = session.get(OverlayRow, summary.overlay_id) if summary.live else None
        live_skills.extend(overlay.skill_ids or [] if overlay else [])
    subjects = {
        row.subject for row in session.scalars(select(SkillRow).where(SkillRow.id.in_(live_skills)))
    }
    return {
        "student_id": str(student.id),
        "subject": sorted(subjects)[0] if subjects else "math",
        "chapters": [
            {
                "id": s.id,
                "title": s.title,
                "live": s.live,
                "status": s.status,
                "recommended": s.id == recommended,
                "skills_total": s.skills_total,
                "skills_can_do_it": s.skills_can_do_it,
            }
            for s in summaries
        ],
    }


def find_chapter(session: Session, student: StudentRow, chapter_id: str) -> ChapterRow | None:
    row = session.get(ChapterRow, chapter_id)
    if row is None or row.book_id != student.book_id:
        return None
    return row


def chapter_is_live(session: Session, chapter: ChapterRow) -> bool:
    return _is_live(session.get(OverlayRow, chapter.overlay_id))


def student_chapter_skills(
    session: Session, student: StudentRow, chapter: ChapterRow, now: datetime
) -> dict[str, Any]:
    from app.lessons.loader import lesson_for_skill, servable

    locale = student.home_language or "en"
    summary = _summary(session, student, chapter, locale, now)
    overlay = session.get(OverlayRow, chapter.overlay_id)
    skill_ids = list(overlay.skill_ids or []) if overlay else []
    titles = {
        row.id: pick_localized_field(dict(row.title or {}), locale)
        for row in session.scalars(select(SkillRow).where(SkillRow.id.in_(skill_ids)))
    }
    path = skill_path(_mastery_levels(session, student.id, skill_ids, now))
    for row in path:
        row["title"] = titles.get(row["id"]) or row["id"]
        lesson = lesson_for_skill(row["id"])
        row["has_lesson"] = bool(lesson and servable(lesson))
    return {
        "chapter": {
            "id": summary.id,
            "title": summary.title,
            "live": summary.live,
            "status": summary.status,
            "skills_total": summary.skills_total,
            "skills_can_do_it": summary.skills_can_do_it,
        },
        "skills": path,
    }


__all__ = [
    "CAN_DO_IT",
    "COMING_SOON",
    "NOT_STARTED",
    "ChapterSummary",
    "chapter_is_live",
    "find_chapter",
    "recommend_chapter",
    "skill_path",
    "student_chapter_skills",
    "student_chapters",
]
