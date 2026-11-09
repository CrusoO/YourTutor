"""POST /explain: an in-depth, first-principles explanation of a typed question."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.auth.authz import FORBIDDEN
from app.auth.consent import has_scope, is_guest
from app.auth.deps import ActorDep, DbSession
from app.budget import llm_budget
from app.config import settings
from app.conversation.voice import fallback_turn, register_for_grade
from app.db.models import StudentRow
from app.explain import proof
from app.explain.answer_guard import enforce_no_leak, load_active_item
from app.explain.chat_stream import final, stream_reply
from app.explain.service import Gate, explain
from app.explain.service_chat import build_chat, can_stream, prepare_chat
from app.explain.service_lesson import (
    build_lesson,
    build_opening,
    build_rest,
    clean_client_opening,
)
from app.explain.story import build_story
from app.safety import guarded_llm_route, is_paused
from app.safety_classifier import get_classifier

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
    # The student's own open practice session. When given, the reply never gives away the answer
    # to the item on screen before two hints and an attempt.
    session_id: uuid.UUID | None = None


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
    result = guarded_llm_route(
        db,
        actor.student_id,
        "explain",
        body.prompt,
        body.language,
        lambda: explain(body.prompt, body.language, gate, restricted=True),
    )
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
    gate, _ = _lesson_gate(db, actor)
    if _over_budget():
        return BUSY
    assert actor.student_id is not None  # _lesson_gate refuses anyone else
    if body.opening is not None:
        opening = clean_client_opening(body.opening)
        if opening is None:
            return {"kind": "unavailable", "reason": "bad_opening"}
        return guarded_llm_route(
            db,
            actor.student_id,
            "lesson",
            body.prompt,
            body.language,
            lambda: build_rest(body.prompt, body.language, opening, gate, restricted=True),
        )
    return guarded_llm_route(
        db,
        actor.student_id,
        "lesson",
        body.prompt,
        body.language,
        lambda: build_lesson(body.prompt, body.language, gate, restricted=True),
    )


@router.post("/lesson/opening")
def explain_lesson_opening(body: ExplainIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Just the first two blocks of a lesson (a hook and a prediction), fast.

    Returns {kind:"opening", level, objectives, blocks:[hook, predict]}. The student can start at
    once; the rest comes from /explain/lesson with this opening sent back.
    """
    gate, _ = _lesson_gate(db, actor)
    if _over_budget():
        return BUSY
    assert actor.student_id is not None  # _lesson_gate refuses anyone else
    return guarded_llm_route(
        db,
        actor.student_id,
        "lesson",
        body.prompt,
        body.language,
        lambda: build_opening(body.prompt, body.language, gate, restricted=True),
    )


class _ChatTurn:
    """What a chat request needs, worked out once so the plain and streamed routes agree."""

    def __init__(self, body: ChatIn, db: DbSession, actor: ActorDep) -> None:
        assert actor.student_id is not None
        self.student_id = actor.student_id
        guest = is_guest(db, actor.student_id)
        allowed = (
            settings.explain_guests_enabled
            if guest
            else has_scope(db, actor.student_id, "ai_processing")
        )
        self.gate = Gate(enabled=settings.explain_enabled, allowed=allowed)
        self.history = [{"role": m.role, "content": m.content} for m in body.history]
        student = db.get(StudentRow, actor.student_id)
        self.register = register_for_grade(student.grade if student else None)
        self.active = load_active_item(db, actor.student_id, body.session_id)
        self.body = body

    def with_fallback(self, result: dict[str, Any]) -> dict[str, Any]:
        """Never a bare error: an honest authored line and the next choices. `kind` and `reason`
        are unchanged, so a client that ignores `fallback` behaves as before."""
        if result.get("kind") == "unavailable":
            turns = sum(1 for m in self.history if m["role"] == "assistant")
            result["fallback"] = fallback_turn(
                str(result.get("reason", "")), self.register, self.body.language, turns
            )
        return result


def _run_chat(turn: _ChatTurn, db: DbSession) -> dict[str, Any]:
    body = turn.body
    result = guarded_llm_route(
        db,
        turn.student_id,
        "chat",
        body.prompt,
        body.language,
        lambda: enforce_no_leak(
            lambda rule: build_chat(
                body.prompt,
                body.language,
                turn.history,
                turn.gate,
                restricted=True,
                register=turn.register,
                extra_rule=rule,
            ),
            turn.active,
            body.language,
        ),
    )
    return turn.with_fallback(result)


@router.post("/chat")
def explain_chat(body: ChatIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Socratic tutor: one short reply to a student's follow-up question.

    The client sends the full conversation history with each request (stateless server).
    Returns {kind:"reply", text, language} or a gate/safety signal. When no reply can be given,
    {kind:"unavailable", reason, fallback:{reason, text, offers}} carries an authored line.
    """
    if not actor.is_student or actor.student_id is None:
        raise FORBIDDEN
    if _over_budget():
        return BUSY
    return _run_chat(_ChatTurn(body, db, actor), db)


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _sse_response(events: Iterator[str]) -> StreamingResponse:
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _once(result: dict[str, Any]) -> StreamingResponse:
    return _sse_response(iter([_sse(final(result))]))


@router.post("/chat/stream")
def explain_chat_stream(body: ChatIn, db: DbSession, actor: ActorDep) -> StreamingResponse:
    """The same reply as POST /explain/chat, sent as server-sent events.

    Each event is a JSON line `data: {...}`: `{"type":"delta","text":"..."}` carries one checked
    sentence; the last event is `{"type":"final","result":{...}}`, the same body /explain/chat
    returns. Keep the final result: it replaces what was shown if the guard had to step in.
    Anything decided before a model is called (distress, refusal, pause, no consent) arrives as a
    lone `final`. The same checks apply as on the plain route.
    """
    if not actor.is_student or actor.student_id is None:
        raise FORBIDDEN
    if _over_budget():
        return _once(BUSY)
    turn = _ChatTurn(body, db, actor)
    # Streaming shows text before the whole reply exists, so it is used only when no check needs
    # the whole reply (the output classifier) and the chat is not paused.
    if get_classifier() is not None or is_paused(db, turn.student_id):
        return _once(_run_chat(turn, db))
    prepared = prepare_chat(
        body.prompt,
        body.language,
        turn.history,
        turn.gate,
        restricted=True,
        register=turn.register,
    )
    if isinstance(prepared, dict):  # decided before any model call: the shared distress flow
        early = guarded_llm_route(
            db, turn.student_id, "chat", body.prompt, body.language, lambda: prepared
        )
        return _once(turn.with_fallback(early))
    if not can_stream(prepared.model):
        return _once(_run_chat(turn, db))

    def events() -> Iterator[str]:
        for event in stream_reply(prepared, turn.active):
            if event["type"] == "final":
                event = final(turn.with_fallback(event["result"]))
            yield _sse(event)

    return _sse_response(events())


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
    result = guarded_llm_route(
        db,
        actor.student_id,
        "story",
        body.prompt,
        body.language,
        lambda: build_story(body.prompt, body.language, gate, restricted=True),
    )
    if result["kind"] == "story":
        result["proof"] = proof.sign(actor.student_id, result["story"])
    return result
