"""Teacher alerts that come from a pattern in the event log (not from one session's policy)."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EventRow, ItemRow, SessionRow

REPEAT_LIMIT = 3  # the same misconception this many times on one skill
REPEAT_WINDOW = timedelta(days=14)


def repeated_misconceptions(
    db: Session, student_id: uuid.UUID, now: datetime
) -> list[dict[str, str]]:
    """Skills where one named misconception was diagnosed at least three times in two weeks."""
    rows = db.execute(
        select(EventRow.payload, EventRow.item_id)
        .join(SessionRow, EventRow.session_id == SessionRow.id)
        .where(
            SessionRow.student_id == student_id,
            EventRow.event_type == "answer",
            EventRow.created_at >= now - REPEAT_WINDOW,
        )
    ).all()
    hits: list[tuple[str | None, str]] = []
    for payload, item_id in rows:
        body = payload if isinstance(payload, dict) else {}
        diagnosis = body.get("diagnosis")
        if (
            isinstance(diagnosis, dict)
            and diagnosis.get("class") == "misconception"
            and diagnosis.get("detail")
        ):
            hits.append((item_id if isinstance(item_id, str) else None, str(diagnosis["detail"])))
    if not hits:
        return []
    item_ids = {item_id for item_id, _ in hits if item_id}
    skill_of = {
        row.id: row.primary_skill
        for row in db.scalars(select(ItemRow).where(ItemRow.id.in_(item_ids)))
    }
    counts: Counter[tuple[str, str]] = Counter()
    for item_id, detail in hits:
        skill = skill_of.get(item_id or "")
        if skill:
            counts[(skill, detail)] += 1
    found = sorted({skill for (skill, _), n in counts.items() if n >= REPEAT_LIMIT})
    return [{"skill_id": skill, "type": "repeated_misconception"} for skill in found]
