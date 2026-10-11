"""Admin-only pilot metrics."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.auth.authz import require
from app.auth.deps import ActorDep, DbSession
from app.metrics.pilot import pilot_metrics

router = APIRouter()


@router.get("/admin/metrics/pilot")
def pilot(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    require(actor.is_admin)
    return pilot_metrics(db)
