/**
 * Reviewer desk rules, as pure functions. They mirror the API's rules (content_review/service.py
 * `check_desk_decision`) so a reviewer sees a problem before sending; the API stays the authority and its 422
 * messages are shown too.
 */
import type { DeskCard, DeskDecision, DeskDecisionBody, DeskSeverity } from "@/lib/api";
import { desk } from "@/lib/reviewDeskCopy";

export const CHECK_COUNT = 5;
export const MIN_NOTE_CHARS = 8; // non-space characters
export const MAX_ACTIVE_SECONDS = 7200; // the API refuses more than this per decision

export type Answer = boolean | null;
/** What a reviewer has entered on one question so far (kept per question while they move around). */
export type Draft = {
  checks: Answer[];
  notes: string[];
  reason: string | null;
  severity: DeskSeverity | null;
  note: string;
  /** set once they pressed Fix, Reject, Skip, or tried to move on with a note missing: shows the red state */
  tried: boolean;
};
export type Problem = { field: string; message: string; question?: number };

export const emptyDraft = (): Draft => ({
  checks: Array(CHECK_COUNT).fill(null) as Answer[],
  notes: Array(CHECK_COUNT).fill("") as string[],
  reason: null,
  severity: null,
  note: "",
  tried: false,
});

/** At least 8 characters that are not spaces. */
export const enoughNote = (text: string): boolean => text.replace(/\s/g, "").length >= MIN_NOTE_CHARS;

/** Questions marked "needs a fix" whose required note is still too short. */
export const missingNotes = (d: Draft): number[] =>
  d.checks.flatMap((c, i) => (c === false && !enoughNote(d.notes[i] ?? "") ? [i] : []));

/** The first question still unanswered, or -1 when all five are answered. */
export const nextUnanswered = (d: Draft): number => d.checks.findIndex((c) => c === null);
export const allYes = (d: Draft): boolean => d.checks.length === CHECK_COUNT && d.checks.every((c) => c === true);
export const anyNeedsFix = (d: Draft): boolean => d.checks.some((c) => c === false);

/** Moving to another question, or skipping, is blocked while a required note is empty. */
export const moveBlocked = (d: Draft): boolean => missingNotes(d).length > 0;

/** Problems that stop this decision from being sent. Empty: it may be sent. */
export function problemsFor(decision: DeskDecision, d: Draft): Problem[] {
  const out: Problem[] = [];
  const missing = missingNotes(d);
  if (decision === "approve") {
    if (!allYes(d)) out.push({ field: "checks", message: desk.needAllYes });
    return out;
  }
  if (decision === "skip") {
    for (const i of missing) out.push({ field: "fix_notes", question: i, message: desk.missingFixNotes(i + 1) });
    return out;
  }
  if (!d.severity) out.push({ field: "severity", message: desk.needSeverity });
  if (!d.reason) out.push({ field: "reason_code", message: desk.needReason });
  if (anyNeedsFix(d)) {
    for (const i of missing) out.push({ field: "fix_notes", question: i, message: desk.missingFixNotes(i + 1) });
  } else if (!enoughNote(d.note)) {
    out.push({ field: "note", message: desk.needMarkedOrNote });
  }
  return out;
}

/** Put the API's 422 messages next to the field they name. "question N" in a fix_notes message names the question. */
export function placeServerErrors(errors: { field: string; message: string }[]): Problem[] {
  return errors.map((e) => {
    const n = /question (\d+)/i.exec(e.message);
    return { field: e.field, message: e.message, question: e.field === "fix_notes" && n ? Number(n[1]) - 1 : undefined };
  });
}

export const clampSeconds = (seconds: number): number =>
  Math.max(0, Math.min(MAX_ACTIVE_SECONDS, Math.floor(Number.isFinite(seconds) ? seconds : 0)));

/** One clock tick: a second counts only when the reviewer has not paused and the tab is visible. */
export const tickSeconds = (seconds: number, state: { paused: boolean; hidden: boolean }): number =>
  state.paused || state.hidden ? seconds : seconds + 1;

export const formatClock = (seconds: number): string =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

/** The request body for a decision. Typed text is trimmed; empty parts are left out. */
export function buildBody(
  card: Pick<DeskCard, "content_hash">,
  decision: DeskDecision,
  d: Draft,
  seconds: number,
): DeskDecisionBody {
  const note = d.note.trim();
  const base = { content_hash: card.content_hash, decision, active_seconds: clampSeconds(seconds) };
  if (decision === "skip") return base;
  if (decision === "approve") return { ...base, checks: d.checks, ...(note ? { note } : {}) };
  const fixNotes = d.checks.flatMap((c, i) => (c === false ? [{ question_index: i, text: (d.notes[i] ?? "").trim() }] : []));
  return {
    ...base,
    checks: d.checks,
    ...(note ? { note } : {}),
    ...(d.severity ? { severity: d.severity } : {}),
    ...(d.reason ? { reason_code: d.reason } : {}),
    ...(fixNotes.length ? { fix_notes: fixNotes } : {}),
  };
}

/** What a key press means on the desk. Typing in a note or a field never triggers a key. */
export type DeskKey =
  | { kind: "answer"; yes: boolean }
  | { kind: "decide"; decision: DeskDecision }
  | { kind: "reason"; code: string }
  | { kind: "toggleAnswer" }
  | { kind: "help" }
  | { kind: "escape" };

export function keyAction(
  key: string,
  target: { tagName?: string; isContentEditable?: boolean } | null,
  mods: { ctrl?: boolean; meta?: boolean; alt?: boolean } = {},
): DeskKey | null {
  const tag = (target?.tagName ?? "").toUpperCase();
  const typing = tag === "TEXTAREA" || tag === "INPUT" || tag === "SELECT" || Boolean(target?.isContentEditable);
  if (typing) return null; // inside a field, Esc leaves the field (the page does that itself)
  if (mods.ctrl || mods.meta || mods.alt) return null;
  if (key === "?") return { kind: "help" };
  if (key === "Escape") return { kind: "escape" };
  const k = key.toLowerCase();
  if (k === "y") return { kind: "answer", yes: true };
  if (k === "n") return { kind: "answer", yes: false };
  if (k === "a") return { kind: "decide", decision: "approve" };
  if (k === "f") return { kind: "decide", decision: "fix" };
  if (k === "r") return { kind: "decide", decision: "reject" };
  if (k === "s") return { kind: "decide", decision: "skip" };
  if (k === "e") return { kind: "toggleAnswer" };
  if (/^[0-9]$/.test(key)) return { kind: "reason", code: key };
  return null;
}

/** Median of the seconds spent (the "typical time" on the summary); 0 when there are none. */
export function median(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}
