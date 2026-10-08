"""Pure teaching policy: (learner, session, last_event) → action. No I/O."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.checkpoint.score import score_answers
from app.content.validator import item_tier
from app.learner.ladder import (
    KIND_ANSWER,
    KIND_HINT,
    KIND_LESSON,
    T_LEVEL,
    LadderEvent,
    apply_ladder_event,
)
from app.learner.mastery_service import apply_event
from app.learner.scheduler_fsrs import FixedClock
from app.learner.types import LearnerEvent, LearnerState, Mastery
from app.orchestrator.diagnosis import classify
from app.orchestrator.diagnostic import (
    is_dont_know,
    next_diagnostic_item,
    record_answer,
    seed_placement,
)
from app.orchestrator.transitions import rule_id_for
from app.orchestrator.types import (
    HARD_ACTIVE_MS,
    IDLE_END_MS,
    LATENCY_CAP_MS,
    MAX_WARMUP,
    PREREQ_BELOW,
    SOFT_ACTIVE_MS,
    SOFT_ITEM_CAP,
    Action,
    CatalogItem,
    Event,
    SessionState,
    default_params,
)
from app.verifier.check import leak_check, verify_response


def policy(learner: LearnerState, session: SessionState, last_event: Event | None) -> Action:
    from app.observe.otel import span

    before = session.phase
    if last_event is not None and last_event.type == "request_hint":
        last_event.type = "request_help"  # request_hint is kept as an alias (G2)
    session.last_event = last_event
    session.last_correct = None
    session.last_diagnosis = None
    with span("policy", component="policy", action_type=last_event.type if last_event else "start"):
        action = _policy(learner, session, last_event, before)
        if action.type == "end_session":
            _rate_session(learner, session)
        return action


def _policy(
    learner: LearnerState, session: SessionState, last_event: Event | None, before: str
) -> Action:
    if last_event and last_event.latency_ms is not None:
        session.active_ms += min(last_event.latency_ms, LATENCY_CAP_MS)
        session.last_active_at = session.now
    finishing = last_event and last_event.type == "show_solution" and session.hint_level_shown >= 2
    if last_event and last_event.type not in {"answer", "resume"} and not finishing:
        if _hard_cap(session) or _soft_cap(session):
            reason = "hard_cap" if _hard_cap(session) else "soft_cap"
            return _annotate(_end(session, reason, resumable=False), session, before, last_event)
    if session.consent_revoked or (last_event and last_event.type == "consent_revoked"):
        return _annotate(
            _end(session, "consent_revoked", resumable=False), session, before, last_event
        )
    if last_event and last_event.type == "resume":
        session.phase = "practice" if session.current_item_id else "start"
        session.ended_reason = None
        if session.last_action and session.last_action.type != "end_session":
            return _annotate(session.last_action, session, before, last_event)
        return _annotate(
            Action(type="show_item", item_id=session.current_item_id),
            session,
            before,
            last_event,
        )
    if _idle_expired(session, last_event):
        return _annotate(_end(session, "idle", resumable=True), session, before, last_event)
    if session.phase == "ended":
        return _annotate(
            Action(type="end_session", ended_reason=session.ended_reason, resumable=True),
            session,
            before,
            last_event,
        )

    if last_event and last_event.type == "idle_nudge":
        return _annotate(
            _keep(session, Action(type="nudge", item_id=session.current_item_id)),
            session,
            before,
            last_event,
        )

    if session.session_type == "diagnostic":
        action = _diagnostic(learner, session, last_event)
    elif session.session_type == "checkpoint":
        action = _checkpoint(session, last_event)
    else:
        action = _practice(learner, session, last_event)
    return _annotate(action, session, before, last_event)


def _practice(learner: LearnerState, session: SessionState, event: Event | None) -> Action:
    if event is None:
        return _enter_practice_loop(learner, session)
    if event.type == "predict_response":
        session.phase = "worked_example"
        item = session.item()
        return _keep(
            session,
            Action(
                type="worked_example",
                item_id=session.current_item_id,
                skill_id=session.current_skill,
                text=item.authored_explanation if item else "",
            ),
        )
    if event.type == "continue":
        return _on_continue(learner, session)
    if event.type == "request_help":
        return _on_hint(learner, session)
    if event.type == "stuck_choice":
        return _on_stuck_choice(learner, session, event)
    if event.type == "stuck_step":
        return _on_stuck_step(learner, session, event)
    if event.type == "show_solution":
        return _on_show_solution(learner, session)
    if event.type == "answer":
        return _on_answer(learner, session, event)
    if event.type == "explain_back":
        return _on_explain_back(session, event)
    return _enter_practice_loop(learner, session)


def _enter_practice_loop(learner: LearnerState, session: SessionState) -> Action:
    if _hard_cap(session):
        return _end(session, "hard_cap", resumable=False)
    if _soft_cap(session):
        return _end(session, "soft_cap", resumable=False)
    if not session.warmup_done:
        due = _due_skills(learner, session)
        if due:
            session.warmup_done = True
            session.warmup_left = min(MAX_WARMUP, len(due))
            return _show_warmup(learner, session, due)
        session.warmup_done = True
    return _select_skill_or_item(learner, session)


def _on_continue(learner: LearnerState, session: SessionState) -> Action:
    if session.phase == "worked_example":
        _lesson_complete(learner, session)
        return _show_practice(learner, session, session.current_skill, new_skill=False)
    if session.phase == "reveal":
        return _similar_item(learner, session)
    if session.phase == "explain_back":
        return _select_skill_or_item(learner, session)
    if session.phase in {"diagnostic", "checkpoint"}:
        session.sequence_index += 1
        if session.session_type == "diagnostic":
            return _diagnostic(learner, session, None)
        return _checkpoint(session, None)
    return _enter_practice_loop(learner, session)


def _on_hint(learner: LearnerState, session: SessionState) -> Action:
    if session.session_type != "practice":
        return _flag(session, "no_hint_in_assessment")
    item = session.item()
    if item is None:
        return _enter_practice_loop(learner, session)
    if session.phase in {"stuck", "stuck_step"}:
        return _keep(session, _stuck_point_action(session, item))
    if (
        session.stuck_item_id != item.id
        and session.last_wrong_item_id != item.id
        and session.hint_level_shown == 0
    ):
        return _ask_stuck_point(learner, session, item)
    if session.hint_level_shown >= 2:
        session.phase = "practice"
        return _keep(
            session,
            Action(type="show_item", item_id=item.id, skill_id=item.primary_skill),
        )
    return _deliver_hint(learner, session, item)


_STUCK_CHOICES = ("start", "step", "restate", "might_be_right")


def _stuck_point_action(session: SessionState, item: CatalogItem) -> Action:
    choices = [
        choice
        for choice in _STUCK_CHOICES
        if (choice != "step" or item.step_hints) and (choice != "restate" or item.hint_restate)
    ]
    return Action(
        type="ask_stuck_point",
        item_id=item.id,
        skill_id=item.primary_skill,
        extras={"choices": choices, "step_count": len(item.step_hints)},
    )


def _ask_stuck_point(learner: LearnerState, session: SessionState, item: CatalogItem) -> Action:
    """R32: ask before telling. The first help request is the item's one BKT update."""
    _maybe_bkt(learner, session, item, event_type="request_hint", correct=False)
    _maybe_ladder(learner, session, item, kind=KIND_HINT, correct=None)
    session.stuck_item_id = item.id
    session.help_without_attempt += 1
    session.phase = "stuck"
    return _keep(session, _stuck_point_action(session, item))


