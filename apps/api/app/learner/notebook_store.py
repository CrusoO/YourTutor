"""Mistake notebook storage: write a miss, read what is due, save a return.

Ids and times only. The learner's typed answer is never passed in, stored or logged (ADR 0005); the
only log line holds counts. Scheduling is in `app.learner.notebook` (pure).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.consent import has_scope, is_guest
from app.auth.security import as_utc
from app.config import settings
from app.db.models import EventRow, ItemRow, NotebookEntryRow, SessionRow, SkillRow
from app.learner import notebook as nb
from app.orchestrator.types import SessionState

SCOPE = "tutoring"


def _en(blob: Any) -> str:
    if isinstance(blob, dict):
        value = blob.get("en")
        return value if isinstance(value, str) else ""
    return blob if isinstance(blob, str) else ""


def may_use(session: Session, student_id: uuid.UUID) -> bool:
    """A signed-in (non-guest) learner who holds the tutoring consent."""
    return not is_guest(session, student_id) and has_scope(session, student_id, SCOPE)


def _state_of(row: NotebookEntryRow) -> nb.EntryState:
    return nb.EntryState(
        row.stage, row.state, as_utc(row.anchor_at), as_utc(row.due_at) if row.due_at else None
    )


def record_miss(
    session: Session,
    student_id: uuid.UUID,
    event_type: str,
    state: SessionState,
    misconception_id: str | None,
    item_id: str | None,
    now: datetime,
) -> bool:
    """Make an entry when the learner's FIRST answer to this item was wrong. Says whether it did."""
    if not settings.mistake_notebook_enabled:
        return False
    if event_type != "answer" or state.last_correct is not False or not item_id:
        return False
    if session.scalar(
        select(NotebookEntryRow.id).where(
            NotebookEntryRow.student_id == student_id, NotebookEntryRow.item_id == item_id
        )
    ):
        return False
    earlier = session.scalar(
        select(EventRow.id)
        .join(SessionRow, SessionRow.id == EventRow.session_id)
        .where(
            SessionRow.student_id == student_id,
            EventRow.item_id == item_id,
            EventRow.event_type == "answer",
        )
        .limit(1)
    )
    if earlier is not None:
        return False
    item = session.get(ItemRow, item_id)
    if item is None or not may_use(session, student_id):
        return False
    diagnosis = state.last_diagnosis
    kind = misconception_id if diagnosis and diagnosis.get("class") == "misconception" else None
    cfg = nb.load_config()
    first = nb.new_entry(now, cfg)
    session.add(
        NotebookEntryRow(
            id=uuid.uuid4(),
            student_id=student_id,
            item_id=item_id,
            skill_id=item.primary_skill,
            misconception_id=kind,
            stage=first.stage,
            state=first.state,
            anchor_at=first.anchor_at,
            due_at=first.due_at,
            created_at=now,
            updated_at=now,
        )
    )
    return True


def _new_form(session: Session, row: NotebookEntryRow) -> tuple[str, bool]:
    """The item to retest with: a different servable item of the same skill, else the same one."""
    from app.player.runtime import load_catalog

    original = session.get(ItemRow, row.item_id)
    if original is None:
        return row.item_id, True
    catalog = load_catalog(session, allow_draft=settings.allow_draft_content)
    cands = [
        (c.id, c.stem, c.difficulty)
        for c in catalog
        if row.skill_id in c.skill_ids and c.pool == "practice"
    ]
    pick = nb.pick_new_form(original.id, _en(original.stem), cands, original.difficulty)
    return (pick, False) if pick else (row.item_id, True)


def due_entries(session: Session, student_id: uuid.UUID, now: datetime) -> list[dict[str, Any]]:
    cfg = nb.load_config()
    rows = session.scalars(
        select(NotebookEntryRow)
        .where(
            NotebookEntryRow.student_id == student_id,
            NotebookEntryRow.state == nb.OPEN,
            NotebookEntryRow.due_at <= now,
        )
        .order_by(NotebookEntryRow.due_at, NotebookEntryRow.id)
        .limit(cfg.due_limit)
    ).all()
    out: list[dict[str, Any]] = []
    for row in rows:
        skill = session.get(SkillRow, row.skill_id)
        item_id, same = _new_form(session, row)
        out.append(
            {
                "entry_id": str(row.id),
                "skill_id": row.skill_id,
                "skill_title": _en(skill.title) if skill else "",
                "misconception_id": row.misconception_id,
                "return_number": row.stage + 1,
                "return_after_days": cfg.return_days[row.stage],
                "item_id": item_id,
                "same_item": same,
            }
        )
    return out


class NotFound(Exception):
    pass


class NotDue(Exception):
    pass


def record_result(
    session: Session, student_id: uuid.UUID, entry_id: uuid.UUID, outcome: str, now: datetime
) -> dict[str, Any]:
    row = session.get(NotebookEntryRow, entry_id)
    if row is None or row.student_id != student_id:
        raise NotFound
    if not nb.is_due(_state_of(row), now):
        raise NotDue
    after = nb.apply_return(_state_of(row), outcome, now, nb.load_config())
    row.stage, row.state = after.stage, after.state
    row.anchor_at, row.due_at, row.updated_at = after.anchor_at, after.due_at, now
    return {
        "entry_id": str(row.id),
        "state": row.state,
        "return_number": row.stage + 1 if row.state == nb.OPEN else None,
        "due_at": row.due_at.isoformat() if row.due_at else None,
    }


def summary(session: Session, student_id: uuid.UUID, now: datetime) -> dict[str, Any]:
    cfg = nb.load_config()
    rows = session.scalars(
        select(NotebookEntryRow).where(NotebookEntryRow.student_id == student_id)
    ).all()
    entries = [_state_of(r) for r in rows]
    return {
        "total": len(rows),
        "due_now": sum(1 for e in entries if nb.is_due(e, now)),
        "waiting_for_return": {
            k: v for k, v in nb.stage_counts(entries, cfg).items() if k != "settled"
        },
        "settled": nb.stage_counts(entries, cfg)["settled"],
        "return_days": list(cfg.return_days),
    }
