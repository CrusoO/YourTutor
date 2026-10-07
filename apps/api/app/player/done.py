"""Done screen summary attached to `end_session` actions (S1b)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.db.models import (
    EventRow,
    ItemRow,
    MasteryRow,
    OverlayRow,
    SessionRow,
    SkillRow,
    StudentRow,
)
from app.learner.chapters import (
    _mastery_levels,
    chapter_for_overlay,
    skill_path,
    student_chapters,
)
from app.learner.summary import done_summary
from app.registries.locale_resolve import pick_localized_field


def levels_snapshot(session: Session, student_id: uuid.UUID) -> dict[str, int]:
    return {
        row.skill_id: row.ladder_level
        for row in session.scalars(select(MasteryRow).where(MasteryRow.student_id == student_id))
    }


def _touched_skills(session: Session, row: SessionRow) -> list[str]:
    ids = [
        item_id
        for item_id in session.scalars(
            select(EventRow.item_id).where(
                EventRow.session_id == row.id, EventRow.event_type == "answer"
            )
        )
        if item_id
    ]
    if not ids:
        return []
    return [
        skill
        for skill in session.scalars(select(ItemRow.primary_skill).where(ItemRow.id.in_(ids)))
        if skill
    ]


def _overlay_id_for(session: Session, skill_ids: list[str]) -> str | None:
    for overlay in session.scalars(select(OverlayRow)):
        if list(overlay.skill_ids or []) == skill_ids:
            return overlay.id
    return None


def attach_summary(
    session: Session, student: StudentRow, row: SessionRow, payload: dict[str, Any]
) -> None:
    """Add `extras.summary` to an `end_session` payload. Nothing else changes."""
    if payload.get("type") != "end_session":
        return
    from app.player.runtime import _overlay_skills, remaining_minutes

    now = now_utc()
    skill_ids = list(_overlay_skills(session, student, row.plan))
    locale = student.home_language or "en"
    titles = {
        skill.id: pick_localized_field(dict(skill.title or {}), locale)
        for skill in session.scalars(select(SkillRow).where(SkillRow.id.in_(skill_ids)))
    }
    path = skill_path(_mastery_levels(session, student.id, skill_ids, now))
    for entry in path:
        entry["title"] = titles.get(entry["id"]) or entry["id"]
    summary = done_summary(
        path,
        start_levels=dict((row.plan or {}).get("levels_at_start") or {}),
        touched=_touched_skills(session, row),
        remaining=remaining_minutes(session, student),
    )
    overview = student_chapters(session, student, now)
    overlay_id = (row.plan or {}).get("overlay_id") or _overlay_id_for(session, skill_ids)
    chapter = chapter_for_overlay(session, student, overlay_id)
    current = next((c for c in overview["chapters"] if chapter and c["id"] == chapter.id), None)
    summary["chapter"] = (
        {"id": current["id"], "title": current["title"], "status": current["status"]}
        if current
        else None
    )
    summary["recommended_chapter"] = next(
        (c["id"] for c in overview["chapters"] if c["recommended"]), None
    )
    extras = dict(payload.get("extras") or {})
    extras["summary"] = summary
    payload["extras"] = extras
