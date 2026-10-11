"""The Ask flow (ARCHITECTURE section 12.3).

input safety -> current-item guard -> scoped search (Layer B) -> relevance gate (Layer C) ->
answer | clarify | out_of_scope -> cited answer with Layer D checks -> source chips.

The model is only asked to word an answer that the gate already allowed; if it is off, unavailable
or breaks a rule, the student gets the approved passage itself.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ask.config import ask_config, load_safety, message
from app.ask.gate import GateDecision, decide
from app.ask.guard import clean_question, screen, targets_current_item
from app.ask.search import Hit, candidates_for, rank
from app.auth.consent import active_scopes, is_guest
from app.config import settings
from app.content.gate import allow_draft_content
from app.db.models import ContentGapRow, ItemRow, SessionRow, StudentRow
from app.llm.gateway import Gate, record_call
from app.llm.personalise import get_gateway
from app.llm.prompt import PromptContext
from app.llm.purposes import Purpose
from app.registries.grade_bands import band_for_grade
from app.registries.loaders import load_all_curricula
from app.registries.locale_resolve import resolve_locale_chain

CITATION = re.compile(r"\s*\[[^\[\]]+\]")
CITED_ID = re.compile(r"\[([^\[\]]+)\]")
ASK_SESSION_TYPE = "ask"


@dataclass
class AskReply:
    kind: str  # answer | clarify | out_of_scope | route_to_help | refused | distress
    text: str
    reason: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    choices: list[dict[str, str]] = field(default_factory=list)
    llm_called: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "text": self.text,
            "reason": self.reason,
            "sources": self.sources,
            "choices": self.choices,
            "llm_called": self.llm_called,
        }


def question_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.casefold().split()).encode("utf-8")).hexdigest()


def log_gap(
    db: Session,
    student: StudentRow,
    question: str,
    reason: str,
    *,
    keep_text: bool,
    skill_id: str | None = None,
) -> ContentGapRow:
    """Record a question the book could not answer. The text itself needs `free_text` consent."""
    row = ContentGapRow(
        id=uuid.uuid4(),
        created_at=datetime.now(UTC),
        context_key=dict(student.context_key or {}),
        question_hash=question_hash(question),
        question_text=question if keep_text else None,
        skill_id=skill_id,
        tier=None,
        reason=reason,
    )
    db.add(row)
    return row


def source_label(student: StudentRow, hit: Hit, language: str) -> str:
    """'Linear equations, section 2, p. 62' from the curriculum registry."""
    spec = load_all_curricula().get(student.curriculum_id)
    chapter_id, _, key = hit.section_id.rpartition(".")
    title, order = "", ""
    for book in spec.books if spec else ():
        for chapter in book.chapters:
            if chapter.id != chapter_id:
                continue
            title = chapter.titles.get(language) or chapter.titles.get("en") or chapter_id
            for section in chapter.sections:
                if section.key == key:
                    order = str(section.order)
    parts = [title or chapter_id]
    if order:
        parts.append(f"section {order}")
    if hit.page:
        parts.append(f"p. {hit.page}")
    return ", ".join(parts)


def _sources(student: StudentRow, hits: list[Hit], language: str) -> list[dict[str, Any]]:
    return [
        {
            "passage_id": h.passage_id,
            "label": source_label(student, h, language),
            "source_ref": h.source_ref,
        }
        for h in hits
    ]


def _active_stem(db: Session, session_id: uuid.UUID | None, student: StudentRow) -> str | None:
    if session_id is None:
        return None
    row = db.get(SessionRow, session_id)
    if row is None or row.student_id != student.id:
        raise HTTPException(status_code=404, detail="session not found")
    item_id = (row.plan or {}).get("current_item_id")
    item = db.get(ItemRow, item_id) if item_id else None
    return str((item.stem or {}).get("en") or "") if item else None


def ask(
    db: Session,
    student: StudentRow,
    question: str,
    *,
    session_id: uuid.UUID | None = None,
    skill_id: str | None = None,
    choice: str | None = None,
) -> AskReply:
    language = student.home_language or "en"
    cfg = ask_config()
    if not settings.ask_enabled:
        raise HTTPException(status_code=404, detail="ask is not available")
    if is_guest(db, student.id) and not settings.ask_guests_enabled:
        raise HTTPException(status_code=403, detail="ask is not available for guests")
    scopes = active_scopes(db, student.id)
    if "free_text" not in scopes:
        raise HTTPException(status_code=403, detail="free_text consent required")

    cleaned = clean_question(question, cfg.max_question_chars)
    if cleaned.empty:
        raise HTTPException(status_code=422, detail="question required")
    if cleaned.too_long:
        return AskReply("refused", message("too_long", language), reason="too_long")
    lists = load_safety(language)
    verdict = screen(cleaned.text, lists)
    if verdict.kind == "distress":
        from app.safety import raise_distress

        raise_distress(db, student, "ask")  # pause tutoring and tell the adults
        return AskReply("distress", message("distress", language), reason="distress")
    if verdict.kind in {"injection", "moderation"}:
        return AskReply("refused", message("refused", language), reason=verdict.kind)
    why = targets_current_item(cleaned.text, _active_stem(db, session_id, student), lists)
    if why:
        return AskReply("route_to_help", message("route_to_help", language), reason=why)

    key = student.context_key or {}
    rows = candidates_for(
        db,
        curriculum_id=str(key.get("curriculum_id") or student.curriculum_id),
        book_id=str(key.get("book_id") or student.book_id),
        chapter_id=str(key.get("chapter_id") or student.current_chapter_id),
        locales=list(resolve_locale_chain(language)),
        allow_draft=allow_draft_content(),
    )
    if choice:
        picked = [r for r in rows if r.id == choice]
        if not picked:
            raise HTTPException(status_code=400, detail="unknown choice")
        decision = GateDecision("answer", hits=tuple(rank(cleaned.text, picked, cfg=cfg)))
    else:
        # Layer A: when the client names a skill, its passages are tried before the whole chapter.
        narrowed = [r for r in rows if skill_id and skill_id in (r.skill_ids or [])]
        decision = decide(rank(cleaned.text, narrowed, cfg=cfg), cfg)
        if decision.kind == "out_of_scope":
            decision = decide(rank(cleaned.text, rows, cfg=cfg), cfg)

    if decision.kind == "out_of_scope":
        log_gap(db, student, cleaned.text, decision.reason, keep_text=True, skill_id=skill_id)
        return AskReply("out_of_scope", message("out_of_scope", language), reason=decision.reason)
    if decision.kind == "clarify":
        return AskReply(
            "clarify",
            message("clarify", language),
            reason=decision.reason,
            choices=[
                {"passage_id": h.passage_id, "label": source_label(student, h, language)}
                for h in decision.choices
            ],
        )
    return _answer(db, student, cleaned.text, decision, session_id, language, scopes)


def _answer(
    db: Session,
    student: StudentRow,
    question: str,
    decision: GateDecision,
    session_id: uuid.UUID | None,
    language: str,
    scopes: set[str],
) -> AskReply:
    hits = list(decision.hits)
    fallback = hits[0].text
    sources = _sources(student, hits[:1], language)
    band = band_for_grade(student.grade)
    if band is None:
        return AskReply("answer", fallback, sources=sources)
    ctx = PromptContext(
        purpose=Purpose.answer_doubt,
        band=band,
        language=language,
        source="\n".join(f"[{h.passage_id}] {h.text}" for h in hits),
        fields={"student_text": question, "passage_ids": ",".join(h.passage_id for h in hits)},
    )
    gate = Gate(ASK_SESSION_TYPE, "ai_processing" in scopes, bool(settings.llm_api_key))
    result = get_gateway().generate(ctx, fallback=fallback, gate=gate)
    if result.llm_called:
        record_call(db, result, ctx, session_id=session_id)
    if result.source != "llm":
        return AskReply("answer", fallback, sources=sources, llm_called=result.llm_called)
    cited = set(CITED_ID.findall(result.text))
    used = [h for h in hits if h.passage_id in cited] or hits[:1]
    return AskReply(
        "answer",
        CITATION.sub("", result.text).strip(),
        sources=_sources(student, used, language),
        llm_called=True,
    )
