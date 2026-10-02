from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.auth.authz import require
from app.auth.deps import ActorDep, DbSession
from app.db.models import EventRow, SessionRow
from app.orchestrator.replay import pseudonymous_session_id

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/sessions/{session_id}/replay")
def replay_session(session_id: uuid.UUID, actor: ActorDep, db: DbSession) -> dict:
    require(actor.is_admin)
    row = db.get(SessionRow, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="session not found")
    events = (
        db.query(EventRow)
        .filter(EventRow.session_id == session_id)
        .order_by(EventRow.created_at)
        .all()
    )
    return {
        "session_id": pseudonymous_session_id(session_id),
        "student_id": f"stu_{row.student_id.hex[:8]}",
        "type": row.type,
        "ended_reason": row.ended_reason,
        "events": [
            {
                "event_type": ev.event_type,
                "item_id": ev.item_id,
                "rule_id": ev.rule_id,
                "state_before": ev.state_before,
                "state_after": ev.state_after,
                "correct": ev.correct,
            }
            for ev in events
        ],
    }
