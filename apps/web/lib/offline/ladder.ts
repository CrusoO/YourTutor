/**
 * Mastery ladder, a mirror of apps/api/app/learner/ladder.py. The shared fixtures in
 * packages/shared/fixtures/ladder run against both, and the offline player and the sync check use
 * this code, so the two sides cannot disagree about a level.
 */

import { type BktParams, DEFAULT_BKT } from "./bkt";
import { applyMastery, type MasteryMemory, newMemory, type MasteryState } from "./mastery";
import { days, isoformat, parseAt } from "./time";

export const LADDER_POOLS = new Set(["practice", "warmup"]);
export const STREAK_ROLES = new Set(["procedure", "apply", "transfer"]);
export const MASTERY_P = 0.95;
export const STREAK_LENGTH = 3;
export const MIN_STRUCTURES = 2;
export const RETAIN_FIRST = days(7);
export const RETAIN_SECOND = days(21);
export const STRETCH_DELAY = days(1);
export const STRETCH_LEVELS = new Set([4, 5]);

export const KIND_ANSWER = "answer";
export const KIND_HINT = "request_hint";
export const KIND_LESSON = "lesson_complete";
export const KIND_TEST_OUT = "test_out";

export type LadderEvent = {
  event_id: string;
  skill_id: string;
  kind: string;
  /** milliseconds since the epoch (UTC) */
  at: number;
  item_id?: string;
  correct?: boolean | null;
  pool?: string;
  role?: string;
  structure?: string;
};

export type SkillLadder = {
  skill_id: string;
  achieved: number[];
  evidence: Record<number, string[]>;
  flags: Record<string, string | number | boolean>;
  seen: string[];
  hinted: string[];
  lesson_done: boolean;
  post_lesson_item: string | null;
  last_practice_at: number | null;
  run: [string, string][];
  retention_events: string[];
};

export function newLadder(skillId: string): SkillLadder {
  return {
    skill_id: skillId,
    achieved: [],
    evidence: {},
    flags: {},
    seen: [],
    hinted: [],
    lesson_done: false,
    post_lesson_item: null,
    last_practice_at: null,
    run: [],
    retention_events: [],
  };
}

export const level = (l: SkillLadder): number => (l.achieved.length ? Math.max(...l.achieved) : 0);
const retentionStage = (l: SkillLadder): number => Number(l.flags["retention_stage"] ?? 0);

/** The same shape as `SkillLadder.summary()` in Python. */
export function summary(l: SkillLadder) {
  const evidence: Record<string, string[]> = {};
  for (const key of Object.keys(l.evidence).map(Number).sort((a, b) => a - b)) {
    evidence[String(key)] = [...l.evidence[key]];
  }
  return { level: level(l), evidence, flags: sortedFlags(l.flags) };
}

