"""Pure teaching policy: (learner, session, last_event) → action. No I/O."""

from __future__ import annotations

from dataclasses import dataclass
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
from app.orchestrator.diagnosis import FAST_STREAK_LIMIT, HELP_WITHOUT_ATTEMPT_LIMIT, classify
from app.orchestrator.diagnostic import (
    is_dont_know,
    next_diagnostic_item,
    record_answer,
    seed_placement,
)
from app.orchestrator.encouragement import pick_variant
from app.orchestrator.transitions import rule_id_for
from app.orchestrator.types import (
    IDLE_END_MS,
    LATENCY_CAP_MS,
    MAX_WARMUP,
    PREREQ_BELOW,
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
            return _annotate(_end_for_cap(learner, session, reason), session, before, last_event)
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
    if event.type == "break_choice":
        return _on_break_choice(learner, session, event)
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
        return _end_for_cap(learner, session, "hard_cap")
    if _soft_cap(session):
        return _end_for_cap(learner, session, "soft_cap")
    if not session.warmup_done:
        due = _due_skills(learner, session)
        if due:
            session.warmup_done = True
            session.warmup_left = min(MAX_WARMUP, len(due))
            return _show_warmup(learner, session, due)
        session.warmup_done = True
    return _select_skill_or_item(learner, session)


def _on_continue(learner: LearnerState, session: SessionState) -> Action:
    if session.phase == "representation":
        target = session.probe_for or session.current_skill
        session.probe_for = None
        return _show_practice(learner, session, target, new_skill=False)
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
    if session.phase == "probe":
        return _flag(session, "no_help_in_probe")
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
    _note_item_seen(session, item)
    session.stuck_item_id = item.id
    session.help_without_attempt += 1
    if session.help_without_attempt >= HELP_WITHOUT_ATTEMPT_LIMIT:
        return _offer_break(session)  # R35: help opened without an attempt three times
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
    """Answer entry point: probe answers, bookkeeping, then the G2b rules around the base flow."""
    item = session.item(event.item_id) or session.item()
    if item is None or session.session_type != "practice":
        return _on_answer_base(learner, session, event)
    if session.phase == "probe" and item.primary_skill == session.probe_skill:
        return _answer_probe(learner, session, item, event)
    first_answer = item.id not in session.answered_items
    hinted = (
        session.hint_level_shown > 0
        or session.stuck_item_id == item.id
        or session.last_wrong_item_id == item.id
    )
    tier_before = item_tier(item.difficulty)
    action = _on_answer_base(learner, session, event)
    if action.rejected or session.last_correct is None:
        return action
    correct = bool(session.last_correct)
    session.last_failure = not correct
    if first_answer:
        _note_first_answer(session, item, correct)
    return _apply_g2b_rules(
        learner,
        session,
        item,
        action,
        _Outcome(first=first_answer, correct=correct, hinted=hinted, tier=tier_before),
    )


def _on_answer_base(learner: LearnerState, session: SessionState, event: Event) -> Action:
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
        # the item is finished: if it is shown again it is a fresh presentation (picker, slip path)
        session.last_wrong_item_id = None
        session.stuck_item_id = None
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


WHEEL_WRONG_STREAK = 3  # R34: consecutive wrong first attempts on one skill
WHEEL_ITEM_LIMIT = 10  # R34: items on one skill in a session without reaching level 4


def _note_item_seen(session: SessionState, item: CatalogItem) -> None:
    if item.id not in session.seen_items:
        session.seen_items.add(item.id)
        skill = item.primary_skill
        session.skill_items[skill] = session.skill_items.get(skill, 0) + 1


def _note_first_answer(session: SessionState, item: CatalogItem, correct: bool) -> None:
    """First answer on an item: it is seen, and it extends or resets the wrong-first-attempt run."""
    session.answered_items.add(item.id)
    _note_item_seen(session, item)
    skill = item.primary_skill
    session.wrong_first_streak[skill] = (
        0 if correct else session.wrong_first_streak.get(skill, 0) + 1
    )


def _wheel_spinning(learner: LearnerState, session: SessionState, skill: str) -> bool:
    if skill in session.wheel_skills or _ladder_level(learner, skill) >= T_LEVEL:
        return False
    return (
        session.wrong_first_streak.get(skill, 0) >= WHEEL_WRONG_STREAK
        or session.skill_items.get(skill, 0) >= WHEEL_ITEM_LIMIT
    )


@dataclass(frozen=True)
class _Outcome:
    """What the student just did on an item, captured before the base flow moved on."""

    first: bool  # the first answer on this item
    correct: bool
    hinted: bool  # help, a stuck-point choice or an earlier wrong answer came first
    tier: str  # tier of the item that was answered


def _apply_g2b_rules(
    learner: LearnerState,
    session: SessionState,
    item: CatalogItem,
    action: Action,
    outcome: _Outcome,
) -> Action:
    """Rules around the base answer flow: R35 break, R34/R33 wheel and probe, R36, R37, praise."""
    skill = item.primary_skill
    _update_runs(session, skill, outcome)
    if session.fast_streak >= FAST_STREAK_LIMIT and action.type in _BREAK_REPLACES:
        return _offer_break(session)
    reason: str | None = None
    if _wheel_spinning(learner, session, skill):
        session.wheel_skills.add(skill)
        reason = "wheel_spinning"
        if session.teacher_share:
            session.alerts.append({"skill_id": skill, "type": "wheel_spinning"})
    diagnosis = session.last_diagnosis or {}
    if diagnosis.get("class") == "prerequisite_gap" and diagnosis.get("detail"):
        reason = reason or "prerequisite_gap"
    if reason is not None and action.type in _PROBE_REPLACES:
        prereq = diagnosis.get("detail") if reason == "prerequisite_gap" else None
        probe = _start_probe(learner, session, skill, prereq)
        if probe is not None:
            return probe
    action = _challenge_or_tier_up(learner, session, item, action, outcome)
    return _maybe_praise(session, item, action, outcome)


_BREAK_REPLACES = frozenset(
    {
        "hint",
        "show_item",
        "similar_item",
        "explain_back_prompt",
        "check_your_work",
        "predict",
        "warmup_item",
        "reveal_solution",  # a guesser who also misses the last hint is offered the break first
    }
)
FRUSTRATION_REVEALS = 2  # R36
FRUSTRATION_WRONG_RUN = 3  # R36
STEP_DOWN_ITEMS = 2  # R36
CHALLENGE_RUN = 3  # R37
PRAISE_GAP_ITEMS = 3  # encouragement is never on consecutive items
_TIERS = ("easy", "medium", "hard")


def _update_runs(session: SessionState, skill: str, outcome: _Outcome) -> None:
    """Counters behind R36 (frustration) and R37 (challenge) and the recovery trigger."""
    if outcome.first:
        session.wrong_run = 0 if outcome.correct else session.wrong_run + 1
        if outcome.correct:
            session.skill_failed.discard(skill) if outcome.tier == "easy" else None
        else:
            session.skill_failed.add(skill)
    unhinted_correct = outcome.first and outcome.correct and not outcome.hinted
    session.unhinted_run = session.unhinted_run + 1 if unhinted_correct else 0
    if (
        session.reveals >= FRUSTRATION_REVEALS or session.wrong_run >= FRUSTRATION_WRONG_RUN
    ) and session.tier_down_items == 0:
        session.tier_down_items = STEP_DOWN_ITEMS  # acknowledge, step down, give a win (R36)
        session.reveals = 0
        session.wrong_run = 0


def _effective_tier(session: SessionState, wanted: str) -> str:
    """Apply a pending step-down (R36) or step-up (R37) to the tier of the next item."""
    index = _TIERS.index(wanted) if wanted in _TIERS else 1
    if session.tier_down_items > 0:
        session.tier_down_items -= 1
        index = max(0, index - 1)
    elif session.tier_up_next:
        session.tier_up_next = False
        index = min(len(_TIERS) - 1, index + 1)
    return _TIERS[index]


def _offer_break(session: SessionState) -> Action:
    """R35: offer a break or a different activity. Calm, never accusatory (copy is in the UI)."""
    session.fast_streak = 0
    session.help_without_attempt = 0
    session.phase = "break_choice"
    action = Action(
        type="break_or_switch",
        item_id=session.current_item_id,
        skill_id=session.current_skill,
        extras={"choices": ["break", "switch", "continue"]},
    )
    action.rule_id = "R35"
    return _keep(session, action)


def _on_break_choice(learner: LearnerState, session: SessionState, event: Event) -> Action:
    if session.phase != "break_choice":
        return _flag(session, "not_in_break_choice")
    choice = (event.response or "").strip()
    if choice not in {"break", "switch", "continue"}:
        return _flag(session, "bad_choice")
    session.phase = "practice"
    item = session.item()
    if choice == "break":
        return _end(session, "break", resumable=True)
    if choice == "switch" and session.current_skill:
        skill = session.current_skill
        session.blocked_skills.add(skill)
        nxt = _select_skill_or_item(learner, session)
        if not (nxt.type == "end_session" and nxt.ended_reason == "chapter_complete"):
            return nxt
        session.blocked_skills.discard(skill)  # nothing else to switch to: stay
        session.phase = "practice"
        session.ended_reason = None
    if item is None:
        return _enter_practice_loop(learner, session)
    return _keep(session, Action(type="show_item", item_id=item.id, skill_id=item.primary_skill))


def _challenge_or_tier_up(
    learner: LearnerState,
    session: SessionState,
    item: CatalogItem,
    action: Action,
    outcome: _Outcome,
) -> Action:
    """R37: after three unhinted correct first attempts step the tier up; at hard, a challenge."""
    if session.unhinted_run < CHALLENGE_RUN:
        return action
    session.unhinted_run = 0
    if outcome.tier != "hard":
        session.tier_up_next = True
        if action.type == "show_item" and not action.extras:
            if session.shown_item_ids and session.shown_item_ids[-1] == action.item_id:
                session.shown_item_ids.pop()  # re-pick one tier higher
            return _show_practice(learner, session, item.primary_skill, new_skill=False)
        return action
    if action.type not in {"show_item", "explain_back_prompt"}:
        return action
    challenge = _challenge_item(learner, session, item.primary_skill)
    return challenge or action


def _challenge_item(learner: LearnerState, session: SessionState, skill: str) -> Action | None:
    """A transfer item on the skill, or an interleaved item from another skill in the chapter."""
    picked = _pick_item(session, skill, p_known=0.9, prefer_tier="hard", roles=("transfer",))
    if picked is None or picked.role != "transfer":
        for other in session.overlay_skill_ids:
            if other == skill or other in session.blocked_skills:
                continue
            picked = _pick_item(
                session, other, p_known=0.9, prefer_tier="hard", roles=("transfer",)
            )
            if picked is not None:
                break
    if picked is None:
        return None
    session.current_skill = picked.primary_skill
    session.current_item_id = picked.id
    session.hint_level_shown = 0
    session.attempt_after_hint2 = False
    session.phase = "practice"
    session.shown_item_ids.append(picked.id)
    action = Action(
        type="show_item",
        item_id=picked.id,
        skill_id=picked.primary_skill,
        extras={"challenge": True},
    )
    action.rule_id = "R37"
    return _keep(session, action)


def _maybe_praise(
    session: SessionState, item: CatalogItem, action: Action, outcome: _Outcome
) -> Action:
    """Encouragement only on a trigger, never after an easy item, never on consecutive items."""
    if not (outcome.first and outcome.correct) or outcome.tier == "easy":
        return action
    if session.items_completed - session.last_praise_at < PRAISE_GAP_ITEMS:
        return action
    trigger: str | None = None
    if outcome.tier == "hard" and not outcome.hinted:
        trigger = "hard_success"
    elif item.primary_skill in session.skill_failed:
        trigger = "recovery"
    session.skill_failed.discard(item.primary_skill)
    if trigger is None or action.type == "end_session":
        return action
    return _attach_praise(session, action, trigger)


def _attach_praise(session: SessionState, action: Action, trigger: str) -> Action:
    action.extras = {
        **(action.extras or {}),
        "encouragement": {
            "trigger": trigger,
            "variant": pick_variant(trigger, session.praise_count),
        },
    }
    session.last_praise_at = session.items_completed
    session.praise_count += 1
    return action


def _serve_win(learner: LearnerState, session: SessionState) -> Action | None:
    """R40: one short item likely to succeed before a cap ends the session after a failure."""
    skills = [s for s in [session.current_skill, *session.overlay_skill_ids] if s]
    for skill in dict.fromkeys(skills):
        item = _pick_item(session, skill, p_known=0.0, prefer_tier="easy", roles=("procedure",))
        if item is not None:
            break
    else:
        return None
    session.win_served = True
    session.phase = "practice"
    session.current_skill = item.primary_skill
    session.current_item_id = item.id
    session.hint_level_shown = 0
    session.attempt_after_hint2 = False
    session.shown_item_ids.append(item.id)
    action = Action(
        type="show_item",
        item_id=item.id,
        skill_id=item.primary_skill,
        extras={"win": True},
    )
    action.rule_id = "R40"
    return _keep(session, action)


def _end_for_cap(learner: LearnerState, session: SessionState, reason: str) -> Action:
    """A cap ended the session: after a failure one likely-success item comes first (R40)."""
    if session.last_failure and not session.win_served:
        win = _serve_win(learner, session)
        if win is not None:
            return win
    action = _end(session, reason, resumable=False)
    if not session.last_failure:
        _attach_praise(session, action, "session_end")
    return action


# actions the probe may replace: the next step of the item the student just answered
_PROBE_REPLACES = frozenset(
    {"hint", "show_item", "similar_item", "explain_back_prompt", "check_your_work"}
)


def _lowest_mastery_prerequisite(
    learner: LearnerState, session: SessionState, target: str
) -> str | None:
    candidates = [
        sid
        for sid in session.prerequisites.get(target, ())
        if sid not in session.probe_done
        and any(row.primary_skill == sid for row in _eligible_items(session, sid, set()))
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda sid: (_p_known(learner, sid, session), sid))


def _start_probe(
    learner: LearnerState, session: SessionState, target: str, prereq: str | None
) -> Action | None:
    """R33: one practice item on the prerequisite; none to probe means a new representation."""
    if prereq is not None and prereq in session.probe_done:
        return None
    chosen = prereq or _lowest_mastery_prerequisite(learner, session, target)
    item = (
        _pick_item(
            session,
            chosen,
            p_known=_p_known(learner, chosen, session),
            prefer_tier="easy",
            roles=("procedure",),
        )
        if chosen
        else None
    )
    if chosen is None or item is None:
        return _change_representation(session, target)
    session.probe_done.add(chosen)
    session.probe_skill, session.probe_for = chosen, target
    session.phase = "probe"
    session.current_skill = chosen
    session.current_item_id = item.id
    session.hint_level_shown = 0
    session.attempt_after_hint2 = False
    session.shown_item_ids.append(item.id)
    action = Action(
        type="show_item",
        item_id=item.id,
        skill_id=chosen,
        extras={"probe": True, "for_skill": target},
    )
    action.rule_id = "R33"
    return _keep(session, action)


def _change_representation(session: SessionState, target: str) -> Action:
    """Show the target skill in a different way: its worked example (no lesson credit)."""
    session.phase = "representation"
    session.probe_for = target
    session.current_skill = target
    current = session.item()
    if current is None or current.primary_skill != target:
        current = next((row for row in session.catalog if row.primary_skill == target), None)
        session.current_item_id = current.id if current else None
    action = Action(
        type="worked_example",
        item_id=session.current_item_id,
        skill_id=target,
        text=current.authored_explanation if current else "",
        extras={"representation_change": True},
    )
    action.rule_id = "R33"
    return _keep(session, action)


def _answer_probe(
    learner: LearnerState, session: SessionState, item: CatalogItem, event: Event
) -> Action:
    correct = verify_response(
        event.response or "",
        answer_sympy=item.answer_sympy,
        accept=list(item.accept),
        item_type=item.type,
        verify=item.verify,
        options=list(item.options),
    )
    session.last_correct = correct
    session.last_diagnosis = None
    _maybe_bkt(learner, session, item, event_type="answer", correct=correct)
    _maybe_ladder(learner, session, item, kind=KIND_ANSWER, correct=correct)
    session.items_completed += 1
    session.answered_items.add(item.id)
    _note_item_seen(session, item)
    prereq, target = session.probe_skill, session.probe_for
    session.probe_skill = None
    if correct and target:
        return _change_representation(
            session, target
        )  # the prerequisite is fine: teach T differently
    session.probe_for = None
    session.phase = "practice"
    if prereq:
        session.scheduled_prereq, session.scheduled_left = prereq, 2  # prerequisite next, T later
    return _select_skill_or_item(learner, session)


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
    session.reveals += 1
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
    wanted = _effective_tier(session, item_tier(source.difficulty))
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
        return _end_for_cap(learner, session, reason)
    if session.warmup_left > 0:
        due = _due_skills(learner, session)
        if due:
            return _show_warmup(learner, session, due)
        session.warmup_left = 0
    stretch = _stretch_skill(learner, session)
    if stretch is not None:
        session.stretch_served += 1
        session.stretch_skills.add(stretch)
        session.introduced_skills.add(stretch)  # already learned: no predict / worked example
        return _show_practice(learner, session, stretch, new_skill=False)
    skill = _choose_skill(learner, session)
    if skill is None:
        done = _end(session, "chapter_complete", resumable=False)
        if not session.last_failure:
            _attach_praise(session, done, "session_end")
        return done
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
    shifted = _effective_tier(session, wanted)
    item = _pick_item(
        session,
        skill,
        p_known=_p_known(learner, skill, session),
        roles=roles,
        prefer_tier=shifted if shifted != wanted else None,
    )
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
    scheduled = session.scheduled_prereq
    if scheduled and session.scheduled_left > 0:
        session.scheduled_left -= 1
        if session.scheduled_left == 0:
            session.scheduled_prereq = None
        return scheduled
    session.scheduled_prereq, session.scheduled_left = None, 0
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
MAX_STRETCH_PER_SESSION = 2


def _stretch_skill(learner: LearnerState, session: SessionState) -> str | None:
    """The stretch slot: a skill whose scheduled apply (level 4) or transfer (level 5) item is due.

    The ladder sets `stretch_after_<level>` one day after the level was reached, so the item
    comes in a later session, spaced like a review. At most two per session, one per skill, and
    only when an item of the right role exists (a missing item is not a content gap here).
    """
    if session.session_type != "practice" or session.stretch_served >= MAX_STRETCH_PER_SESSION:
        return None
    for skill_id in session.overlay_skill_ids:
        if skill_id in session.blocked_skills or skill_id in session.stretch_skills:
            continue
        ladder = learner.ladders.get(skill_id)
        if ladder is None or ladder.level not in _EXTENSION_ROLE:
            continue
        due = ladder.flags.get(f"stretch_after_{ladder.level}")
        if not due or datetime.fromisoformat(str(due)) > session.now:
            continue
        role = _EXTENSION_ROLE[ladder.level]
        if any(row.role == role for row in _eligible_items(session, skill_id, set())):
            return skill_id
    return None


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
    return (
        session.active_ms >= session.soft_active_ms
        or session.items_completed >= session.soft_item_cap
    )


def _hard_cap(session: SessionState) -> bool:
    return session.active_ms >= session.hard_active_ms


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
