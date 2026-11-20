import { safeStorage } from "../api";

/**
 * The "days this week" record. It is only local calendar dates (YYYY-MM-DD) of days the student practised, kept on this
 * device under a key made from their pseudonymous learner or guest id. No time of day, nothing is sent anywhere, and
 * every storage call is guarded: the page works with no storage at all.
 */

export type DayStatus = "practised" | "rest" | "none" | "today" | "later";
export type DayCell = { index: number; key: string; status: DayStatus };

const KEEP_DAYS = 14;

/** Local calendar date as YYYY-MM-DD (never a time). */
export function dateKey(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

/** Monday = 0 ... Sunday = 6. */
export function weekdayIndex(d: Date): number {
  return (d.getDay() + 6) % 7;
}

/**
 * The seven days of the current week, Monday first. One rest day is built in: the first day already gone by that has no
 * practice counts as the rest day, so a day off never shows as a failure.
 */
export function weekCells(practisedKeys: readonly string[], now: Date): DayCell[] {
  const today = weekdayIndex(now);
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - today);
  const done = new Set(practisedKeys);
  let restUsed = false;
  const cells: DayCell[] = [];
  for (let i = 0; i < 7; i++) {
    const day = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i);
    const key = dateKey(day);
    let status: DayStatus;
    if (done.has(key)) status = "practised";
    else if (i > today) status = "later";
    else if (i === today) status = "today";
    else if (!restUsed) {
      restUsed = true;
      status = "rest";
    } else status = "none";
    cells.push({ index: i, key, status });
  }
  return cells;
}

export function practisedCount(cells: readonly DayCell[]): number {
  return cells.filter((c) => c.status === "practised").length;
}

export type WeekState = { on: boolean; days: string[] };

function keyFor(learnerId: string): string {
  return `yt_week_dots:${learnerId || "guest"}`;
}

export function loadWeek(learnerId: string): WeekState {
  try {
    const raw = safeStorage()?.getItem(keyFor(learnerId));
    if (!raw) return { on: false, days: [] };
    const parsed = JSON.parse(raw) as Partial<WeekState>;
    const days = Array.isArray(parsed.days) ? parsed.days.filter((d): d is string => /^\d{4}-\d{2}-\d{2}$/.test(String(d))) : [];
    return { on: parsed.on === true, days: days.slice(-KEEP_DAYS) };
  } catch {
    return { on: false, days: [] };
  }
}

export function saveWeek(learnerId: string, state: WeekState): void {
  try {
    const keep = { on: state.on, days: [...new Set(state.days)].sort().slice(-KEEP_DAYS) };
    safeStorage()?.setItem(keyFor(learnerId), JSON.stringify(keep));
  } catch {
    /* storage is optional */
  }
}

/** Switching off forgets the days too, so nothing is kept for a view the student does not want. */
export function clearWeek(learnerId: string): void {
  try {
    safeStorage()?.removeItem(keyFor(learnerId));
  } catch {
    /* storage is optional */
  }
}
