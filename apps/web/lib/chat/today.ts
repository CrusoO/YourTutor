/**
 * Pure helpers for the returning student's home (UI-2b): the progress ring, the plan of about 25 minutes and the
 * weekly consistency row. Nothing here talks to the server; the active days are dates kept on this device only,
 * and there is no streak, no loss framing and no ranking.
 */
export type Share = { done: number; total: number; percent: number };

/** Share of syllabus skills at "can do it" or better, across the chapters that are live. */
export function progressShare(chapters: { skills_can_do_it: number; skills_total: number }[]): Share {
  const done = chapters.reduce((sum, c) => sum + c.skills_can_do_it, 0);
  const total = chapters.reduce((sum, c) => sum + c.skills_total, 0);
  return { done, total, percent: total ? Math.round((done / total) * 100) : 0 };
}

export type PlanItem = { kind: "review"; count: number; minutes: number } | { kind: "learn"; title: string; minutes: number };
export type Plan = { items: PlanItem[]; minutes: number };

const TARGET_MINUTES = 25;
const MAX_REVIEWS = 5;
const MINUTES_PER_REVIEW = 3;

/** Due reviews first (at most five), then the recommended next skill fills the rest of the time. */
export function planFor({ due, next }: { due: number; next: string | undefined }): Plan | null {
  const items: PlanItem[] = [];
  const reviews = Math.min(Math.max(0, due), MAX_REVIEWS);
  if (reviews > 0) items.push({ kind: "review", count: reviews, minutes: reviews * MINUTES_PER_REVIEW });
  const used = items.reduce((sum, i) => sum + i.minutes, 0);
  if (next) items.push({ kind: "learn", title: next, minutes: Math.max(5, TARGET_MINUTES - used) });
  if (!items.length) return null;
  return { items, minutes: items.reduce((sum, i) => sum + i.minutes, 0) };
}

const DAYS_KEY = "yt.days";

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** The seven days of the week containing `now`, Monday first. */
export function weekDays(now: Date): Date[] {
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });
}

function readDays(): string[] {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(DAYS_KEY) || "[]");
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

/** Record that the student did something today. Dates only, the last 21 kept. */
export function markActive(now: Date = new Date()): void {
  const today = iso(now);
  const days = readDays();
  if (days.includes(today)) return;
  try {
    window.localStorage.setItem(DAYS_KEY, JSON.stringify([...days, today].slice(-21)));
  } catch {
    /* storage is optional: the row just stays empty */
  }
}

/** For each day of this week (Monday first): was the student active on this device? */
export function activeDays(now: Date = new Date()): boolean[] {
  const days = new Set(readDays());
  return weekDays(now).map((d) => days.has(iso(d)));
}
