/** Offline player types: mirrors of apps/api/app/orchestrator/types.py (practice sessions only). */

import type { Card } from "./fsrs";
import type { BktParams } from "./bkt";
import type { SkillLadder } from "./ladder";
import { type MasteryMemory, type MasteryState, newMemory } from "./mastery";

export const SOFT_ACTIVE_MS = 15 * 60 * 1000;
export const HARD_ACTIVE_MS = 20 * 60 * 1000;
export const IDLE_END_MS = 10 * 60 * 1000;
export const LATENCY_CAP_MS = 5 * 60 * 1000;
export const SOFT_ITEM_CAP = 12;
export const MAX_WARMUP = 3;
export const PREREQ_BELOW = 0.6;

export type CatalogItem = {
  id: string;
  skill_ids: string[];
  difficulty: number;
  pool: string;
  status: string;
  role: string;
  structure: string;
  type: string;
  answer_sympy: string;
  accept: string[];
  hints: [number, string][];
  solution_steps: string[];
  misconception_rules: [string, string[]][];
  prediction_prompt: string;
  authored_explanation: string;
  options: { id: string; en?: string }[];
  /** milliseconds since the epoch, or null when never shown */
  last_shown_at: number | null;
  slip_patterns: Record<string, unknown>[];
  prereq_signatures: Record<string, unknown>[];
  intermediate_values: string[];
  min_plausible_ms: number | null;
  step_hints: string[];
  hint_restate: string;
  /** the question as shown (packs carry it; the policy never reads it) */
  stem?: string;
};

export const primarySkill = (item: CatalogItem): string => item.skill_ids[0];

export function hintText(item: CatalogItem, level: number): string {
  for (const [rowLevel, text] of item.hints) if (rowLevel === level) return text;
  return "";
}

export type PolicyEvent = {
  type: string;
  response?: string | null;
  client_correct?: boolean | null;
  latency_ms?: number | null;
  item_id?: string | null;
  idle_ms?: number | null;
  text?: string | null;
  event_id?: string | null;
};

export type Action = {
  type: string;
  item_id?: string | null;
  skill_id?: string | null;
  hint_level?: number | null;
  misconception_id?: string | null;
  text?: string | null;
  source: string;
  correct?: boolean | null;
  grade?: string | null;
  store_text: boolean;
  llm_called: boolean;
  ended_reason?: string | null;
  resumable: boolean;
  guardrail_flag?: string | null;
  rejected: boolean;
  state_before?: string | null;
  state_after?: string | null;
  rule_id?: string | null;
  extras: Record<string, unknown>;
};

export function makeAction(type: string, fields: Partial<Action> = {}): Action {
  return {
    type,
    source: "authored",
    store_text: false,
    llm_called: false,
    resumable: false,
    rejected: false,
    extras: {},
    ...fields,
  };
}

export type SessionState = {
  session_type: string;
  /** milliseconds since the epoch */
  now: number;
  catalog: CatalogItem[];
  overlay_skill_ids: string[];
  bkt_params: Record<string, BktParams>;
  prerequisites: Record<string, string[]>;
  phase: string;
  current_skill: string | null;
  current_item_id: string | null;
  hint_level_shown: number;
  attempt_after_hint2: boolean;
  explain_back_done: Set<string>;
  introduced_skills: Set<string>;
  shown_item_ids: string[];
  items_completed: number;
  active_ms: number;
  last_active_at: number | null;
  warmup_done: boolean;
  warmup_left: number;
  last_action: Action | null;
  consent_revoked: boolean;
  allow_draft: boolean;
  llm_called: boolean;
  ended_reason: string | null;
  last_event: PolicyEvent | null;
  last_correct: boolean | null;
  event_counter: number;
  session_key: string;
  stored_explain_text: string | null;
  similar_from_item_id: string | null;
  last_wrong_response: string | null;
  last_wrong_item_id: string | null;
  fast_streak: number;
  help_without_attempt: number;
  misconception_remedial: Record<string, string>;
  last_diagnosis: { class: string; detail: string | null } | null;
  misconception_text: Record<string, string>;
  stuck_item_id: string | null;
  stretch_served: number;
  teacher_share: boolean;
  alerts: { skill_id: string; type: string }[];
  wheel_skills: Set<string>;
  wrong_first_streak: Record<string, number>;
  skill_items: Record<string, number>;
  seen_items: Set<string>;
  answered_items: Set<string>;
  lesson_prereq_levels: Record<string, number[]>;
  probe_for: string | null;
  probe_skill: string | null;
  probe_done: Set<string>;
  scheduled_prereq: string | null;
  scheduled_left: number;
  reveals: number;
  wrong_run: number;
  tier_down_items: number;
  tier_up_next: boolean;
  unhinted_run: number;
  last_failure: boolean;
  win_served: boolean;
  skill_failed: Set<string>;
  last_praise_at: number;
  praise_count: number;
  soft_active_ms: number;
  soft_item_cap: number;
  hard_active_ms: number;
  max_words: number;
  stretch_skills: Set<string>;
  blocked_skills: Set<string>;
  content_gaps: Record<string, unknown>[];
  bkt_memory: MasteryMemory;
};

