"""POST /actions/route: does this typed message ask Brownie to do something in the app?"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.actions.registry import Tier
from app.actions.service import route
from app.auth.authz import FORBIDDEN
from app.auth.consent import is_guest
from app.auth.deps import ActorDep, DbSession

router = APIRouter(prefix="/actions", tags=["actions"])

LANGUAGES = ("en", "hi")


class RouteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utterance: str = Field(max_length=500)
    language: str = "en"


@router.post("/route")
def route_action(body: RouteIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """No model call and nothing stored: a pure lookup, so it is free and cannot hit a quota."""
    if not actor.is_student or actor.student_id is None:
        raise FORBIDDEN
    tier = Tier.GUEST if is_guest(db, actor.student_id) else Tier.STUDENT
    language = body.language if body.language in LANGUAGES else "en"
    return route(body.utterance, language, tier)
