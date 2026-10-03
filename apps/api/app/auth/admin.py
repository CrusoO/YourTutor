from __future__ import annotations

import uuid

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.auth import service
from app.auth.authz import require
from app.auth.deps import ActorDep, DbSession
from app.checkpoint.study import REFERRER_POLICY, paper_entry_html
from app.db.models import EventRow, SessionRow
from app.orchestrator.replay import pseudonymous_session_id

router = APIRouter(prefix="/admin", tags=["admin"])


class PaperIn(BaseModel):
    pseudonym: str
    form: str
    occasion: str = "pretest"
    answers: list[dict[str, Any]]
    entry_pass: int = 1
    checkpoint_id: str = "CP.LIN1.CLASS9"


@router.get("/paper-entry")
def paper_entry_screen(actor: ActorDep) -> HTMLResponse:
    require(actor.is_admin)
    return HTMLResponse(paper_entry_html(), headers={"Referrer-Policy": REFERRER_POLICY})


@router.post("/checkpoints/paper")
def paper_entry(body: PaperIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.enter_paper_checkpoint(
        db,
        actor,
        pseudonym=body.pseudonym,
        form=body.form,
        occasion=body.occasion,
        answers=body.answers,
        entry_pass=body.entry_pass,
        checkpoint_id=body.checkpoint_id,
    )


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
                "item": _replay_item(db, ev.item_id),
                "rule_id": ev.rule_id,
                "state_before": ev.state_before,
                "state_after": ev.state_after,
                "correct": ev.correct,
            }
            for ev in events
        ],
    }


def _replay_item(db: DbSession, item_id: str | None) -> dict[str, str] | None:
    if not item_id:
        return None
    from app.db.models import ItemRow

    row = db.get(ItemRow, item_id)
    if row is None:
        return None
    stem = row.stem if isinstance(row.stem, dict) else {}
    return {"id": row.id, "status": row.status, "stem_en": stem.get("en") or ""}
