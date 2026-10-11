"""What a teacher sees about a class: only students whose guardian shared with the teacher.

Every function takes the visible student ids from `teacher_visible_student_ids` (or all members for
an admin), so a student without `teacher_share` never appears, not even as a count. Students are
listed alphabetically; nothing is ranked or averaged.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import as_utc
from app.db.models import (
    LlmCallRow,
    MasteryRow,
    SessionRow,
    SkillRow,
    StudentRow,
    TeacherAlertRow,
)
from app.player.runtime import _overlay_skills
from app.registries.locale_resolve import pick_localized_field

STUCK_PHASES = frozenset({"stuck", "stuck_step", "break_choice", "reveal"})
STUCK_WINDOW = timedelta(minutes=10)
ALERT_LABELS = {
    "wheel_spinning": "Keeps missing this skill",
    "repeated_misconception": "Same mistake again and again",
    "distress": "Said something worrying: please check in",
}
LEVELS = list(range(0, 8))


def _students(db: Session, ids: set[uuid.UUID]) -> list[StudentRow]:
    rows = db.scalars(select(StudentRow).where(StudentRow.id.in_(ids))).all() if ids else []
    return sorted(rows, key=lambda s: (s.display_name.casefold(), str(s.id)))


def _titles(db: Session, skill_ids: list[str]) -> dict[str, str]:
    rows = db.scalars(select(SkillRow).where(SkillRow.id.in_(skill_ids))).all()
    return {row.id: pick_localized_field(dict(row.title or {}), "en") or row.id for row in rows}


def heatmap(db: Session, class_id: uuid.UUID, visible: set[uuid.UUID]) -> dict[str, Any]:
    """Ladder level (0 to 7) per student and skill, plus how many students sit at each level."""
    students = _students(db, visible)
    skill_ids: list[str] = []
    for student in students:
        for sid in _overlay_skills(db, student):
            if sid not in skill_ids:
                skill_ids.append(sid)
    levels: dict[tuple[uuid.UUID, str], int] = {}
    if students and skill_ids:
        for row in db.scalars(
            select(MasteryRow).where(
                MasteryRow.student_id.in_(visible), MasteryRow.skill_id.in_(skill_ids)
            )
        ):
            levels[(row.student_id, row.skill_id)] = row.ladder_level
    counts = {sid: {level: 0 for level in LEVELS} for sid in skill_ids}
    rows = []
    for student in students:
        cells = {sid: levels.get((student.id, sid), 0) for sid in skill_ids}
        for sid, level in cells.items():
            counts[sid][level] += 1
        rows.append({"id": str(student.id), "display_name": student.display_name, "levels": cells})
    titles = _titles(db, skill_ids)
    return {
        "kind": "heatmap",
        "class_id": str(class_id),
        "skills": [{"id": sid, "title": titles.get(sid, sid)} for sid in skill_ids],
        "levels": LEVELS,
        "students": rows,
        "counts": {sid: {str(k): v for k, v in c.items()} for sid, c in counts.items()},
    }


def stuck_now(
    db: Session, class_id: uuid.UUID, visible: set[uuid.UUID], now: datetime
) -> dict[str, Any]:
    """Students in an open session who are at the help picker, the break offer, a reveal, or two
    hints deep, and active in the last ten minutes."""
    sessions = (
        db.scalars(
            select(SessionRow).where(
                SessionRow.student_id.in_(visible),
                SessionRow.ended_at.is_(None),
                SessionRow.type == "practice",
            )
        ).all()
        if visible
        else []
    )
    names = {s.id: s.display_name for s in _students(db, visible)}
    out: list[dict[str, Any]] = []
    for row in sessions:
        plan = row.plan or {}
        recent = now - as_utc(row.last_active_at) <= STUCK_WINDOW
        stuck = plan.get("phase") in STUCK_PHASES or int(plan.get("hint_level_shown") or 0) >= 2
        if recent and stuck:
            out.append(
                {
                    "student_id": str(row.student_id),
                    "display_name": names[row.student_id],
                    "skill_id": plan.get("current_skill") or "",
                    "phase": plan.get("phase"),
                    "since": as_utc(row.last_active_at).isoformat(),
                }
            )
    titles = _titles(db, sorted({e["skill_id"] for e in out if e["skill_id"]}))
    for entry in out:
        entry["skill_title"] = titles.get(entry["skill_id"], entry["skill_id"])
    out.sort(key=lambda e: (str(e["display_name"]).casefold(), e["student_id"]))
    return {"kind": "stuck", "class_id": str(class_id), "students": out}


def alerts(db: Session, class_id: uuid.UUID, visible: set[uuid.UUID]) -> dict[str, Any]:
    """Open alerts. An alert closes by itself when the skill reaches level 4."""
    rows = (
        db.scalars(
            select(TeacherAlertRow)
            .where(TeacherAlertRow.student_id.in_(visible), TeacherAlertRow.resolved_at.is_(None))
            .order_by(TeacherAlertRow.created_at)
        ).all()
        if visible
        else []
    )
    names = {s.id: s.display_name for s in _students(db, visible)}
    titles = _titles(db, sorted({r.skill_id for r in rows}))
    items = [
        {
            "id": str(r.id),
            "student_id": str(r.student_id),
            "display_name": names[r.student_id],
            "skill_id": r.skill_id,
            "skill_title": titles.get(r.skill_id, r.skill_id),
            "type": r.type,
            "label": ALERT_LABELS.get(r.type, r.type),
            "since": as_utc(r.created_at).isoformat(),
        }
        for r in rows
    ]
    items.sort(key=lambda a: (a["display_name"].casefold(), a["since"]))
    return {"kind": "alerts", "class_id": str(class_id), "alerts": items}


def review_items(db: Session, visible: set[uuid.UUID] | None) -> list[dict[str, Any]]:
    """AI replies sampled for a human to read. `visible` None means every student (admin)."""
    query = (
        select(LlmCallRow, SessionRow)
        .join(SessionRow, LlmCallRow.session_id == SessionRow.id)
        .where(LlmCallRow.review_status == "pending", LlmCallRow.output_text.is_not(None))
        .order_by(LlmCallRow.created_at)
    )
    out = []
    names: dict[uuid.UUID, str] = {}
    for call, session in db.execute(query).all():
        if visible is not None and session.student_id not in visible:
            continue
        if session.student_id not in names:
            student = db.get(StudentRow, session.student_id)
            names[session.student_id] = student.display_name if student else ""
        out.append(
            {
                "id": str(call.id),
                "student_id": str(session.student_id),
                "display_name": names[session.student_id],
                "purpose": call.purpose,
                "text": call.output_text,
                "created_at": as_utc(call.created_at).isoformat(),
            }
        )
    return out


def decide_review(
    db: Session, call_id: uuid.UUID, decision: str, visible: set[uuid.UUID] | None
) -> None:
    if decision not in {"ok", "bad"}:
        raise HTTPException(status_code=422, detail="decision must be ok or bad")
    call = db.get(LlmCallRow, call_id)
    session = db.get(SessionRow, call.session_id) if call and call.session_id else None
    if call is None or session is None or call.review_status != "pending":
        raise HTTPException(status_code=404, detail="not found")
    if visible is not None and session.student_id not in visible:
        raise HTTPException(status_code=404, detail="not found")  # not visible: same as missing
    call.review_status = decision