def _on_stuck_choice(learner: LearnerState, session: SessionState, event: Event) -> Action:
    item = session.item()
    if session.phase != "stuck" or item is None:
        return _flag(session, "not_in_stuck_picker")
    choice = (event.response or "").strip()
    offered = _stuck_point_action(session, item).extras["choices"]
    if choice not in offered:
        return _flag(session, "bad_choice")
    if choice == "start":
        if session.hint_level_shown >= 2:
            session.phase = "practice"
            return _keep(
                session, Action(type="show_item", item_id=item.id, skill_id=item.primary_skill)
            )
        return _deliver_hint(learner, session, item)
    if choice == "step":
        session.phase = "stuck_step"
        return _keep(
            session,
            Action(
                type="ask_stuck_step",
                item_id=item.id,
                skill_id=item.primary_skill,
                extras={"step_count": len(item.step_hints)},
            ),
        )
    if choice == "restate":
        session.phase = "practice"
        return _keep(
            session,
            Action(
                type="hint",
                item_id=item.id,
                skill_id=item.primary_skill,
                text=item.hint_restate,
                source="authored",
                extras={"kind": "restate"},
            ),
        )
    session.phase = "practice"
    if session.last_wrong_item_id == item.id:
        return _check_your_work(session, item, "recheck")
    return _keep(
        session,
        Action(
            type="show_item",
            item_id=item.id,
            skill_id=item.primary_skill,
            extras={"prompt_submit": True},
        ),
    )