function sortedFlags(flags: SkillLadder["flags"]) {
  return Object.fromEntries(Object.entries(flags).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
}

/** The same shape as `SkillLadder.to_json()` in Python. */
export function toJson(l: SkillLadder) {
  const evidence: Record<string, string[]> = {};
  for (const key of Object.keys(l.evidence).map(Number).sort((a, b) => a - b)) {
    evidence[String(key)] = [...l.evidence[key]];
  }
  return {
    skill_id: l.skill_id,
    achieved: [...l.achieved].sort((a, b) => a - b),
    evidence,
    flags: { ...l.flags },
    seen: [...l.seen],
    hinted: [...l.hinted],
    lesson_done: l.lesson_done,
    post_lesson_item: l.post_lesson_item,
    last_practice_at: l.last_practice_at === null ? null : isoformat(l.last_practice_at),
    run: l.run.map((pair) => [...pair]),
    retention_events: [...l.retention_events],
  };
}

function achieve(l: SkillLadder, lvl: number, eventIds: string[], at: number | null = null) {
  if (l.achieved.includes(lvl)) return;
  l.achieved.push(lvl);
  l.evidence[lvl] = [...eventIds];
  const key = `stretch_after_${lvl}`;
  if (at !== null && STRETCH_LEVELS.has(lvl) && !(key in l.flags)) {
    l.flags[key] = isoformat(at + STRETCH_DELAY);
  }
}

export function lessonLevel1Reached(l: SkillLadder, e: LadderEvent): boolean {
  return (
    l.lesson_done && e.kind === KIND_ANSWER && !!e.correct && l.post_lesson_item === e.item_id
  );
}

export function applyLadderEvent(
  ladders: Map<string, SkillLadder>,
  event: LadderEvent,
  pKnown: number,
): SkillLadder | null {
  const ensure = () => {
    let l = ladders.get(event.skill_id);
    if (!l) {
      l = newLadder(event.skill_id);
      ladders.set(event.skill_id, l);
    }
    return l;
  };
  const pool = event.pool ?? "practice";
  if (event.kind === KIND_TEST_OUT) {
    const l = ensure();
    if (!l.achieved.includes(4)) {
      achieve(l, 4, [event.event_id], event.at);
      l.flags["evidence"] = "test_out";
    }
    return l;
  }
  if (event.kind !== KIND_LESSON && !LADDER_POOLS.has(pool)) return null;
  const l = ensure();
  if (event.kind === KIND_LESSON) {
    l.lesson_done = true;
    l.post_lesson_item = null;
    return l;
  }
  if (event.kind !== KIND_ANSWER && event.kind !== KIND_HINT) return l;

  const itemId = event.item_id ?? "";
  const first = !l.seen.includes(itemId);
  const previousPractice = l.last_practice_at;
  const achievedBefore = new Set(l.achieved);

  if (l.lesson_done && l.post_lesson_item === null) l.post_lesson_item = itemId;
  if (first) {
    l.seen.push(itemId);
    if (event.kind === KIND_HINT) l.hinted.push(itemId);
  }
  const unhintedCorrectFirst = first && event.kind === KIND_ANSWER && !!event.correct;

  if (first) firstAttempt(l, event, pKnown, unhintedCorrectFirst, achievedBefore);
  if (event.kind === KIND_ANSWER && event.correct) {
    if ((event.role ?? "procedure") === "procedure") achieve(l, 3, [event.event_id]);
    if (lessonLevel1Reached(l, event)) achieve(l, 1, [event.event_id]);
  }
  if (first && pool === "warmup") {
    review(l, event, previousPractice, unhintedCorrectFirst);
  }
  l.last_practice_at = event.at;
  retentionLevel(l);
  return l;
}

function firstAttempt(
  l: SkillLadder,
  event: LadderEvent,
  pKnown: number,
  unhintedCorrect: boolean,
  achievedBefore: Set<number>,
) {
  const role = event.role ?? "procedure";
  if (unhintedCorrect && role === "explain") achieve(l, 2, [event.event_id]);
  if (unhintedCorrect && role === "apply" && achievedBefore.has(4)) {
    achieve(l, 5, [event.event_id], event.at);
  }
  if (unhintedCorrect && role === "transfer" && achievedBefore.has(5)) {
    achieve(l, 6, [event.event_id]);
  }
  if (STREAK_ROLES.has(role)) {
    if (unhintedCorrect) {
      l.run = [...l.run, [event.event_id, event.structure ?? ""] as [string, string]].slice(
        -STREAK_LENGTH,
      );
    } else {
      l.run = [];
    }
  }
  if (
    unhintedCorrect &&
    STREAK_ROLES.has(role) &&
    l.run.length === STREAK_LENGTH &&
    new Set(l.run.map(([, structure]) => structure)).size >= MIN_STRUCTURES &&
    pKnown >= MASTERY_P
  ) {
    achieve(l, 4, l.run.map(([id]) => id), event.at);
  }
}

function review(
  l: SkillLadder,
  event: LadderEvent,
  previousPractice: number | null,
  reviewCorrect: boolean,
) {
  const stage = retentionStage(l);
  if (!reviewCorrect) {
    l.flags["retention_stage"] = 0;
    l.retention_events = [];
    if (l.achieved.includes(7)) {
      l.achieved = l.achieved.filter((v) => v !== 7);
      delete l.evidence[7];
      l.flags["lapsed"] = true;
    }
    return;
  }
  if (previousPractice === null) return;
  const gap = event.at - previousPractice;
  if (stage === 0 && gap >= RETAIN_FIRST) {
    l.flags["retention_stage"] = 1;
    l.retention_events = [event.event_id];
  } else if (stage === 1 && gap >= RETAIN_SECOND) {
    l.flags["retention_stage"] = 2;
    l.retention_events = [...l.retention_events, event.event_id];
  }
}

function retentionLevel(l: SkillLadder) {
  if (retentionStage(l) >= 2 && l.achieved.includes(6) && !l.achieved.includes(7)) {
    achieve(l, 7, l.retention_events);
    delete l.flags["lapsed"];
  }
}

/** Fold the log into per-skill ladders; events dated after `now` are ignored. */
export function compute(
  events: LadderEvent[],
  now: number,
  paramsBySkill: Record<string, BktParams> = {},
): Map<string, SkillLadder> {
  const params: Record<string, BktParams> = { ...paramsBySkill };
  const state: MasteryState = { mastery: new Map() };
  const memory: MasteryMemory = newMemory();
  const ladders = new Map<string, SkillLadder>();
  for (const event of events) {
    if (event.at > now) continue;
    const pool = event.pool ?? "practice";
    let pKnown = 0.0;
    if (event.kind === KIND_LESSON || event.kind === KIND_TEST_OUT) {
      applyLadderEvent(ladders, event, 0.0);
      continue;
    }
    if (LADDER_POOLS.has(pool) && (event.kind === KIND_ANSWER || event.kind === KIND_HINT)) {
      params[event.skill_id] ??= DEFAULT_BKT;
      applyMastery(
        state,
        {
          item_id: event.item_id ?? "",
          skill_id: event.skill_id,
          event_type: event.kind,
          correct: event.correct ?? null,
          pool,
          session_id: "",
          is_warmup: pool === "warmup",
        },
        params,
        memory,
      );
      pKnown = state.mastery.get(event.skill_id)!.p_known;
    }
    applyLadderEvent(ladders, event, pKnown);
  }
  return ladders;
}

export { parseAt };

/** Rebuild a ladder from the shape `toJson` (and Python's `to_json`) writes. */
export function fromJson(data: ReturnType<typeof toJson>): SkillLadder {
  const evidence: Record<number, string[]> = {};
  for (const [key, ids] of Object.entries(data.evidence ?? {})) evidence[Number(key)] = [...ids];
  return {
    skill_id: String(data.skill_id),
    achieved: [...(data.achieved ?? [])],
    evidence,
    flags: { ...(data.flags ?? {}) } as SkillLadder["flags"],
    seen: [...(data.seen ?? [])],
    hinted: [...(data.hinted ?? [])],
    lesson_done: !!data.lesson_done,
    post_lesson_item: data.post_lesson_item ?? null,
    last_practice_at: data.last_practice_at ? parseAt(String(data.last_practice_at)) : null,
    run: (data.run ?? []).map(([a, b]) => [String(a), String(b)] as [string, string]),
    retention_events: [...(data.retention_events ?? [])],
  };
}
