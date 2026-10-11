"""Offline endpoints: download a pack, sync a session played without a network."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.auth.authz import require, student_or_404
from app.auth.deps import ActorDep, DbSession
from app.offline.pack import build_pack
from app.offline.sync import SyncIn, sync_offline_session

router = APIRouter()


@router.get("/students/me/pack")
def get_pack(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    require(actor.is_student and actor.student_id is not None)
    student = student_or_404(db, actor.student_id)  # type: ignore[arg-type]
    return build_pack(db, student)


@router.post("/sync/events")
def sync_events(body: SyncIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return sync_offline_session(db, actor, body)
