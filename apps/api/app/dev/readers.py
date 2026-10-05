"""Read-only views of student state for the dev tooling."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MasteryRow, ReviewCardRow, StudentRow


def ladder_levels(db: Session, student: StudentRow) -> tuple[dict[str, int], dict[str, int]]:
    """(skill -> ladder level, skill -> attempts) as the engine stored them."""
    rows = db.scalars(select(MasteryRow).where(MasteryRow.student_id == student.id)).all()
    return {r.skill_id: r.ladder_level for r in rows}, {r.skill_id: r.attempts for r in rows}


def card_due(db: Session, student: StudentRow, skill_id: str) -> datetime | None:
    card = db.get(ReviewCardRow, (student.id, skill_id))
    if card is None:
        return None
    return card.due_at if card.due_at.tzinfo else card.due_at.replace(tzinfo=UTC)