def _on_stuck_step(learner: LearnerState, session: SessionState, event: Event) -> Action:
    item = session.item()
    if session.phase != "stuck_step" or item is None:
        return _flag(session, "not_in_stuck_picker")
    try:
        index = int((event.response or "").strip())
    except ValueError:
        return _flag(session, "bad_step")
    if not 0 <= index < len(item.step_hints):
        return _flag(session, "bad_step")
    text = item.step_hints[index]
    if leak_check(text, item.answer_sympy, level=1):
        text = item.hint(1)  # never reveal before hint 3
    session.phase = "practice"
    return _keep(
        session,
        Action(
            type="hint",
            item_id=item.id,
            skill_id=item.primary_skill,
            text=text,
            source="authored",
            extras={"kind": "step", "step": index},
        ),
    )


def _check_your_work(session: SessionState, item: CatalogItem, kind: str) -> Action:
    """R31: point at what to recheck. No hint level is used."""
    session.phase = "practice"
    return _keep(
        session,
        Action(
            type="check_your_work",
            item_id=item.id,
            skill_id=item.primary_skill,
            extras={"check_kind": kind},
        ),
    )


def _deliver_hint(learner: LearnerState, session: SessionState, item: CatalogItem) -> Action:
    level = session.hint_level_shown + 1
    text = item.hint(level)
    if leak_check(text, item.answer_sympy, level=level):
        text = item.hint(level)
    _maybe_bkt(learner, session, item, event_type="request_hint", correct=False)
    if session.last_event is not None and session.last_event.type == "request_help":
        _maybe_ladder(learner, session, item, kind=KIND_HINT, correct=None)
    session.hint_level_shown = level
    session.phase = "practice"
    misconception = _match_misconception(item, session.last_wrong_response or "")
    targeted = session.misconception_text.get(misconception or "")
    if level == 1 and targeted and not leak_check(targeted, item.answer_sympy, level=1):
        text = targeted  # the hint names the misunderstanding, not just the item (R30)
    return _keep(
        session,
        Action(
            type="hint",
            item_id=item.id,
            skill_id=item.primary_skill,
            hint_level=level,
            misconception_id=misconception,
            text=text,
            source="authored",
        ),
    )


def _on_show_solution(learner: LearnerState, session: SessionState) -> Action:
    if session.session_type != "practice":
        return _flag(session, "no_reveal_in_assessment")
    if session.hint_level_shown < 2:
        return _flag(session, "illegal_reveal")
    return _reveal(session)


