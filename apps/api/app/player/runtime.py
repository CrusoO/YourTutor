"""Wire policy() to persisted sessions and enrich actions for the player."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.actor import Actor
from app.auth.authz import can_start_session, require
from app.auth.consent import active_scopes, has_scope
from app.auth.security import as_utc, now_utc
from app.config import settings
from app.content.locale import is_missing_translation
from app.db.models import (
    EventRow,
    ItemRow,
    MasteryRow,
    OverlayRow,
    ReviewCardRow,
    SessionRow,
    SkillRow,
    StudentRow,
)
from app.learner.bkt import BktParams
from app.learner.types import LearnerState, Mastery, ReviewCard
from app.orchestrator.policy import policy
from app.player.action_flags import hint_solution_flags
from app.orchestrator.types import (
    SOFT_ACTIVE_MS,
    Action,
    CatalogItem,
    Event,
    SessionState,
    default_params,
)

GOAL_MS = SOFT_ACTIVE_MS


def _locale_value(blob: dict | None, locale: str) -> str:
    data = blob or {}
    requested = str(data.get(locale) or "")
    if locale != "en" and is_missing_translation(requested):
        return str(data.get("en") or "")
    if is_missing_translation(requested):
        return str(data.get("en") or requested)
    return requested


def _item_to_catalog(row: ItemRow) -> CatalogItem:
    answer = row.answer or {}
    hints = []
    for hint in row.hints or []:
        hints.append((int(hint.get("level", 0)), str(hint.get("en") or "")))
    steps = tuple(str((step or {}).get("en") or "") for step in (row.solution_steps or []))
    rules = []
    for rule in row.misconception_rules or []:
        rules.append((str(rule.get("id")), tuple(str(v) for v in rule.get("when_answer_equals") or [])))
    return CatalogItem(
        id=row.id,
        skill_ids=tuple(row.skill_ids or []),
        difficulty=float(row.difficulty),
        pool=row.pool,
        status=row.status,
        type=row.type,
        answer_sympy=str(answer.get("sympy") or "0"),
        accept=tuple(str(v) for v in answer.get("accept") or []),
        hints=tuple(hints),
        solution_steps=steps,
        misconception_rules=tuple(rules),
        prediction_prompt=str((row.prediction_prompt or {}).get("en") or ""),
        authored_explanation=steps[-1] if steps else "",
        verify=row.verify,
        options=tuple(row.options or ()),
    )


def load_catalog(session: Session, *, allow_draft: bool) -> tuple[CatalogItem, ...]:
    from app.content.gate import content_status_is_servable

    rows = session.scalars(select(ItemRow)).all()
    out = []
    for row in rows:
        if not content_status_is_servable(row.status, allow_draft=allow_draft):
            continue
        out.append(_item_to_catalog(row))
    return tuple(out)


def load_learner(session: Session, student_id: uuid.UUID) -> LearnerState:
    state = LearnerState()
    for row in session.scalars(select(MasteryRow).where(MasteryRow.student_id == student_id)).all():
        state.mastery[row.skill_id] = Mastery(
            skill_id=row.skill_id,
            p_known=row.p_known,
            attempts=row.attempts,
            unhinted_correct=row.unhinted_correct,
            hinted_correct=row.hinted_correct,
        )
    for row in session.scalars(select(ReviewCardRow).where(ReviewCardRow.student_id == student_id)).all():
        state.cards[row.skill_id] = ReviewCard(
            skill_id=row.skill_id,
            due_at=as_utc(row.due_at),
            fsrs_state=row.fsrs_state or {},
        )
    return state


def persist_learner(session: Session, student_id: uuid.UUID, learner: LearnerState) -> None:
    now = now_utc()
    for skill_id, mastery in learner.mastery.items():
        session.merge(
            MasteryRow(
                student_id=student_id,
                skill_id=skill_id,
                p_known=mastery.p_known,
                attempts=mastery.attempts,
                unhinted_correct=mastery.unhinted_correct,
                hinted_correct=mastery.hinted_correct,
                last_updated=now,
            )
        )
    for skill_id, card in learner.cards.items():
        session.merge(
            ReviewCardRow(
                student_id=student_id,
                skill_id=skill_id,
                fsrs_state=card.fsrs_state,
                due_at=card.due_at,
            )
        )


def _overlay_skills(session: Session, student: StudentRow) -> tuple[str, ...]:
    chapter_id = student.current_chapter_id
    if student.context_key and isinstance(student.context_key, dict):
        chapter_id = student.context_key.get("chapter_id") or chapter_id
    if chapter_id:
        row = session.get(OverlayRow, chapter_id)
        if row:
            return tuple(row.skill_ids or ())
    first = session.scalars(select(OverlayRow)).first()
    return tuple(first.skill_ids or ()) if first else ()


def _bkt_and_prereqs(session: Session, skill_ids: tuple[str, ...]) -> tuple[dict[str, BktParams], dict[str, tuple[str, ...]]]:
    params: dict[str, BktParams] = {}
    prereqs: dict[str, tuple[str, ...]] = {}
    rows = session.scalars(select(SkillRow)).all()
    for row in rows:
        raw = row.bkt or {}
        params[row.id] = BktParams(
            p_init=float(raw.get("p_init", 0.2)),
            p_learn=float(raw.get("p_learn", 0.15)),
            p_slip=float(raw.get("p_slip", 0.1)),
            p_guess=float(raw.get("p_guess", 0.2)),
        )
        prereqs[row.id] = tuple(row.prerequisites or ())
    for sid in skill_ids:
        params.setdefault(sid, default_params())
        prereqs.setdefault(sid, ())
    return params, prereqs


def _dump_action(action: Action | None) -> dict[str, Any] | None:
    if action is None:
        return None
    return {
        "type": action.type,
        "item_id": action.item_id,
        "skill_id": action.skill_id,
        "hint_level": action.hint_level,
        "misconception_id": action.misconception_id,
        "text": action.text,
        "source": action.source,
        "correct": action.correct,
        "grade": action.grade,
        "store_text": action.store_text,
        "llm_called": action.llm_called,
        "ended_reason": action.ended_reason,
        "resumable": action.resumable,
        "guardrail_flag": action.guardrail_flag,
        "rejected": action.rejected,
        "state_before": action.state_before,
        "state_after": action.state_after,
        "rule_id": action.rule_id,
        "extras": action.extras,
    }


def _load_action(data: dict[str, Any] | None) -> Action | None:
    if not data:
        return None
    return Action(
        type=str(data.get("type") or "show_item"),
        item_id=data.get("item_id"),
        skill_id=data.get("skill_id"),
        hint_level=data.get("hint_level"),
        misconception_id=data.get("misconception_id"),
        text=data.get("text"),
        source=str(data.get("source") or "authored"),
        correct=data.get("correct"),
        grade=data.get("grade"),
        store_text=bool(data.get("store_text")),
        llm_called=bool(data.get("llm_called")),
        ended_reason=data.get("ended_reason"),
        resumable=bool(data.get("resumable")),
        guardrail_flag=data.get("guardrail_flag"),
        rejected=bool(data.get("rejected")),
        state_before=data.get("state_before"),
        state_after=data.get("state_after"),
        rule_id=data.get("rule_id"),
        extras=dict(data.get("extras") or {}),
    )


def _dump_memory(memory: dict) -> dict[str, Any]:
    unhinted = memory.get("session_unhinted") or {}
    serial: dict[str, dict[str, list[int]]] = {}
    for skill, items in unhinted.items():
        serial[str(skill)] = {str(item): list(counts) for item, counts in items.items()}
    return {
        "bkt_done": list(memory.get("bkt_done") or []),
        "hinted": list(memory.get("hinted") or []),
        "first_wrong": list(memory.get("first_wrong") or []),
        "session_unhinted": serial,
        "warmup_skills": list(memory.get("warmup_skills") or []),
    }


def _load_memory(data: dict | None) -> dict:
    raw = data or {}
    unhinted: dict = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for skill, items in (raw.get("session_unhinted") or {}).items():
        for item, counts in items.items():
            unhinted[skill][item] = [int(counts[0]), int(counts[1])]
    return {
        "bkt_done": set(raw.get("bkt_done") or []),
        "hinted": set(raw.get("hinted") or []),
        "first_wrong": set(raw.get("first_wrong") or []),
        "session_unhinted": unhinted,
        "warmup_skills": set(raw.get("warmup_skills") or []),
    }


def dump_state(state: SessionState) -> dict[str, Any]:
    last_active = state.last_active_at.isoformat() if state.last_active_at else None
    return {
        "phase": state.phase,
        "current_skill": state.current_skill,
        "current_item_id": state.current_item_id,
        "hint_level_shown": state.hint_level_shown,
        "attempt_after_hint2": state.attempt_after_hint2,
        "bkt_updated": list(state.bkt_updated),
        "explain_back_done": list(state.explain_back_done),
        "introduced_skills": list(state.introduced_skills),
        "shown_item_ids": list(state.shown_item_ids),
        "items_completed": state.items_completed,
        "active_ms": state.active_ms,
        "last_active_at": last_active,
        "warmup_done": state.warmup_done,
        "warmup_left": state.warmup_left,
        "consent_revoked": state.consent_revoked,
        "has_ai_processing": state.has_ai_processing,
        "has_api_key": state.has_api_key,
        "allow_draft": state.allow_draft,
        "llm_called": state.llm_called,
        "ended_reason": state.ended_reason,
        "diagnostic_ids": list(state.diagnostic_ids),
        "checkpoint_ids": list(state.checkpoint_ids),
        "sequence_index": state.sequence_index,
        "diagnostic_results": state.diagnostic_results,
        "skipped_skills": list(state.skipped_skills),
        "skills_not_tested": list(state.skills_not_tested),
        "checkpoint_answers": state.checkpoint_answers,
        "checkpoint_result": state.checkpoint_result,
        "similar_from_item_id": state.similar_from_item_id,
        "last_wrong_response": state.last_wrong_response,
        "blocked_skills": list(state.blocked_skills),
        "content_gaps": state.content_gaps,
        "stored_explain_text": state.stored_explain_text,
        "last_action": _dump_action(state.last_action),
        "bkt_memory": _dump_memory(state.bkt_memory),
    }


def load_state(
    plan: dict[str, Any],
    *,
    session_type: str,
    now: datetime,
    catalog: tuple[CatalogItem, ...],
    overlay_skill_ids: tuple[str, ...],
    bkt_params: dict[str, BktParams],
    prerequisites: dict[str, tuple[str, ...]],
) -> SessionState:
    last_active = plan.get("last_active_at")
    parsed_active = datetime.fromisoformat(last_active) if last_active else now
    return SessionState(
        session_type=session_type,
        now=now,
        catalog=catalog,
        overlay_skill_ids=overlay_skill_ids,
        bkt_params=bkt_params,
        prerequisites=prerequisites,
        phase=str(plan.get("phase") or "start"),
        current_skill=plan.get("current_skill"),
        current_item_id=plan.get("current_item_id"),
        hint_level_shown=int(plan.get("hint_level_shown") or 0),
        attempt_after_hint2=bool(plan.get("attempt_after_hint2")),
        bkt_updated=set(plan.get("bkt_updated") or []),
        explain_back_done=set(plan.get("explain_back_done") or []),
        introduced_skills=set(plan.get("introduced_skills") or []),
        shown_item_ids=list(plan.get("shown_item_ids") or []),
        items_completed=int(plan.get("items_completed") or 0),
        active_ms=int(plan.get("active_ms") or 0),
        last_active_at=parsed_active,
        warmup_done=bool(plan.get("warmup_done")),
        warmup_left=int(plan.get("warmup_left") or 0),
        last_action=_load_action(plan.get("last_action")),
        consent_revoked=bool(plan.get("consent_revoked")),
        has_ai_processing=bool(plan.get("has_ai_processing")),
        has_api_key=False,
        allow_draft=bool(plan.get("allow_draft", settings.allow_draft_content)),
        llm_called=bool(plan.get("llm_called")),
        ended_reason=plan.get("ended_reason"),
        diagnostic_ids=list(plan.get("diagnostic_ids") or []),
        checkpoint_ids=list(plan.get("checkpoint_ids") or []),
        sequence_index=int(plan.get("sequence_index") or 0),
        diagnostic_results=list(plan.get("diagnostic_results") or []),
        skipped_skills=set(plan.get("skipped_skills") or []),
        skills_not_tested=list(plan.get("skills_not_tested") or []),
        checkpoint_answers=list(plan.get("checkpoint_answers") or []),
        checkpoint_result=plan.get("checkpoint_result"),
        stored_explain_text=plan.get("stored_explain_text"),
        similar_from_item_id=plan.get("similar_from_item_id"),
        last_wrong_response=plan.get("last_wrong_response"),
        blocked_skills=set(plan.get("blocked_skills") or []),
        content_gaps=list(plan.get("content_gaps") or []),
        bkt_memory=_load_memory(plan.get("bkt_memory")),
    )


def _build_state(session: Session, row: SessionRow, student: StudentRow) -> tuple[SessionState, LearnerState]:
    scopes = active_scopes(session, student.id)
    skills = _overlay_skills(session, student)
    params, prereqs = _bkt_and_prereqs(session, skills)
    catalog = load_catalog(session, allow_draft=settings.allow_draft_content)
    state = load_state(
        row.plan or {},
        session_type=row.type,
        now=now_utc(),
        catalog=catalog,
        overlay_skill_ids=skills,
        bkt_params=params,
        prerequisites=prereqs,
    )
    state.has_ai_processing = "ai_processing" in scopes
    state.allow_draft = settings.allow_draft_content
    state.active_ms = row.active_ms
    if not state.checkpoint_ids and row.type == "checkpoint":
        if student.current_chapter_id == "OV.E2E.MINI":
            state.checkpoint_ids = [
                item.id
                for item in catalog
                if item.pool == "checkpoint" and item.primary_skill in skills
            ]
        else:
            state.checkpoint_ids = [item.id for item in catalog if item.pool == "checkpoint"]
    return state, load_learner(session, student.id)


def _persist_state(row: SessionRow, state: SessionState) -> None:
    row.plan = dump_state(state)
    row.active_ms = state.active_ms
    row.llm_called = state.llm_called
    row.last_active_at = now_utc()
    if state.last_action and state.last_action.type == "end_session":
        row.ended_reason = state.last_action.ended_reason or state.ended_reason
        row.resumable = bool(state.last_action.resumable)
        if row.ended_at is None:
            row.ended_at = now_utc()
    elif state.phase == "ended" and state.ended_reason:
        row.ended_reason = state.ended_reason
        if row.ended_at is None:
            row.ended_at = now_utc()
    else:
        row.ended_at = None
        row.ended_reason = None
        row.resumable = False


def _item_payload(row: ItemRow | None, locale: str, *, reveal: bool, steps: bool) -> dict[str, Any] | None:
    if row is None:
        return None
    payload = {
        "id": row.id,
        "type": row.type,
        "skill_ids": row.skill_ids,
        "stem": _locale_value(row.stem, locale),
        "prediction": _locale_value(row.prediction_prompt, locale),
        "options": [
            {
                "id": str(opt.get("id") or ""),
                "label": _locale_value(opt, locale) or str(opt.get("id") or ""),
            }
            for opt in (row.options or [])
        ],
    }
    if steps:
        payload["steps"] = [_locale_value(step, locale) for step in (row.solution_steps or [])]
    if reveal:
        payload["answer"] = (row.answer or {}).get("sympy")
        payload["hints"] = [
            {"level": hint.get("level"), "text": _locale_value(hint, locale)}
            for hint in (row.hints or [])
        ]
    return payload


def enrich_action(
    session: Session,
    state: SessionState,
    action: Action,
    locale: str,
) -> dict[str, Any]:
    item_row = session.get(ItemRow, action.item_id) if action.item_id else None
    if item_row is None and state.current_item_id:
        item_row = session.get(ItemRow, state.current_item_id)
    reveal = action.type in {"reveal_solution", "explain_back_result"}
    steps = action.type in {"worked_example", "reveal_solution", "explain_back_prompt", "explain_back_result"}
    extras = dict(action.extras or {})
    assessment = bool(extras.get("assessment") or state.session_type in {"diagnostic", "checkpoint"})
    can_request_hint, can_show_solution = hint_solution_flags(
        state, action, assessment=assessment
    )
    payload = {
        "type": action.type,
        "item_id": action.item_id or state.current_item_id,
        "skill_id": action.skill_id or state.current_skill,
        "hint_level": action.hint_level,
        "misconception_id": action.misconception_id,
        "text": action.text,
        "source": action.source,
        "correct": action.correct,
        "grade": action.grade,
        "ended_reason": action.ended_reason or state.ended_reason,
        "reason": action.ended_reason or extras.get("reason") or state.ended_reason,
        "resumable": action.resumable,
        "rejected": action.rejected,
        "guardrail_flag": action.guardrail_flag,
        "extras": extras,
        "session_type": state.session_type,
        "phase": state.phase,
        "hint_level_shown": state.hint_level_shown,
        "allow_hint": can_request_hint,
        "can_request_hint": can_request_hint,
        "can_show_solution": can_show_solution,
        "dont_know_option": bool(extras.get("dont_know_option")),
        "item": _item_payload(item_row, locale, reveal=reveal, steps=steps),
    }
    if action.type == "hint" and item_row is not None:
        payload["item"] = _item_payload(item_row, locale, reveal=False, steps=False)
    return payload


def session_view(session: Session, actor: Actor, row: SessionRow) -> dict[str, Any]:
    student = session.get(StudentRow, row.student_id)
    assert student is not None
    require(can_start_session(actor, student) or actor.is_admin)
    state, learner = _build_state(session, row, student)
    if not (row.plan or {}).get("last_action"):
        event = Event(type="resume") if row.resumable or row.ended_at else None
        if row.resumable:
            row.ended_at = None
            row.ended_reason = None
            row.resumable = False
        action = policy(learner, state, event)
        persist_learner(session, student.id, learner)
        _persist_state(row, state)
    else:
        action = state.last_action or Action(type="show_item", item_id=state.current_item_id)
    locale = student.home_language or "en"
    enriched = enrich_action(session, state, action, locale)
    return {
        "id": str(row.id),
        "type": row.type,
        "student_id": str(row.student_id),
        "action": enriched,
        "progress": {
            "items_completed": state.items_completed,
            "active_ms": row.active_ms,
            "resumable": bool(row.resumable),
            "ended_reason": row.ended_reason,
        },
        "llm_called": row.llm_called,
    }


def apply_player_event(
    session: Session,
    actor: Actor,
    row: SessionRow,
    *,
    client_event_id: uuid.UUID,
    event_type: str,
    item_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    student = session.get(StudentRow, row.student_id)
    assert student is not None
    require(can_start_session(actor, student) or actor.is_admin)
    if not has_scope(session, row.student_id, "tutoring"):
        row.ended_at = now_utc()
        row.ended_reason = "consent_revoked"
        row.resumable = False
        return {
            "session_id": str(row.id),
            "duplicate": False,
            "action": {"type": "end_session", "reason": "consent_revoked", "ended_reason": "consent_revoked"},
            "progress": {"items_completed": 0, "active_ms": row.active_ms, "resumable": False},
            "llm_called": False,
        }
    prior = session.scalar(select(EventRow).where(EventRow.client_event_id == client_event_id))
    if prior:
        view = session_view(session, actor, row)
        view["session_id"] = str(row.id)
        view["duplicate"] = True
        return view
    state, learner = _build_state(session, row, student)
    event = Event(
        type=event_type,
        response=str(payload.get("response")) if payload.get("response") is not None else None,
        client_correct=payload.get("correct"),
        latency_ms=payload.get("latency_ms"),
        item_id=item_id,
        idle_ms=payload.get("idle_ms"),
        text=payload.get("text"),
    )
    action = policy(learner, state, event)
    persist_learner(session, student.id, learner)
    _persist_state(row, state)
    session.add(
        EventRow(
            id=uuid.uuid4(),
            client_event_id=client_event_id,
            session_id=row.id,
            item_id=item_id or action.item_id,
            event_type=event_type,
            payload=payload,
            correct=action.correct,
            hint_level=action.hint_level,
            latency_ms=payload.get("latency_ms"),
            created_at=now_utc(),
            state_before=action.state_before,
            state_after=action.state_after,
            rule_id=action.rule_id,
        )
    )
    locale = student.home_language or "en"
    return {
        "session_id": str(row.id),
        "duplicate": False,
        "action": enrich_action(session, state, action, locale),
        "progress": {
            "items_completed": state.items_completed,
            "active_ms": row.active_ms,
            "resumable": bool(row.resumable),
            "ended_reason": row.ended_reason,
        },
        "llm_called": row.llm_called,
    }


def today_payload(session: Session, student: StudentRow) -> dict[str, Any]:
    from app.db.models import CurriculumRow
    from app.registries.loaders import load_jurisdiction_profile
    from app.registries.quiet_hours import in_quiet_hours

    curriculum = session.get(CurriculumRow, student.curriculum_id)
    default_tz = curriculum.default_timezone if curriculum else "UTC"
    tz = ZoneInfo(student.timezone or default_tz)
    profile = load_jurisdiction_profile(
        curriculum.jurisdiction_profile if curriculum else "default_strict"
    )
    start_local = datetime.combine(datetime.now(tz).date(), time.min, tzinfo=tz)
    start_utc = start_local.astimezone(ZoneInfo("UTC"))
    rows = session.scalars(
        select(SessionRow).where(SessionRow.student_id == student.id, SessionRow.started_at >= start_utc)
    ).all()
    used = sum(row.active_ms for row in rows)
    remaining = max(0, int((GOAL_MS - used) / 60000))
    open_row = session.scalar(
        select(SessionRow).where(
            SessionRow.student_id == student.id,
            SessionRow.ended_at.is_(None),
        )
    )
    idle_row = session.scalar(
        select(SessionRow).where(
            SessionRow.student_id == student.id,
            SessionRow.resumable.is_(True),
        )
    )
    resume = open_row or idle_row
    return {
        "student_id": str(student.id),
        "display_name": student.display_name,
        "goal_minutes": int(GOAL_MS / 60000),
        "remaining_active_minutes": remaining,
        "used_active_ms": used,
        "timezone": student.timezone,
        "locale": student.home_language,
        "resume": (
            {"session_id": str(resume.id), "type": resume.type, "resumable": bool(resume.resumable)}
            if resume
            else None
        ),
        "quiet_hours": {
            "start": profile.quiet_hours.start,
            "end": profile.quiet_hours.end,
            "active": in_quiet_hours(now_utc(), tz, profile),
        },
    }
