"""POST /explain: an in-depth, first-principles explanation of a typed question."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.auth.authz import FORBIDDEN
from app.auth.consent import has_scope, is_guest
from app.auth.deps import ActorDep, DbSession
from app.budget import llm_budget
from app.config import settings
from app.explain import proof
from app.explain.service import Gate, explain
from app.explain.service_chat import build_chat
from app.explain.service_lesson import (
    build_lesson,
    build_opening,
    build_rest,
    clean_client_opening,
)
from app.explain.story import build_story

router = APIRouter(prefix="/explain", tags=["explain"])

BUSY: dict[str, Any] = {"kind": "unavailable", "reason": "daily_limit"}


def _over_budget() -> bool:
    """True when today's model budget for the whole API is spent (LLM_DAILY_CAP)."""
    return not llm_budget.charge(settings.llm_daily_cap)


class ExplainIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(max_length=2000)
    language: str = "en"


class LessonIn(ExplainIn):
    # The opening the student has already seen, sent back so the rest can follow from it.
    opening: list[dict[str, Any]] | None = Field(default=None, max_length=4)


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=1000)


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(max_length=500)
    language: str = "en"
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


@router.post("")
def explain_question(body: ExplainIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    if not actor.is_student or actor.student_id is None:
        raise FORBIDDEN
    if _over_budget():
        return BUSY
    guest = is_guest(db, actor.student_id)
    # A guest holds no AI consent, so a guest is served only where the owner has switched that on.
    allowed = (
        settings.explain_guests_enabled
        if guest
        else has_scope(db, actor.student_id, "ai_processing")
    )
    gate = Gate(enabled=settings.explain_enabled, allowed=allowed)
    result = explain(body.prompt, body.language, gate, restricted=not guest)
    if result["kind"] == "explanation":
        # The web client calls /explain/story separately in parallel to get the animated story.
        # /explain only needs to provide a text fallback for the client.
        source = proof.video_source(result["title"], result["sections"])
        result["video"] = {"source": source, "proof": proof.sign(actor.student_id, source)}
    return result


def _lesson_gate(db: DbSession, actor: ActorDep) -> tuple[Gate, bool]:
    """The consent gate for any lesson call, and whether the caller is a guest."""
    if not actor.is_student or actor.student_id is None:
        raise FORBIDDEN
    guest = is_guest(db, actor.student_id)
    allowed = (
        settings.explain_guests_enabled
        if guest
        else has_scope(db, actor.student_id, "ai_processing")
    )
    return Gate(enabled=settings.explain_enabled, allowed=allowed), guest


@router.post("/lesson")
def explain_lesson(body: LessonIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """A student question compiled into structured interactive lesson blocks (JSON).

    Without `opening`: returns {kind:"lesson", level, objectives,
    blocks:[hook|predict|widget|explain|check|transfer|recap]}.
    With the `opening` the student has already seen (from /explain/lesson/opening): returns
    {kind:"rest", blocks:[...]}, the remaining blocks written to follow it.
    The same consent gate and safety screen as /explain apply.
    """
    gate, guest = _lesson_gate(db, actor)
    if _over_budget():
        return BUSY
    if body.opening is not None:
        opening = clean_client_opening(body.opening)
        if opening is None:
            return {"kind": "unavailable", "reason": "bad_opening"}
        return build_rest(body.prompt, body.language, opening, gate, restricted=not guest)
    return build_lesson(body.prompt, body.language, gate, restricted=not guest)


@router.post("/lesson/opening")
def explain_lesson_opening(body: ExplainIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Just the first two blocks of a lesson (a hook and a prediction), fast.

    Returns {kind:"opening", level, objectives, blocks:[hook, predict]}. The student can start at
    once; the rest comes from /explain/lesson with this opening sent back.
    """
    gate, guest = _lesson_gate(db, actor)
    if _over_budget():
        return BUSY
    return build_opening(body.prompt, body.language, gate, restricted=not guest)


@router.post("/chat")
def explain_chat(body: ChatIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Socratic tutor: one short reply to a student's follow-up question.

    The client sends the full conversation history with each request (stateless server).
    Returns {kind:"reply", text, language} or a gate/safety signal.
    """
    if not actor.is_student or actor.student_id is None:
        raise FORBIDDEN
    if _over_budget():
        return BUSY
    guest = is_guest(db, actor.student_id)
    allowed = (
        settings.explain_guests_enabled
        if guest
        else has_scope(db, actor.student_id, "ai_processing")
    )
    gate = Gate(enabled=settings.explain_enabled, allowed=allowed)
    history = [{"role": m.role, "content": m.content} for m in body.history]
    return build_chat(body.prompt, body.language, history, gate, restricted=not guest)


@router.post("/story")
def explain_story(body: ExplainIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """The question planned as an animated story, written scene by scene and signed."""
    if not actor.is_student or actor.student_id is None:
        raise FORBIDDEN
    if _over_budget():
        return BUSY
    guest = is_guest(db, actor.student_id)
    allowed = (
        settings.explain_guests_enabled
        if guest
        else has_scope(db, actor.student_id, "ai_processing")
    )
    gate = Gate(enabled=settings.explain_enabled, allowed=allowed)
    result = build_story(body.prompt, body.language, gate, restricted=not guest)
    if result["kind"] == "story":
        result["proof"] = proof.sign(actor.student_id, result["story"])
    return result