def _on_answer(learner: LearnerState, session: SessionState, event: Event) -> Action:
    item = session.item(event.item_id) or session.item()
    if item is None:
        return _enter_practice_loop(learner, session)
    correct = verify_response(
        event.response or "",
        answer_sympy=item.answer_sympy,
        accept=list(item.accept),
        item_type=item.type,
        verify=item.verify,
        options=list(item.options),
    )
    if session.session_type == "practice" and item.pool != "practice":
        return _flag(session, "checkpoint_item_in_practice")
    session.last_correct = correct
    if session.session_type == "practice":
        _track_engagement(session, item, event)
        diagnosis = classify(item, event.response or "", correct, learner, session)
        session.last_diagnosis = diagnosis.as_payload()
    if session.session_type != "diagnostic":
        _maybe_bkt(learner, session, item, event_type="answer", correct=correct)
        _maybe_ladder(learner, session, item, kind=KIND_ANSWER, correct=correct)
    if session.session_type == "diagnostic":
        record_answer(session, item, correct=correct, dont_know=is_dont_know(event.response))
        return _diagnostic(learner, session, None)
    if session.session_type == "checkpoint":
        session.checkpoint_answers.append(
            {
                "item_id": item.id,
                "skill_id": item.primary_skill,
                "correct": correct,
                "response": event.response,
            }
        )
        session.items_completed += 1
        session.sequence_index += 1
        return _checkpoint(session, None)

    if correct:
        session.items_completed += 1
        session.shown_item_ids.append(item.id)
        if session.phase == "warmup":
            return _select_skill_or_item(learner, session)
        return _after_correct(learner, session, item)
    first_attempt = session.last_wrong_item_id != item.id
    session.last_wrong_response = event.response or ""
    session.last_wrong_item_id = item.id
    if (
        first_attempt
        and session.hint_level_shown == 0
        and session.last_diagnosis is not None
        and session.last_diagnosis["class"] == "slip"
    ):
        return _check_your_work(session, item, str(session.last_diagnosis["detail"]))
    if session.hint_level_shown >= 2:
        session.attempt_after_hint2 = True
        return _reveal(session)
    return _deliver_hint(learner, session, item)


def _track_engagement(session: SessionState, item: CatalogItem, event: Event) -> None:
    """Counters behind the disengagement class (R35): fast answers and help without an attempt."""
    fast = (
        event.latency_ms is not None
        and item.min_plausible_ms is not None
        and event.latency_ms < item.min_plausible_ms
    )
    session.fast_streak = session.fast_streak + 1 if fast else 0
    session.help_without_attempt = 0


def _after_correct(learner: LearnerState, session: SessionState, item: CatalogItem) -> Action:
    skill = item.primary_skill
    mastery = learner.mastery.get(skill)
    first_unhinted = (
        mastery is not None
        and mastery.unhinted_correct >= 1
        and session.hint_level_shown == 0
        and skill not in session.explain_back_done
    )
    reached = mastery is not None and mastery.mastered and skill not in session.explain_back_done
    if first_unhinted or reached:
        session.phase = "explain_back"
        session.explain_back_done.add(skill)
        return _keep(
            session,
            Action(
                type="explain_back_prompt",
                item_id=item.id,
                skill_id=skill,
                text=item.authored_explanation,
            ),
        )
    return _select_skill_or_item(learner, session)


def _on_explain_back(session: SessionState, event: Event) -> Action:
    session.stored_explain_text = event.text or event.response
    item = session.item()
    session.phase = "select_skill"
    return _keep(
        session,
        Action(
            type="explain_back_result",
            item_id=session.current_item_id,
            skill_id=session.current_skill,
            text=item.authored_explanation if item else "",
            grade=None,
            store_text=True,
            llm_called=False,
        ),
    )


def _reveal(session: SessionState) -> Action:
    item = session.item()
    assert item is not None
    lead = item.hint(3)
    body = " ".join(item.solution_steps)
    session.phase = "reveal"
    session.similar_from_item_id = item.id
    return _keep(
        session,
        Action(
            type="reveal_solution",
            item_id=item.id,
            skill_id=item.primary_skill,
            text=f"{lead} {body}".strip(),
            extras={"hint3": lead},
        ),
    )


def _similar_item(learner: LearnerState, session: SessionState) -> Action:
    source = session.item(session.similar_from_item_id) or session.item()
    if source is None:
        return _select_skill_or_item(learner, session)
    wanted = item_tier(source.difficulty)
    nxt = _pick_item(
        session,
        source.primary_skill,
        p_known=source.difficulty,
        exclude={source.id},
        prefer_tier=wanted,
        roles=(source.role,),
    )
    if nxt is None:
        return _content_gap(learner, session, source.primary_skill, wanted)
    session.current_item_id = nxt.id
    session.current_skill = nxt.primary_skill
    session.hint_level_shown = 0
    session.attempt_after_hint2 = False
    session.phase = "practice"
    session.shown_item_ids.append(nxt.id)
    return _keep(
        session,
        Action(type="similar_item", item_id=nxt.id, skill_id=nxt.primary_skill),
    )


