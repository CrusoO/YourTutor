/** Client-only timers; defaults match production (60s hint, 90s idle). */
export const hintDelayMs = Number(process.env.NEXT_PUBLIC_HINT_DELAY_MS || 60_000);
export const idleNudgeMs = Number(process.env.NEXT_PUBLIC_IDLE_NUDGE_MS || 90_000);
