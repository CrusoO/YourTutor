import type { ChapterCard, ChapterStatus } from "@/lib/api";

export type StudentHomeSnapshot = {
  resume: { session_id: string } | null;
  minutesLeft: number | null;
  current: { chapter: ChapterCard; skill?: string } | null;
  started: boolean;
  due: number;
  topics: { id: string; title: string; percent: number | null }[];
};

const CACHE_PREFIX = "yt_guest_home_v1:";
const CHAPTER_STATUSES: ChapterStatus[] = [
  "not_started",
  "learning",
  "can_do_it",
  "solid",
  "review_due",
  "coming_soon",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isChapterStatus(value: unknown): value is ChapterStatus {
  return typeof value === "string" && CHAPTER_STATUSES.some((status) => status === value);
}

function isChapterCard(value: unknown): value is ChapterCard {
  if (!isRecord(value)) return false;
  return (
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    typeof value.live === "boolean" &&
    isChapterStatus(value.status) &&
    typeof value.recommended === "boolean" &&
    typeof value.skills_total === "number" &&
    typeof value.skills_can_do_it === "number"
  );
}

function isStudentHomeSnapshot(value: unknown): value is StudentHomeSnapshot {
  if (!isRecord(value)) return false;
  const resume =
    value.resume === null ||
    (isRecord(value.resume) && typeof value.resume.session_id === "string");
  const current =
    value.current === null ||
    (isRecord(value.current) &&
      isChapterCard(value.current.chapter) &&
      (value.current.skill === undefined || typeof value.current.skill === "string"));
  const topics =
    Array.isArray(value.topics) &&
    value.topics.every(
      (topic) =>
        isRecord(topic) &&
        typeof topic.id === "string" &&
        typeof topic.title === "string" &&
        (topic.percent === null ||
          (typeof topic.percent === "number" &&
            Number.isFinite(topic.percent) &&
            topic.percent >= 0 &&
            topic.percent <= 100)),
    );

  return (
    resume &&
    current &&
    topics &&
    (value.minutesLeft === null ||
      (typeof value.minutesLeft === "number" && Number.isFinite(value.minutesLeft))) &&
    typeof value.started === "boolean" &&
    typeof value.due === "number" &&
    Number.isFinite(value.due)
  );
}

function cacheKey(studentId: string): string {
  return `${CACHE_PREFIX}${encodeURIComponent(studentId)}`;
}

export function readGuestHomeCache(studentId: string): StudentHomeSnapshot | null {
  try {
    const raw = window.sessionStorage.getItem(cacheKey(studentId));
    if (!raw) return null;
    const value: unknown = JSON.parse(raw);
    return isStudentHomeSnapshot(value) ? value : null;
  } catch {
    return null;
  }
}

export function writeGuestHomeCache(studentId: string, snapshot: StudentHomeSnapshot): void {
  try {
    window.sessionStorage.setItem(cacheKey(studentId), JSON.stringify(snapshot));
  } catch {
    // Guest caching is optional when browser storage is unavailable.
  }
}

export function clearGuestHomeCache(studentId: string): void {
  try {
    window.sessionStorage.removeItem(cacheKey(studentId));
  } catch {
    // Guest caching is optional when browser storage is unavailable.
  }
}