def _select_skill_or_item(learner: LearnerState, session: SessionState) -> Action:
    if _hard_cap(session) or _soft_cap(session):
        reason = "hard_cap" if _hard_cap(session) else "soft_cap"
        return _end(session, reason, resumable=False)
    if session.warmup_left > 0:
        due = _due_skills(learner, session)
        if due:
            return _show_warmup(learner, session, due)
        session.warmup_left = 0
    skill = _choose_skill(learner, session)
    if skill is None:
        return _end(session, "chapter_complete", resumable=False)
    session.current_skill = skill
    if skill not in session.introduced_skills and skill not in _shown_skills(learner):
        session.phase = "predict"
        return _keep(
            session,
            Action(
                type="predict",
                skill_id=skill,
                item_id=None,
                text=_prediction_for(session, skill),
            ),
        )
    return _show_practice(learner, session, skill, new_skill=False)


def _show_practice(
    learner: LearnerState, session: SessionState, skill: str | None, *, new_skill: bool
) -> Action:
    if skill is None:
        return _end(session, "chapter_complete", resumable=False)
    wanted = item_tier(_p_known(learner, skill, session))
    roles, required = _roles_for(learner, session, skill)
    item = _pick_item(session, skill, p_known=_p_known(learner, skill, session), roles=roles)
    if item is None:
        return _content_gap(learner, session, skill, wanted)
    if required and item.role != roles[0]:
        _log_role_gap(session, skill, roles[0], wanted)
    session.introduced_skills.add(skill)
    session.current_skill = skill
    session.current_item_id = item.id
    session.hint_level_shown = 0
    session.attempt_after_hint2 = False
    session.phase = "practice"
    session.shown_item_ids.append(item.id)
    return _keep(session, Action(type="show_item", item_id=item.id, skill_id=skill))


def _show_warmup(learner: LearnerState, session: SessionState, due: list[str]) -> Action:
    skill = due[0]
    item = _pick_item(
        session,
        skill,
        p_known=_p_known(learner, skill, session),
        roles=_warmup_roles(learner, skill),
    )
    if item is None:
        session.warmup_left = 0
        return _select_skill_or_item(learner, session)
    session.warmup_left = max(0, session.warmup_left - 1)
    session.current_skill = skill
    session.current_item_id = item.id
    session.phase = "warmup"
    session.shown_item_ids.append(item.id)
    return _keep(
        session,
        Action(type="warmup_item", item_id=item.id, skill_id=skill, extras={"warmup": True}),
    )


def _diagnostic(learner: LearnerState, session: SessionState, event: Event | None) -> Action:
    blocked = {"request_help", "request_hint", "show_solution", "explain_back", "predict_response"}
    if event and event.type in blocked:
        return _flag(session, "no_hint_in_assessment")
    if event and event.type == "answer":
        return _on_answer(learner, session, event)
    item = next_diagnostic_item(session)
    if item is None:
        seed_placement(learner, session)
        action = _end(session, "diagnostic_complete", resumable=False)
        action.extras = {
            "skills_not_tested": list(session.skills_not_tested),
            "skipped_skills": sorted(session.skipped_skills),
        }
        return action
    session.current_item_id = item.id
    session.current_skill = item.primary_skill
    session.phase = "diagnostic"
    session.shown_item_ids.append(item.id)
    extras: dict = {"assessment": True, "dont_know_option": True}
    return _keep(
        session,
        Action(
            type="show_item",
            item_id=item.id,
            skill_id=item.primary_skill,
            extras=extras,
        ),
    )


