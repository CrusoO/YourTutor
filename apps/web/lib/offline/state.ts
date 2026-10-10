/** Plain-object views of the session and learner, in the shape the Python runtime stores. */

import { toJson } from "./ladder";
import { isoformat } from "./time";
import type { Action, LearnerState, SessionState } from "./types";

const sorted = (values: Iterable<string>) => [...values].sort();

export function dumpSession(s: SessionState) {
  return {
    phase: s.phase,
    current_skill: s.current_skill,
    current_item_id: s.current_item_id,
    hint_level_shown: s.hint_level_shown,
    attempt_after_hint2: s.attempt_after_hint2,
    explain_back_done: sorted(s.explain_back_done),
    introduced_skills: sorted(s.introduced_skills),
    shown_item_ids: [...s.shown_item_ids],
    items_completed: s.items_completed,
    active_ms: s.active_ms,
    last_active_at: s.last_active_at === null ? null : isoformat(s.last_active_at),
    warmup_done: s.warmup_done,
    warmup_left: s.warmup_left,
    ended_reason: s.ended_reason,
    similar_from_item_id: s.similar_from_item_id,
    last_wrong_response: s.last_wrong_response,
    last_wrong_item_id: s.last_wrong_item_id,
    fast_streak: s.fast_streak,
    help_without_attempt: s.help_without_attempt,
    stuck_item_id: s.stuck_item_id,
    stretch_served: s.stretch_served,
    wheel_skills: sorted(s.wheel_skills),
    wrong_first_streak: { ...s.wrong_first_streak },
    skill_items: { ...s.skill_items },
    seen_items: sorted(s.seen_items),
    answered_items: sorted(s.answered_items),
    probe_for: s.probe_for,
    lesson_prereq_levels: { ...s.lesson_prereq_levels },
    probe_skill: s.probe_skill,
    probe_done: sorted(s.probe_done),
    scheduled_prereq: s.scheduled_prereq,
    scheduled_left: s.scheduled_left,
    reveals: s.reveals,
    wrong_run: s.wrong_run,
    tier_down_items: s.tier_down_items,
    tier_up_next: s.tier_up_next,
    unhinted_run: s.unhinted_run,
    last_failure: s.last_failure,
    win_served: s.win_served,
    skill_failed: sorted(s.skill_failed),
    last_praise_at: s.last_praise_at,
    praise_count: s.praise_count,
    stretch_skills: sorted(s.stretch_skills),
    blocked_skills: sorted(s.blocked_skills),
    content_gaps: s.content_gaps.map((gap) => ({ ...gap })),
    stored_explain_text: s.stored_explain_text,
    alerts: s.alerts.map((alert) => ({ ...alert })),
  };
}

export function dumpAction(a: Action) {
  return {
    type: a.type,
    item_id: a.item_id ?? null,
    skill_id: a.skill_id ?? null,
    hint_level: a.hint_level ?? null,
    misconception_id: a.misconception_id ?? null,
    text: a.text ?? null,
    source: a.source,
    correct: a.correct ?? null,
    grade: a.grade ?? null,
    store_text: a.store_text,
    llm_called: a.llm_called,
    ended_reason: a.ended_reason ?? null,
    resumable: a.resumable,
    guardrail_flag: a.guardrail_flag ?? null,
    rejected: a.rejected,
    state_before: a.state_before ?? null,
    state_after: a.state_after ?? null,
    rule_id: a.rule_id ?? null,
    extras: a.extras,
  };
}

const minute = (ms: number) => isoformat(ms).slice(0, 16);

export function dumpLearner(l: LearnerState) {
  const mastery: Record<string, unknown> = {};
  for (const sid of [...l.mastery.keys()].sort()) {
    const m = l.mastery.get(sid)!;
    mastery[sid] = {
      p_known: m.p_known,
      attempts: m.attempts,
      unhinted_correct: m.unhinted_correct,
      hinted_correct: m.hinted_correct,
    };
  }
  const ladders: Record<string, unknown> = {};
  for (const sid of [...l.ladders.keys()].sort()) ladders[sid] = toJson(l.ladders.get(sid)!);
  const cards: Record<string, string> = {};
  for (const sid of [...l.cards.keys()].sort()) cards[sid] = minute(l.cards.get(sid)!.due.getTime());
  return { mastery, ladders, cards };
}
