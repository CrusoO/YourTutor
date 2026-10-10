/**
 * Per-skill mastery from learner events: a mirror of apps/api/app/learner/mastery_service.py.
 * BKT is updated once per item (the first answer or hint request); counts of unhinted and hinted
 * correct answers follow the same rules. FSRS review cards are optional (`state.cards`), because
 * ts-fsrs rounds its numbers differently from the Python library: the server's cards are the ones
 * that count after a sync.
 */

import { type BktParams, posterior } from "./bkt";
import { type Card, rateSession, rateWarmup, reviewCard } from "./fsrs";

export type Mastery = {
  skill_id: string;
  p_known: number;
  attempts: number;
  unhinted_correct: number;
  hinted_correct: number;
};

export type MasteryState = {
  mastery: Map<string, Mastery>;
  cards?: Map<string, Card>;
};

export type LearnerEvent = {
  item_id: string;
  skill_id: string;
  event_type: string;
  correct?: boolean | null;
  pool?: string;
  session_id?: string;
  latency_ms?: number | null;
  is_warmup?: boolean;
  /** only used to date FSRS reviews */
  at?: number;
};

export type MasteryMemory = {
  bkt_done: Set<string>;
  hinted: Set<string>;
  first_wrong: Set<string>;
  /** session id -> skill id -> [unhinted correct, unhinted first attempts] */
  session_unhinted: Map<string, Map<string, [number, number]>>;
  warmup_skills: Set<string>;
};

export function newMemory(): MasteryMemory {
  return {
    bkt_done: new Set(),
    hinted: new Set(),
    first_wrong: new Set(),
    session_unhinted: new Map(),
    warmup_skills: new Set(),
  };
}

export const isMastered = (m: Mastery): boolean => m.p_known >= 0.95 && m.unhinted_correct >= 3;

function ensure(state: MasteryState, skillId: string, params: BktParams): Mastery {
  let row = state.mastery.get(skillId);
  if (!row) {
    row = { skill_id: skillId, p_known: params.p_init, attempts: 0, unhinted_correct: 0, hinted_correct: 0 };
    state.mastery.set(skillId, row);
  }
  return row;
}

export function applyMastery(
  state: MasteryState,
  event: LearnerEvent,
  paramsBySkill: Record<string, BktParams>,
  memory: MasteryMemory,
): void {
  const pool = event.pool ?? "practice";
  if (event.event_type === "explain_back" || pool === "checkpoint") return;
  if (event.event_type === "session_end") {
    sessionEnd(state, event, memory);
    return;
  }
  const params = paramsBySkill[event.skill_id];
  const mastery = ensure(state, event.skill_id, params);

  if (event.event_type === "request_hint") {
    memory.hinted.add(event.item_id);
    if (!memory.bkt_done.has(event.item_id)) {
      mastery.p_known = posterior(mastery.p_known, false, params);
      mastery.attempts += 1;
      memory.bkt_done.add(event.item_id);
    }
    return;
  }
  if (event.event_type !== "answer") return;

  const first = !memory.bkt_done.has(event.item_id);
  const wasHinted = memory.hinted.has(event.item_id);
  if (first) {
    mastery.p_known = posterior(mastery.p_known, !!event.correct, params);
    mastery.attempts += 1;
    memory.bkt_done.add(event.item_id);
    if (event.correct && !wasHinted) mastery.unhinted_correct += 1;
    if (!event.correct) memory.first_wrong.add(event.item_id);
  } else if (event.correct && (wasHinted || memory.first_wrong.has(event.item_id))) {
    mastery.hinted_correct += 1;
  }

  const warmup = !!event.is_warmup || pool === "warmup";
  if (warmup) {
    memory.warmup_skills.add(`${event.session_id ?? ""}\u0000${event.skill_id}`);
    if (state.cards && event.at !== undefined) {
      state.cards.set(
        event.skill_id,
        reviewCard(
          state.cards.get(event.skill_id),
          rateWarmup(!!event.correct, wasHinted, event.latency_ms ?? null),
          event.at,
        ),
      );
    }
    return;
  }
  if (pool === "practice" && first && !wasHinted) {
    const sid = event.session_id ?? "";
    let skills = memory.session_unhinted.get(sid);
    if (!skills) {
      skills = new Map();
      memory.session_unhinted.set(sid, skills);
    }
    const pair = skills.get(event.skill_id) ?? [0, 0];
    pair[1] += 1;
    if (event.correct) pair[0] += 1;
    skills.set(event.skill_id, pair);
  }
}

function sessionEnd(state: MasteryState, event: LearnerEvent, memory: MasteryMemory) {
  const sid = event.session_id ?? "";
  const perSkill = memory.session_unhinted.get(sid);
  if (!perSkill || !state.cards || event.at === undefined) return;
  for (const [skillId, [correct, total]] of perSkill) {
    if (memory.warmup_skills.has(`${sid}\u0000${skillId}`)) continue;
    const rate = total ? correct / total : 0.0;
    state.cards.set(skillId, reviewCard(state.cards.get(skillId), rateSession(rate), event.at));
  }
}