def _checkpoint(session: SessionState, event: Event | None) -> Action:
    if event and event.type in {"request_help", "request_hint", "show_solution", "explain_back"}:
        return _flag(session, "no_hint_in_assessment")
    ids = session.checkpoint_ids or [row.id for row in session.catalog if row.pool == "checkpoint"]
    if event and event.type == "answer":
        # scored only; mastery/FSRS not updated (policy never calls apply_event here)
        item = session.item(event.item_id) or session.item()
        if item is not None:
            verify_response(
                event.response or "",
                answer_sympy=item.answer_sympy,
                accept=list(item.accept),
                item_type=item.type,
                verify=item.verify,
                options=list(item.options),
            )
        session.items_completed += 1
        session.sequence_index += 1
    if session.sequence_index >= len(ids):
        session.phase = "ended"
        session.ended_reason = "checkpoint_complete"
        result = score_answers(session.checkpoint_answers)
        session.checkpoint_result = result
        return _keep(
            session,
            Action(
                type="checkpoint_score",
                ended_reason="checkpoint_complete",
                extras=result,
            ),
        )
    item = session.item(ids[session.sequence_index])
    session.current_item_id = item.id if item else None
    session.phase = "checkpoint"
    return _keep(
        session,
        Action(
            type="show_item",
            item_id=session.current_item_id,
            skill_id=item.primary_skill if item else None,
            extras={"assessment": True},
        ),
    )


def _ladder_level(learner: LearnerState, skill_id: str) -> int:
    row = learner.ladders.get(skill_id)
    return row.level if row else 0


def _choose_skill(learner: LearnerState, session: SessionState) -> str | None:
    """T = first overlay skill below ladder level 4.

    With no such skill: extension practice (level 4 -> apply, 5 -> transfer) on the first skill
    that still has a role to earn, otherwise None (chapter complete).
    """
    target = None
    for skill_id in session.overlay_skill_ids:
        if skill_id in session.blocked_skills:
            continue
        if _ladder_level(learner, skill_id) < T_LEVEL:
            target = skill_id
            break
    if target is None:
        return _extension_skill(learner, session)
    weak = [
        sid
        for sid in session.prerequisites.get(target, ())
        if _p_known(learner, sid, session) < PREREQ_BELOW
    ]
    if weak:
        return min(weak, key=lambda sid: (_p_known(learner, sid, session), sid))
    return target


_EXTENSION_ROLE = {4: "apply", 5: "transfer"}


def _extension_skill(learner: LearnerState, session: SessionState) -> str | None:
    for skill_id in session.overlay_skill_ids:
        if skill_id in session.blocked_skills:
            continue
        role = _EXTENSION_ROLE.get(_ladder_level(learner, skill_id))
        if role is None:
            continue
        if any(row.role == role for row in _eligible_items(session, skill_id, set())):
            session.introduced_skills.add(skill_id)  # already learned: no predict / worked example
            return skill_id
        _log_role_gap(session, skill_id, role, item_tier(_p_known(learner, skill_id, session)))
    return None


def _roles_for(
    learner: LearnerState, session: SessionState, skill: str
) -> tuple[tuple[str, ...], bool]:
    """Preferred roles (first is the target) and whether a miss is a content gap.

    Level 4 -> apply, level 5 -> transfer, otherwise procedure; until level 2 is reached a
    recall / explain item is mixed in on every second and fourth item of the skill.
    """
    ladder = learner.ladders.get(skill)
    level = ladder.level if ladder else 0
    if level == 4:
        return ("apply", "procedure"), True
    if level == 5:
        return ("transfer", "procedure"), True
    if 2 not in (ladder.achieved if ladder else []) and level < T_LEVEL:
        shown = sum(
            1
            for item_id in session.shown_item_ids
            if (row := session.item(item_id)) is not None and row.primary_skill == skill
        )
        slot = shown % 4
        if slot == 1:
            return ("recall", "procedure"), False
        if slot == 3:
            return ("explain", "procedure"), False
    return ("procedure",), True


def _warmup_roles(learner: LearnerState, skill: str) -> tuple[str, ...]:
    level = _ladder_level(learner, skill)
    if level == 4:
        return ("apply", "procedure")
    if level == 5:
        return ("transfer", "procedure")
    return ("procedure",)


def _log_role_gap(session: SessionState, skill: str, role: str, tier: str) -> None:
    if any(g.get("skill") == skill and g.get("role") == role for g in session.content_gaps):
        return
    session.content_gaps.append(
        {
            "skill": skill,
            "tier": tier,
            "role": role,
            "item_ids_seen": list(session.shown_item_ids),
            "reason": "role_missing",
        }
    )


