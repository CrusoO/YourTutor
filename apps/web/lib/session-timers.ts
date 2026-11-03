/** Client-only timers; defaults match production (60s hint, 90s idle). */
export const hintDelayMs = Number(process.env.NEXT_PUBLIC_HINT_DELAY_MS || 60_000);
export const idleNudgeMs = Number(process.env.NEXT_PUBLIC_IDLE_NUDGE_MS || 90_000);

/** The longest answer time worth recording; the API caps active time per event at the same five minutes. */
export const MAX_ANSWER_MS = 300_000;

/** Milliseconds from when the question appeared to now: a whole number, at least 1, at most five minutes. */
export function elapsedMs(shownAt: number, now: number = Date.now()): number {
  const gone = Math.round(now - shownAt);
  return Math.min(MAX_ANSWER_MS, Math.max(1, Number.isFinite(gone) ? gone : 1));
}