export function newSession(
  fields: Pick<SessionState, "now" | "catalog" | "overlay_skill_ids" | "bkt_params"> &
    Partial<SessionState>,
): SessionState {
  return {
    session_type: "practice",
    prerequisites: {},
    phase: "start",
    current_skill: null,
    current_item_id: null,
    hint_level_shown: 0,
    attempt_after_hint2: false,
    explain_back_done: new Set(),
    introduced_skills: new Set(),
    shown_item_ids: [],
    items_completed: 0,
    active_ms: 0,
    last_active_at: null,
    warmup_done: false,
    warmup_left: 0,
    last_action: null,
    consent_revoked: false,
    allow_draft: false,
    llm_called: false,
    ended_reason: null,
    last_event: null,
    last_correct: null,
    event_counter: 0,
    session_key: "",
    stored_explain_text: null,
    similar_from_item_id: null,
    last_wrong_response: null,
    last_wrong_item_id: null,
    fast_streak: 0,
    help_without_attempt: 0,
    misconception_remedial: {},
    last_diagnosis: null,
    misconception_text: {},
    stuck_item_id: null,
    stretch_served: 0,
    teacher_share: false,
    alerts: [],
    wheel_skills: new Set(),
    wrong_first_streak: {},
    skill_items: {},
    seen_items: new Set(),
    answered_items: new Set(),
    lesson_prereq_levels: {},
    probe_for: null,
    probe_skill: null,
    probe_done: new Set(),
    scheduled_prereq: null,
    scheduled_left: 0,
    reveals: 0,
    wrong_run: 0,
    tier_down_items: 0,
    tier_up_next: false,
    unhinted_run: 0,
    last_failure: false,
    win_served: false,
    skill_failed: new Set(),
    last_praise_at: -99,
    praise_count: 0,
    soft_active_ms: SOFT_ACTIVE_MS,
    soft_item_cap: SOFT_ITEM_CAP,
    hard_active_ms: HARD_ACTIVE_MS,
    max_words: 60,
    stretch_skills: new Set(),
    blocked_skills: new Set(),
    content_gaps: [],
    bkt_memory: newMemory(),
    ...fields,
  };
}

export function itemById(session: SessionState, id?: string | null): CatalogItem | null {
  const target = id || session.current_item_id;
  if (!target) return null;
  return session.catalog.find((row) => row.id === target) ?? null;
}

/** The learner side: mastery, FSRS cards and ladders (the `LearnerState` of Python). */
export type LearnerState = MasteryState & {
  cards: Map<string, Card>;
  ladders: Map<string, SkillLadder>;
};

export function newLearner(): LearnerState {
  return { mastery: new Map(), cards: new Map(), ladders: new Map() };
}

/** An item with every field defaulted; callers set what they need. */
export function makeItem(fields: Partial<CatalogItem> & Pick<CatalogItem, "id" | "skill_ids">): CatalogItem {
  return {
    difficulty: 0.5,
    pool: "practice",
    status: "approved",
    role: "procedure",
    structure: "",
    type: "expression",
    answer_sympy: "0",
    accept: [],
    hints: [],
    solution_steps: [],
    misconception_rules: [],
    prediction_prompt: "",
    authored_explanation: "",
    options: [],
    last_shown_at: null,
    slip_patterns: [],
    prereq_signatures: [],
    intermediate_values: [],
    min_plausible_ms: null,
    step_hints: [],
    hint_restate: "",
    ...fields,
  };
}
