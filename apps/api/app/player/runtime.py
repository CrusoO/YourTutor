"""Wire policy() to persisted sessions and enrich actions for the player."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.actor import Actor
from app.auth.authz import can_start_session, require
from app.auth.consent import active_scopes, has_scope
from app.auth.security import as_utc, now_utc
from app.config import settings
from app.content.copy import with_encouragement_text
from app.content.locale import is_missing_translation
from app.content.signatures import structure_signature
from app.db.models import (
    EventRow,
    ItemRow,
    MasteryRow,
    MisconceptionRow,
    OverlayRow,
    ReviewCardRow,
    SessionRow,
    SkillRow,
    StudentRow,
    TeacherAlertRow,
)
from app.learner.bkt import BktParams
from app.learner.ladder import SkillLadder
from app.learner.types import LearnerState, Mastery, ReviewCard
from app.lessons.path import lesson_path
from app.llm.personalise import personalise_action
from app.orchestrator.policy import policy
from app.orchestrator.types import (
    SOFT_ACTIVE_MS,
    Action,
    CatalogItem,
    Event,
    SessionState,
    default_params,
)
from app.player.action_flags import hint_solution_flags
from app.player.lesson_events import LESSON_EVENTS, check_lesson_event, lesson_for_state
from app.registries.grade_bands import SessionLimits, session_limits, ui_for_grade

GOAL_MS = (
    SOFT_ACTIVE_MS  # default (grades 9-10); the student's band decides, see limits_for_student
)


def limits_for_student(student: StudentRow) -> SessionLimits:
    """Session caps and word limit from the student's grade band (config/grade_bands.yaml)."""
    return session_limits(student.grade)


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
        rules.append(
            (str(rule.get("id")), tuple(str(v) for v in rule.get("when_answer_equals") or []))
        )
    return CatalogItem(
        id=row.id,
        skill_ids=tuple(row.skill_ids or []),
        difficulty=float(row.difficulty),
        pool=row.pool,
        status=row.status,
        role=row.role or "procedure",
        structure=structure_signature(str((row.stem or {}).get("en") or "")),
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
        slip_patterns=tuple(row.slip_patterns or ()),
        prereq_signatures=tuple(row.prereq_signatures or ()),
        intermediate_values=tuple(str(v) for v in (row.intermediate_values or ())),
        min_plausible_ms=row.min_plausible_ms,
        step_hints=tuple(str((s or {}).get("en") or "") for s in (row.step_hints or ())),
        hint_restate=str((row.hint_restate or {}).get("en") or ""),
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
        state.ladders[row.skill_id] = _ladder_from_row(row)
    for card_row in session.scalars(
        select(ReviewCardRow).where(ReviewCardRow.student_id == student_id)
    ).all():
        state.cards[card_row.skill_id] = ReviewCard(
            skill_id=card_row.skill_id,
            due_at=as_utc(card_row.due_at),
            fsrs_state=card_row.fsrs_state or {},
        )
    return state


def _ladder_from_row(row: MasteryRow) -> SkillLadder:
    memory = row.ladder_memory or {}
    if memory.get("skill_id") == row.skill_id:
        return SkillLadder.from_json(memory)
    evidence = {int(k): list(v) for k, v in (row.ladder_evidence or {}).items()}
    achieved = sorted(evidence) or ([row.ladder_level] if row.ladder_level else [])
    return SkillLadder(
        skill_id=row.skill_id, achieved=achieved, evidence=evidence, flags=dict(row.flags or {})
    )


def persist_learner(session: Session, student_id: uuid.UUID, learner: LearnerState) -> None:
    now = now_utc()
    for skill_id, mastery in learner.mastery.items():
        ladder = learner.ladders.get(skill_id)
        summary = ladder.summary() if ladder else {"level": 0, "evidence": {}, "flags": {}}
        session.merge(
            MasteryRow(
                student_id=student_id,
                skill_id=skill_id,
                p_known=mastery.p_known,
                attempts=mastery.attempts,
                unhinted_correct=mastery.unhinted_correct,
                hinted_correct=mastery.hinted_correct,
                last_updated=now,
                ladder_level=summary["level"],
                ladder_evidence=summary["evidence"],
                flags=summary["flags"],
                ladder_memory=ladder.to_json() if ladder else {},
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


def _overlay_skills(
    session: Session, student: StudentRow, plan: dict | None = None
) -> tuple[str, ...]:
    chapter_id = student.current_chapter_id
    if student.context_key and isinstance(student.context_key, dict):
        chapter_id = student.context_key.get("chapter_id") or chapter_id
    if plan and plan.get("overlay_id"):
        chapter_id = str(plan["overlay_id"])
    if chapter_id:
        row = session.get(OverlayRow, chapter_id)
        if row:
            return tuple(row.skill_ids or ())
    first = session.scalars(select(OverlayRow)).first()
    return tuple(first.skill_ids or ()) if first else ()


def _bkt_and_prereqs(
    session: Session, skill_ids: tuple[str, ...]
) -> tuple[dict[str, BktParams], dict[str, tuple[str, ...]]]:
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
        "warmup_skills": {tuple(pair) for pair in raw.get("warmup_skills") or []},
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
        "last_wrong_item_id": state.last_wrong_item_id,
        "fast_streak": state.fast_streak,
        "help_without_attempt": state.help_without_attempt,
        "stuck_item_id": state.stuck_item_id,
        "stretch_served": state.stretch_served,
        "wheel_skills": sorted(state.wheel_skills),
        "wrong_first_streak": state.wrong_first_streak,
        "skill_items": state.skill_items,
        "seen_items": sorted(state.seen_items),
        "answered_items": sorted(state.answered_items),
        "probe_for": state.probe_for,
        "lesson_prereq_levels": state.lesson_prereq_levels,
        "probe_skill": state.probe_skill,
        "probe_done": sorted(state.probe_done),
        "scheduled_prereq": state.scheduled_prereq,
        "scheduled_left": state.scheduled_left,
        "reveals": state.reveals,
        "wrong_run": state.wrong_run,
        "tier_down_items": state.tier_down_items,
        "tier_up_next": state.tier_up_next,
        "unhinted_run": state.unhinted_run,
        "last_failure": state.last_failure,
        "win_served": state.win_served,
        "skill_failed": sorted(state.skill_failed),
        "last_praise_at": state.last_praise_at,
        "praise_count": state.praise_count,
        "stretch_skills": sorted(state.stretch_skills),
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
        last_wrong_item_id=plan.get("last_wrong_item_id"),
        fast_streak=int(plan.get("fast_streak") or 0),
        help_without_attempt=int(plan.get("help_without_attempt") or 0),
        stuck_item_id=plan.get("stuck_item_id"),
        stretch_served=int(plan.get("stretch_served") or 0),
        wheel_skills=set(plan.get("wheel_skills") or []),
        wrong_first_streak={k: int(v) for k, v in (plan.get("wrong_first_streak") or {}).items()},
        skill_items={k: int(v) for k, v in (plan.get("skill_items") or {}).items()},
        seen_items=set(plan.get("seen_items") or []),
        answered_items=set(plan.get("answered_items") or []),
        probe_for=plan.get("probe_for"),
        lesson_prereq_levels={
            k: [int(x) for x in v] for k, v in (plan.get("lesson_prereq_levels") or {}).items()
        },
        probe_skill=plan.get("probe_skill"),
        probe_done=set(plan.get("probe_done") or []),
        scheduled_prereq=plan.get("scheduled_prereq"),
        scheduled_left=int(plan.get("scheduled_left") or 0),
        reveals=int(plan.get("reveals") or 0),
        wrong_run=int(plan.get("wrong_run") or 0),
        tier_down_items=int(plan.get("tier_down_items") or 0),
        tier_up_next=bool(plan.get("tier_up_next")),
        unhinted_run=int(plan.get("unhinted_run") or 0),
        last_failure=bool(plan.get("last_failure")),
        win_served=bool(plan.get("win_served")),
        skill_failed=set(plan.get("skill_failed") or []),
        last_praise_at=int(plan.get("last_praise_at", -99)),
        praise_count=int(plan.get("praise_count") or 0),
        stretch_skills=set(plan.get("stretch_skills") or []),
        blocked_skills=set(plan.get("blocked_skills") or []),
        content_gaps=list(plan.get("content_gaps") or []),
        bkt_memory=_load_memory(plan.get("bkt_memory")),
    )


def _build_state(
    session: Session, row: SessionRow, student: StudentRow
) -> tuple[SessionState, LearnerState]:
    scopes = active_scopes(session, student.id)
    skills = _overlay_skills(session, student, row.plan)
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
    state.session_key = str(row.id)
    state.teacher_share = "teacher_share" in scopes
    limits = limits_for_student(student)
    state.soft_active_ms = limits.soft_active_ms
    state.soft_item_cap = limits.soft_items
    state.hard_active_ms = limits.hard_active_ms
    state.max_words = limits.max_words
    locale = student.home_language or "en"
    for mc in session.scalars(select(MisconceptionRow)):
        state.misconception_remedial[mc.id] = mc.remedial_skill
        text = _locale_value(mc.explanation, locale)
        if text:
            state.misconception_text[mc.id] = text
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


# plan keys owned by the session, not by the policy state; they survive every rewrite
_PLAN_KEEP = ("overlay_id", "levels_at_start", "offline", "client_session_id", "last_event_at")


def _persist_state(row: SessionRow, state: SessionState) -> None:
    kept = {k: (row.plan or {})[k] for k in _PLAN_KEEP if (row.plan or {}).get(k) is not None}
    row.plan = dump_state(state)
    row.plan.update(kept)
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


def _item_payload(
    row: ItemRow | None, locale: str, *, reveal: bool, steps: bool
) -> dict[str, Any] | None:
    if row is None:
        return None
    payload: dict[str, Any] = {
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


def _localised_help_text(row: ItemRow, action: Action, locale: str) -> str | None:
    """Step hints and the restated question are authored per language; fall back to English."""
    kind = (action.extras or {}).get("kind")
    if kind == "restate" and row.hint_restate:
        return _locale_value(row.hint_restate, locale) or None
    if kind == "step":
        index = int((action.extras or {}).get("step", -1))
        steps = row.step_hints or []
        if 0 <= index < len(steps):
            text = _locale_value(steps[index], locale)
            if text:
                return text
    return None


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
    steps = action.type in {
        "worked_example",
        "reveal_solution",
        "explain_back_prompt",
        "explain_back_result",
    }
    extras = with_encouragement_text(dict(action.extras or {}), locale)
    assessment = bool(
        extras.get("assessment") or state.session_type in {"diagnostic", "checkpoint"}
    )
    can_request_hint, can_show_solution = hint_solution_flags(state, action, assessment=assessment)
    payload = {
        "type": action.type,
        "item_id": action.item_id or state.current_item_id,
        "skill_id": action.skill_id or state.current_skill,
        "hint_level": action.hint_level,
        "misconception_id": action.misconception_id,
        "text": action.text,
        "source": action.source,
        "llm_called": action.llm_called,
        "correct": action.correct,
        "grade": action.grade,
        "ended_reason": action.ended_reason or state.ended_reason,
        "reason": action.ended_reason or extras.get("reason") or state.ended_reason,
        "resumable": action.resumable,
        "rejected": action.rejected,
        "guardrail_flag": action.guardrail_flag,
        "rule_id": action.rule_id,
        "extras": extras,
        "session_type": state.session_type,
        "phase": state.phase,
        "hint_level_shown": state.hint_level_shown,
        "allow_hint": can_request_hint,
        "can_request_help": can_request_hint,
        "can_request_hint": can_request_hint,  # deprecated alias of can_request_help
        "can_show_solution": can_show_solution,
        "dont_know_option": bool(extras.get("dont_know_option")),
        "item": _item_payload(item_row, locale, reveal=reveal, steps=steps),
    }
    if action.type == "hint" and item_row is not None:
        payload["item"] = _item_payload(item_row, locale, reveal=False, steps=False)
        payload["text"] = _localised_help_text(item_row, action, locale) or action.text
    payload["sources"] = _source_chips(action, state)
    if action.type in {"predict", "worked_example"}:
        lesson = lesson_for_state(state)
        if lesson is not None:
            order, kinds = lesson_path(
                state.lesson_prereq_levels.get(state.current_skill or "", []),
                [beat.kind for beat in lesson.beats],
            )
            served = lesson.model_dump(mode="json", by_alias=True, exclude_none=True)
            served["beats"] = _beats_in_path(served["beats"], kinds)
            served["order"] = order
            payload["lesson"] = served
    return payload


SOURCE_CHIP_ACTIONS = frozenset(
    {"predict", "worked_example", "reveal_solution", "explain_back_result"}
)


def _source_chips(action: Action, state: SessionState) -> list[dict[str, str]]:
    """Where an explanation comes from: the approved source of the skill lesson, with its title."""
    from app.lessons.loader import lesson_for_skill, servable
    from app.lessons.sources import source_titles

    skill_id = action.skill_id or state.current_skill
    if action.type not in SOURCE_CHIP_ACTIONS or not skill_id:
        return []
    lesson = lesson_for_skill(skill_id)
    if lesson is None or not servable(lesson):
        return []
    refs = list(dict.fromkeys([lesson.source_ref, *(s.source_ref for s in lesson.scenes())]))
    titles = source_titles()
    return [{"id": ref, "title": titles.get(ref, ref)} for ref in refs]


def _beats_in_path(beats: list[dict], kinds: list[str]) -> list[dict]:
    """The authored beats R38 keeps, in order (kinds may repeat, so walk both lists together)."""
    out: list[dict] = []
    wanted = iter(kinds)
    want = next(wanted, None)
    for beat in beats:
        if beat["kind"] == want:
            out.append(beat)
            want = next(wanted, None)
    return out


def reopen_idle(row: SessionRow) -> bool:
    """Reopen a session that ended as idle (resumable). Returns True when it was reopened.

    Used by Resume on Today and by starting a session of the same type: both land in the same
    place, so a student never sees "Done for now / idle" for a session they can continue.
    """
    if not row.resumable:
        return False
    row.ended_at = None
    row.ended_reason = None
    row.resumable = False
    row.last_active_at = now_utc()
    plan = dict(row.plan or {})
    plan["last_active_at"] = row.last_active_at.isoformat()  # resuming restarts the idle clock
    last = plan.get("last_action") or {}
    if last.get("type") == "end_session":
        plan["last_action"] = None
        plan["ended_reason"] = None
        plan["phase"] = "practice" if plan.get("current_item_id") else "start"
    row.plan = plan
    return True


def session_view(session: Session, actor: Actor, row: SessionRow) -> dict[str, Any]:
    student = session.get(StudentRow, row.student_id)
    assert student is not None
    require(can_start_session(actor, student) or actor.is_admin)
    if row.type == "test_out":
        from app.player import test_out

        return test_out.view(session, student, row)
    expire_stale_sessions(session, student)
    reopened = reopen_idle(row)
    state, learner = _build_state(session, row, student)
    if not (row.plan or {}).get("last_action"):
        event = Event(type="resume") if reopened or row.ended_at else None
        action = policy(learner, state, event)
        persist_learner(session, student.id, learner)
        sync_alerts(session, student, state, learner)
        _persist_state(row, state)
    else:
        action = state.last_action or Action(type="show_item", item_id=state.current_item_id)
    locale = student.home_language or "en"
    enriched = enrich_action(session, state, action, locale)
    _attach_summary(session, student, row, enriched)
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


from app.player.ladder_log import recompute_ladders  # noqa: E402,F401


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
            "action": {
                "type": "end_session",
                "reason": "consent_revoked",
                "ended_reason": "consent_revoked",
            },
            "progress": {"items_completed": 0, "active_ms": row.active_ms, "resumable": False},
            "llm_called": False,
        }
    prior = session.scalar(select(EventRow).where(EventRow.client_event_id == client_event_id))
    if prior:
        view = session_view(session, actor, row)
        view["session_id"] = str(row.id)
        view["duplicate"] = True
        return view
    if row.type == "test_out":
        from app.player import test_out

        catalog = load_catalog(session, allow_draft=settings.allow_draft_content)
        return test_out.apply_event(
            session, row, student, catalog, client_event_id, event_type, item_id, payload
        )
    state, learner = _build_state(session, row, student)
    if event_type in LESSON_EVENTS:
        return _apply_lesson_event(
            session, row, student, state, event_type, payload, client_event_id
        )
    response = str(payload.get("response")) if payload.get("response") is not None else None
    if event_type in {"stuck_choice", "break_choice"}:
        response = str(payload.get("choice") or "")
    elif event_type == "stuck_step":
        response = str(payload.get("index")) if payload.get("index") is not None else ""
    event = Event(
        type=event_type,
        response=response,
        client_correct=payload.get("correct"),
        latency_ms=payload.get("latency_ms"),
        item_id=item_id,
        idle_ms=payload.get("idle_ms"),
        text=payload.get("text"),
        event_id=str(client_event_id),
    )
    action = policy(learner, state, event)
    action = personalise_action(
        session,
        state,
        action,
        grade=student.grade,
        language=student.home_language or "en",
        session_id=row.id,
        student_text=event.text or event.response if event_type == "explain_back" else None,
    )
    persist_learner(session, student.id, learner)
    sync_alerts(session, student, state, learner)
    _persist_state(row, state)
    session.add(
        EventRow(
            id=uuid.uuid4(),
            client_event_id=client_event_id,
            session_id=row.id,
            item_id=item_id or action.item_id,
            event_type="request_help" if event_type == "request_hint" else event_type,
            payload={**payload, "diagnosis": state.last_diagnosis}
            if state.last_diagnosis
            else payload,
            correct=state.last_correct if event_type == "answer" else action.correct,
            hint_level=action.hint_level,
            latency_ms=payload.get("latency_ms"),
            created_at=state.now,
            state_before=action.state_before,
            state_after=action.state_after,
            rule_id=action.rule_id,
        )
    )
    locale = student.home_language or "en"
    enriched = enrich_action(session, state, action, locale)
    _attach_summary(session, student, row, enriched)
    return {
        "session_id": str(row.id),
        "duplicate": False,
        "action": enriched,
        "progress": {
            "items_completed": state.items_completed,
            "active_ms": row.active_ms,
            "resumable": bool(row.resumable),
            "ended_reason": row.ended_reason,
        },
        "llm_called": row.llm_called,
    }


def sync_alerts(
    session: Session, student: StudentRow, state: SessionState, learner: LearnerState
) -> None:
    """Write queued teacher alerts (the policy only queues them with teacher_share) and resolve
    open ones whose skill has reached ladder level 4."""
    now = now_utc()
    open_rows = session.scalars(
        select(TeacherAlertRow).where(
            TeacherAlertRow.student_id == student.id, TeacherAlertRow.resolved_at.is_(None)
        )
    ).all()
    have = {(row.skill_id, row.type) for row in open_rows}
    if state.teacher_share:
        from app.views.alerts import repeated_misconceptions

        state.alerts.extend(repeated_misconceptions(session, student.id, now))
    for alert in state.alerts:
        key = (alert["skill_id"], alert["type"])
        if key not in have:
            session.add(
                TeacherAlertRow(
                    id=uuid.uuid4(),
                    student_id=student.id,
                    skill_id=key[0],
                    type=key[1],
                    created_at=now,
                )
            )
            have.add(key)
    state.alerts = []
    for row in open_rows:
        ladder = learner.ladders.get(row.skill_id)
        if ladder is not None and ladder.level >= 4:
            row.resolved_at = now
    session.flush()


def _attach_summary(
    session: Session, student: StudentRow, row: SessionRow, payload: dict[str, Any]
) -> None:
    from app.player.done import attach_summary

    attach_summary(session, student, row, payload)


def _apply_lesson_event(
    session: Session,
    row: SessionRow,
    student: StudentRow,
    state: SessionState,
    event_type: str,
    payload: dict[str, Any],
    client_event_id: uuid.UUID,
) -> dict[str, Any]:
    """Record a lesson beat event after the server re-checks it. No policy call, no BKT/FSRS."""
    verdict = check_lesson_event(state, event_type, payload)
    session.add(
        EventRow(
            id=uuid.uuid4(),
            client_event_id=client_event_id,
            session_id=row.id,
            item_id=None,
            event_type=event_type,
            payload={**payload, "_verdict": {"ok": verdict.ok, "code": verdict.code}},
            correct=verdict.correct,
            hint_level=None,
            latency_ms=payload.get("latency_ms"),
            created_at=state.now,
            state_before=state.phase,
            state_after=state.phase,
            rule_id=None,
        )
    )
    action = state.last_action or Action(type=state.phase)
    enriched = enrich_action(session, state, action, student.home_language or "en")
    enriched["rejected"] = not verdict.ok
    enriched["lesson_correct"] = verdict.correct  # the server's verdict, for beat feedback
    enriched["guardrail_flag"] = None if verdict.ok else verdict.code
    return {
        "session_id": str(row.id),
        "duplicate": False,
        "action": enriched,
        "progress": {
            "items_completed": state.items_completed,
            "active_ms": row.active_ms,
            "resumable": bool(row.resumable),
            "ended_reason": row.ended_reason,
        },
        "llm_called": row.llm_called,
    }


def expire_stale_sessions(session: Session, student: StudentRow) -> None:
    """Close sessions that crossed local midnight (ARCHITECTURE: resume only within the same day).

    Open or idle-resumable sessions whose last activity was on an earlier local day are ended with
    `day_rollover` and are no longer resumable. Progress is unaffected: it lives in the student
    model, not in the session.
    """
    from app.registries.timezone import same_local_day

    now = now_utc()
    zone = _student_tz(session, student).key
    rows = session.scalars(
        select(SessionRow).where(
            SessionRow.student_id == student.id,
            (SessionRow.ended_at.is_(None)) | (SessionRow.resumable.is_(True)),
        )
    ).all()
    for row in rows:
        if row.type == "test_out" or same_local_day(as_utc(row.last_active_at), now, zone):
            continue
        row.resumable = False
        if row.ended_at is None:
            row.ended_at = now
        row.ended_reason = "day_rollover"
        plan = dict(row.plan or {})
        plan["last_action"] = _dump_action(
            Action(type="end_session", ended_reason="day_rollover", resumable=False)
        )
        row.plan = plan
    session.flush()  # later queries in this request must see the expiry


def _student_tz(session: Session, student: StudentRow) -> ZoneInfo:
    from app.db.models import CurriculumRow

    curriculum = session.get(CurriculumRow, student.curriculum_id)
    return ZoneInfo(student.timezone or (curriculum.default_timezone if curriculum else "UTC"))


def _used_active_ms(session: Session, student: StudentRow, tz: ZoneInfo) -> int:
    start_local = datetime.combine(now_utc().astimezone(tz).date(), time.min, tzinfo=tz)
    start_utc = start_local.astimezone(ZoneInfo("UTC"))
    rows = session.scalars(
        select(SessionRow).where(
            SessionRow.student_id == student.id, SessionRow.started_at >= start_utc
        )
    ).all()
    return sum(row.active_ms for row in rows)


def remaining_minutes(session: Session, student: StudentRow) -> int:
    used = _used_active_ms(session, student, _student_tz(session, student))
    goal = limits_for_student(student).soft_active_ms
    return max(0, int((goal - used) / 60000))


def current_offer(session: Session, student: StudentRow) -> str | None:
    """The first-run or re-offer prompt for this student, if any (see app/player/onboarding.py)."""
    from app.player.onboarding import offer_for

    base = (SessionRow.student_id == student.id, SessionRow.type != "test_out")
    total = session.scalar(select(func.count()).select_from(SessionRow).where(*base)) or 0
    ended = (
        session.scalar(
            select(func.count())
            .select_from(SessionRow)
            .where(*base, SessionRow.type == "practice", SessionRow.ended_at.is_not(None))
        )
        or 0
    )
    return offer_for(student.onboarding, total_sessions=total, ended_practice=ended)


def today_payload(session: Session, student: StudentRow) -> dict[str, Any]:
    from app.registries.quiet_hours import in_quiet_hours
    from app.registries.startup import deployment_jurisdiction_profile

    expire_stale_sessions(session, student)
    tz = _student_tz(session, student)
    profile = deployment_jurisdiction_profile()
    used = _used_active_ms(session, student, tz)
    goal_ms = limits_for_student(student).soft_active_ms
    remaining = max(0, int((goal_ms - used) / 60000))
    open_row = session.scalar(
        select(SessionRow).where(
            SessionRow.student_id == student.id,
            SessionRow.ended_at.is_(None),
            SessionRow.type != "test_out",
        )
    )
    idle_row = session.scalar(
        select(SessionRow).where(
            SessionRow.student_id == student.id,
            SessionRow.resumable.is_(True),
            SessionRow.type != "test_out",
        )
    )
    resume = open_row or idle_row
    return {
        "offer": current_offer(session, student),
        "ui": ui_for_grade(student.grade),
        "student_id": str(student.id),
        "display_name": student.display_name,
        "goal_minutes": int(goal_ms / 60000),
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
