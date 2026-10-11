/** Offline pack: the shape of `GET /students/me/pack`, and how to start a session from it. */

import { createEmptyCard, type Card, State } from "ts-fsrs";
import type { BktParams } from "./bkt";
import { fromJson } from "./ladder";
import type { NotationProfile } from "./math";
import { parseAt } from "./time";
import {
  type CatalogItem,
  type LearnerState,
  newLearner,
  newSession,
  type PolicyEvent,
  type SessionState,
} from "./types";

export type PackLearner = {
  mastery: Record<
    string,
    { p_known: number; attempts: number; unhinted_correct: number; hinted_correct: number }
  >;
  ladders: Record<string, Parameters<typeof fromJson>[0]>;
  cards?: Record<string, { due_at: string; fsrs_state: Record<string, unknown> }>;
};

export type Pack = {
  version: number;
  hash: string;
  student_id?: string;
  chapter_id?: string | null;
  overlay: string[];
  prerequisites: Record<string, string[]>;
  bkt_params: Record<string, BktParams>;
  misconception_remedial: Record<string, string>;
  misconception_text: Record<string, string>;
  catalog: CatalogItem[];
  lessons?: unknown[];
  learner: PackLearner;
  limits: {
    soft_active_ms: number;
    soft_item_cap: number;
    hard_active_ms: number;
    max_words: number;
  };
  notation: NotationProfile;
  dont_know: string[];
};

/** A py-fsrs card (what the server stores) as a ts-fsrs card. */
export function cardFromServer(row: { due_at: string; fsrs_state: Record<string, unknown> }): Card {
  const due = new Date(row.due_at);
  const raw = row.fsrs_state ?? {};
  if (!raw || Object.keys(raw).length === 0) return createEmptyCard(due);
  return {
    due: new Date(String(raw.due ?? row.due_at)),
    stability: Number(raw.stability ?? 0),
    difficulty: Number(raw.difficulty ?? 0),
    elapsed_days: 0,
    scheduled_days: 0,
    learning_steps: Number(raw.step ?? 0),
    reps: 0,
    lapses: 0,
    state: Number(raw.state ?? 0) as State,
    last_review: raw.last_review ? new Date(String(raw.last_review)) : undefined,
  } as Card;
}

export function learnerFromPack(pack: Pack): LearnerState {
  const learner = newLearner();
  for (const [skill, row] of Object.entries(pack.learner.mastery ?? {})) {
    learner.mastery.set(skill, { skill_id: skill, ...row });
  }
  for (const [skill, row] of Object.entries(pack.learner.ladders ?? {})) {
    learner.ladders.set(skill, fromJson(row));
  }
  for (const [skill, row] of Object.entries(pack.learner.cards ?? {})) {
    learner.cards.set(skill, cardFromServer(row));
  }
  return learner;
}

export function sessionFromPack(pack: Pack, startedAt: string, sessionKey = "session"): SessionState {
  const now = parseAt(startedAt);
  const session = newSession({
    now,
    catalog: pack.catalog,
    overlay_skill_ids: pack.overlay,
    bkt_params: pack.bkt_params,
    prerequisites: pack.prerequisites,
    last_active_at: now,
    soft_active_ms: pack.limits.soft_active_ms,
    soft_item_cap: pack.limits.soft_item_cap,
    hard_active_ms: pack.limits.hard_active_ms,
    max_words: pack.limits.max_words,
  });
  session.session_key = sessionKey;
  session.misconception_remedial = { ...pack.misconception_remedial };
  session.misconception_text = { ...pack.misconception_text };
  return session;
}

/** What the server does with a sync event (`app/offline/sync.py: _event_for`), so both sides feed
 *  the policy the same thing. */
export type SyncEvent = {
  client_event_id: string;
  event_type: string;
  item_id?: string | null;
  at: string;
  payload: Record<string, unknown>;
};

export function policyEventFor(event: SyncEvent): PolicyEvent {
  const payload = event.payload ?? {};
  let response: string | null =
    payload.response !== undefined && payload.response !== null ? String(payload.response) : null;
  if (event.event_type === "stuck_choice" || event.event_type === "break_choice") {
    response = String(payload.choice ?? "");
  } else if (event.event_type === "stuck_step") {
    response = payload.index !== undefined && payload.index !== null ? String(payload.index) : "";
  }
  return {
    type: event.event_type,
    response,
    client_correct: (payload.correct as boolean | undefined) ?? null,
    latency_ms: (payload.latency_ms as number | undefined) ?? null,
    item_id: event.item_id ?? null,
    idle_ms: (payload.idle_ms as number | undefined) ?? null,
    text: (payload.text as string | undefined) ?? null,
    event_id: event.client_event_id,
  };
}