def _content_gap(learner: LearnerState, session: SessionState, skill: str, tier: str) -> Action:
    seen = [item_id for item_id in session.shown_item_ids]
    gap = {"skill": skill, "tier": tier, "item_ids_seen": seen}
    session.content_gaps.append(gap)
    session.blocked_skills.add(skill)
    session.phase = "start"
    action = Action(
        type="content_gap",
        skill_id=skill,
        extras=gap,
    )
    session.last_action = action
    follow = _select_skill_or_item(learner, session)
    follow.extras = {**follow.extras, "content_gap": gap}
    if follow.type == "end_session" and not session.overlay_skill_ids:
        return follow
    return follow


def _eligible_items(session: SessionState, skill: str, skip: set[str]) -> list[CatalogItem]:
    return [
        row
        for row in session.catalog
        if row.pool == "practice"
        and row.primary_skill == skill
        and row.id not in skip
        and row.status != "retired"
        and (row.status == "approved" or session.allow_draft)
    ]


def _pick_item(
    session: SessionState,
    skill: str,
    *,
    p_known: float,
    exclude: set[str] | None = None,
    prefer_tier: str | None = None,
    roles: tuple[str, ...] = (),
) -> CatalogItem | None:
    wanted = prefer_tier or item_tier(p_known)
    eligible = _eligible_items(session, skill, exclude or set())
    for role in roles:  # first role with an eligible item; otherwise any eligible role
        role_rows = [row for row in eligible if row.role == role]
        if role_rows:
            eligible = role_rows
            break
    leftover = [row for row in eligible if row.id not in session.shown_item_ids]
    pool = leftover or eligible
    if not pool:
        return None
    in_tier = [row for row in pool if item_tier(row.difficulty) == wanted]
    chosen_pool = in_tier or _nearest_tier(pool, wanted)
    chosen_pool.sort(key=lambda row: (_shown_key(row), row.difficulty, row.id))
    return chosen_pool[0]


def _nearest_tier(pool: list[CatalogItem], wanted: str) -> list[CatalogItem]:
    order = ["easy", "medium", "hard"]
    idx = order.index(wanted) if wanted in order else 1
    neighbors = []
    if idx > 0:
        neighbors.append(order[idx - 1])
    if idx + 1 < len(order):
        neighbors.append(order[idx + 1])
    if idx == 2:
        neighbors.append("easy")
    for tier in neighbors:
        rows = [row for row in pool if item_tier(row.difficulty) == tier]
        if rows:
            return rows
    return pool


def _shown_key(item: CatalogItem) -> tuple[int, datetime]:
    if item.last_shown_at is None:
        return (0, datetime.min)
    return (1, item.last_shown_at)


def _p_known(learner: LearnerState, skill_id: str, session: SessionState) -> float:
    row = learner.mastery.get(skill_id)
    if row is not None:
        return row.p_known
    return session.bkt_params.get(skill_id, default_params()).p_init


def _shown_skills(learner: LearnerState) -> set[str]:
    extras = getattr(learner, "practice_shown_skills", None)
    return set(extras) if extras else set()


def _due_skills(learner: LearnerState, session: SessionState) -> list[str]:
    due = []
    for skill_id, card in learner.cards.items():
        if card.due_at <= session.now:
            due.append(skill_id)
    return due[:MAX_WARMUP]


def _maybe_bkt(
    learner: LearnerState,
    session: SessionState,
    item: CatalogItem,
    *,
    event_type: str,
    correct: bool,
) -> None:
    if session.session_type in {"checkpoint", "diagnostic"}:
        return
    params = {
        sid: session.bkt_params.get(sid, default_params())
        for sid in {item.primary_skill, *session.overlay_skill_ids}
    }
    apply_event(
        learner,
        LearnerEvent(
            item_id=item.id,
            skill_id=item.primary_skill,
            event_type=event_type,
            correct=correct,
            pool="warmup" if session.phase == "warmup" else session.session_type,
            session_id=_session_key(session),
            is_warmup=session.phase == "warmup",
        ),
        params,
        memory=session.bkt_memory,
    )


def _event_id(session: SessionState) -> str:
    event = session.last_event
    if event is not None and event.event_id:
        return event.event_id
    session.event_counter += 1
    return f"auto-{session.event_counter}"


