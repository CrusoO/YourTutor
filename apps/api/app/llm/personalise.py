"""Glue between a session and the LLM gateway.

The policy stays pure. After it decides an action, `personalise_action` may rephrase that action's
text once; the result is stored on the action, so a re-render never calls the model again. Three
things are personalised: plain ladder hints (levels 1 and 2), the explain-back reply, and the
one-sentence encouragement. Everything else is authored text.

BKT and FSRS are never touched here. Skipped calls (no consent, no key, assessment) are not logged.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import GlossaryTermRow, ItemRow
from app.llm.gateway import Gate, Gateway, LlmResult, record_call
from app.llm.prompt import PromptContext
from app.llm.purposes import Purpose
from app.orchestrator.types import Action, SessionState
from app.registries.grade_bands import band_for_grade

PERSONALISED_HINT_LEVELS = (1, 2)
AUTHORED_HINT_KINDS = frozenset({"restate", "step"})  # authored per item, never rephrased
GLOSSARY_LIMIT = 30

_gateway: Gateway | None = None


def get_gateway() -> Gateway:
    global _gateway
    if _gateway is None:
        _gateway = Gateway()
    return _gateway


def set_gateway(gateway: Gateway | None) -> None:
    """Tests and the evals swap in a gateway with a fake provider; None restores the default."""
    global _gateway
    _gateway = gateway


def _glossary(db: Session, language: str) -> dict[str, str]:
    if language == "en":
        return {}
    rows = db.scalars(
        select(GlossaryTermRow).where(GlossaryTermRow.language == language).limit(GLOSSARY_LIMIT)
    ).all()
    return {row.term: row.translation for row in rows}


def _stem(db: Session, item_id: str | None) -> str:
    row = db.get(ItemRow, item_id) if item_id else None
    return str((row.stem or {}).get("en") or "") if row else ""


def _run(
    db: Session,
    state: SessionState,
    ctx: PromptContext,
    fallback: str,
    session_id: uuid.UUID | None,
) -> LlmResult:
    gate = Gate(state.session_type, state.has_ai_processing, bool(settings.llm_api_key))
    result = get_gateway().generate(ctx, fallback=fallback, gate=gate)
    if result.llm_called:
        record_call(db, result, ctx, session_id=session_id)
    return result


def personalise_action(
    db: Session,
    state: SessionState,
    action: Action,
    *,
    grade: int,
    language: str,
    session_id: uuid.UUID | None,
    student_text: str | None = None,
) -> Action:
    """Mutates and returns `action`. Any problem leaves the authored text in place."""
    band = band_for_grade(grade)
    if band is None:
        return action
    base: dict[str, Any] = {"band": band, "language": language, "glossary": _glossary(db, language)}
    item = state.item()
    if (
        action.type == "hint"
        and action.hint_level in PERSONALISED_HINT_LEVELS
        and (action.extras or {}).get("kind") not in AUTHORED_HINT_KINDS
        and action.text
        and item is not None
    ):
        ctx = PromptContext(
            purpose=Purpose.personalise_hint,
            source=action.text,
            forbidden_answer=item.answer_sympy,
            fields={
                "item_stem": _stem(db, item.id),
                "hint_level": str(action.hint_level),
                "authored_hint": action.text,
                "misconception": action.misconception_id or "",
            },
            **base,
        )
        result = _run(db, state, ctx, action.text, session_id)
        _apply(action, result)
    elif action.type == "explain_back_result" and student_text and item is not None:
        model = item.authored_explanation or " ".join(item.solution_steps)
        ctx = PromptContext(
            purpose=Purpose.grade_explain_back,
            source=model,
            forbidden_answer=None,
            fields={"student_text": student_text, "rubric": model},
            **base,
        )
        result = _run(db, state, ctx, action.text or "", session_id)
        _apply(action, result)
        if result.source == "llm":
            action.grade = result.grade
    praise = (action.extras or {}).get("encouragement")
    authored = _authored_praise(praise, language)
    if isinstance(praise, dict) and authored:
        ctx = PromptContext(
            purpose=Purpose.encourage,
            source=authored,
            forbidden_answer=None,
            fields={"trigger": str(praise["trigger"])},
            **base,
        )
        result = _run(db, state, ctx, authored, session_id)
        if result.llm_called:
            action.llm_called = True
            state.llm_called = True
        if result.source == "llm":
            action.extras = {**action.extras, "encouragement": {**praise, "text": result.text}}
    return action


def _authored_praise(praise: object, language: str) -> str:
    """The authored sentence for a praise trigger (text already set, or the variant's copy)."""
    from app.content.copy import resolve_encouragement  # lazy: copy imports the orchestrator

    if not isinstance(praise, dict) or not praise.get("trigger"):
        return ""
    text = praise.get("text") or resolve_encouragement(
        str(praise["trigger"]), str(praise.get("variant")), language
    )
    return str(text or "")


def _apply(action: Action, result: LlmResult) -> None:
    if result.llm_called:
        action.llm_called = True
    if result.source == "llm":
        action.text = result.text
        action.source = "llm"
