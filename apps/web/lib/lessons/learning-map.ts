/**
 * What a learner showed during one interactive lesson, and what to say back about it.
 *
 * Everything here stays on the device: nothing is sent anywhere, and the learner can clear it. A guest holds
 * no consent for more, and the tutor itself never reads this.
 */

export type Confidence = "sure" | "unsure";

/** One answered question: which, how it went the first time, how sure the learner said they were. */
export type Evidence = {
  /** Where the block sits in the lesson, so a later retest can be matched to it. */
  id: string;
  kind: "predict" | "check";
  question: string;
  options: string[];
  /** Index of the right option. */
  correct: number;
  /** Whether the first answer was right. */
  right: boolean;
  confidence: Confidence | null;
  /** A short name for the idea behind the wrong option chosen, when the lesson gave one. */
  idea: string | null;
};

export type Summary = {
  right: Evidence[];
  shaky: Evidence[];
  /** Wrong while sure: the ones most worth fixing, and the ones that come back after a week if not retested. */
  sureButWrong: Evidence[];
  sureCount: number;
  sureRight: number;
};

export function summarise(evidence: readonly Evidence[]): Summary {
  const sure = evidence.filter((e) => e.confidence === "sure");
  return {
    right: evidence.filter((e) => e.right),
    shaky: evidence.filter((e) => !e.right && e.confidence !== "sure"),
    sureButWrong: sure.filter((e) => !e.right),
    sureCount: sure.length,
    sureRight: sure.filter((e) => e.right).length,
  };
}

/** What to say about how well the learner read themselves: nothing when they never said how sure they were. */
export function calibration(summary: Summary): "none" | "good" | "overconfident" {
  if (summary.sureCount === 0) return "none";
  return summary.sureButWrong.length > 0 ? "overconfident" : "good";
}

/** The options in a different order, so a retest checks the idea and not the position. Never the same order. */
export function rotated<T>(items: readonly T[]): T[] {
  if (items.length < 2) return [...items];
  const shift = items.length > 3 ? 2 : 1;
  return [...items.slice(shift), ...items.slice(0, shift)];
}

// ── the device-only record ───────────────────────────────────────────────────

export type SavedLesson = { topic: string; at: string; items: Pick<Evidence, "id" | "kind" | "right" | "confidence" | "idea">[] };

const KEY = "yt.learning-map.v1";
const KEEP = 20;
const TOPIC_CHARS = 80;

function store(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function loadSaved(): SavedLesson[] {
  try {
    const raw = store()?.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? (parsed as SavedLesson[]) : [];
  } catch {
    return [];
  }
}

/** Keep this lesson's result on the device (the latest twenty). Fails quietly where storage is blocked. */
export function saveLesson(topic: string, evidence: readonly Evidence[], now: Date = new Date()): void {
  if (evidence.length === 0) return;
  const entry: SavedLesson = {
    topic: topic.trim().slice(0, TOPIC_CHARS),
    at: now.toISOString(),
    items: evidence.map(({ id, kind, right, confidence, idea }) => ({ id, kind, right, confidence, idea })),
  };
  try {
    store()?.setItem(KEY, JSON.stringify([entry, ...loadSaved()].slice(0, KEEP)));
  } catch {
    /* the lesson still works without a record */
  }
}

export function clearSaved(): void {
  try {
    store()?.removeItem(KEY);
  } catch {
    /* nothing to clear */
  }
}