def _maybe_ladder(
    learner: LearnerState,
    session: SessionState,
    item: CatalogItem,
    *,
    kind: str,
    correct: bool | None,
) -> None:
    """Ladder evidence comes only from practice sessions; diagnostic, checkpoint and explain-back
    never reach it."""
    if session.session_type != "practice":
        return
    skill = item.primary_skill
    row = learner.mastery.get(skill)
    p_known = row.p_known if row is not None else _p_known(learner, skill, session)
    apply_ladder_event(
        learner.ladders,
        LadderEvent(
            event_id=_event_id(session),
            skill_id=skill,
            kind=kind,
            at=session.now,
            item_id=item.id,
            correct=correct,
            pool="warmup" if session.phase == "warmup" else "practice",
            role=item.role,
            structure=item.structure,
        ),
        p_known,
    )


def _lesson_complete(learner: LearnerState, session: SessionState) -> None:
    skill = session.current_skill
    if skill is None or session.session_type != "practice":
        return
    params = session.bkt_params.get(skill, default_params())
    learner.mastery.setdefault(skill, Mastery(skill_id=skill, p_known=params.p_init))
    apply_ladder_event(
        learner.ladders,
        LadderEvent(
            event_id=_event_id(session),
            skill_id=skill,
            kind=KIND_LESSON,
            at=session.now,
        ),
        p_known=0.0,
    )


def _session_key(session: SessionState) -> str:
    return session.session_key or str(id(session))


def _rate_session(learner: LearnerState, session: SessionState) -> None:
    """One FSRS rating per practised skill at session end, from the unhinted-correct rate.

    Skills reviewed as warm-ups were already rated immediately. The per-session counts are
    cleared afterwards, so a resumed session that ends again only rates its new answers.
    """
    if session.session_type != "practice" or session.ended_reason == "consent_revoked":
        return
    key = _session_key(session)
    apply_event(
        learner,
        LearnerEvent(item_id="", skill_id="", event_type="session_end", session_id=key),
        {},
        clock=FixedClock(session.now),
        memory=session.bkt_memory,
    )
    session.bkt_memory["session_unhinted"].pop(key, None)


def _seed_diagnostic(learner: LearnerState, session: SessionState) -> None:
    seed_placement(learner, session)


def _match_misconception(item: CatalogItem, response: str) -> str | None:
    text = response.strip()
    for mid, answers in item.misconception_rules:
        if text in answers:
            return mid
    return None


def _prediction_for(session: SessionState, skill: str) -> str:
    for row in session.catalog:
        if row.primary_skill == skill and row.prediction_prompt:
            return row.prediction_prompt
    return "What do you think the first step is?"


def _idle_expired(session: SessionState, event: Event | None) -> bool:
    if event and event.idle_ms is not None and event.idle_ms >= IDLE_END_MS:
        return True
    if session.last_active_at is None:
        return False
    return session.now - session.last_active_at >= timedelta(milliseconds=IDLE_END_MS)


def _soft_cap(session: SessionState) -> bool:
    return session.active_ms >= SOFT_ACTIVE_MS or session.items_completed >= SOFT_ITEM_CAP


def _hard_cap(session: SessionState) -> bool:
    return session.active_ms >= HARD_ACTIVE_MS


def _end(session: SessionState, reason: str, *, resumable: bool) -> Action:
    session.phase = "ended"
    session.ended_reason = reason
    action = Action(
        type="end_session",
        ended_reason=reason,
        resumable=resumable,
        llm_called=False,
    )
    return _keep(session, action)


def _flag(session: SessionState, flag: str) -> Action:
    action = Action(
        type=session.last_action.type if session.last_action else "show_item",
        item_id=session.current_item_id,
        skill_id=session.current_skill,
        guardrail_flag=flag,
        rejected=True,
        llm_called=False,
    )
    return _keep(session, action)


def _keep(session: SessionState, action: Action) -> Action:
    session.last_action = action
    session.llm_called = session.llm_called or action.llm_called
    return action


def _annotate(action: Action, session: SessionState, before: str, event: Event | None) -> Action:
    ev = event.type if event else "start"
    action.state_before = before
    action.state_after = session.phase
    action.rule_id = action.rule_id or rule_id_for(before, ev, action.type)
    session.last_action = action
    return action
