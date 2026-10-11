const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import type { Lesson } from "./lessons/types";

export type ActionPayload = {
  type: string;
  lesson?: Lesson;
  rejected?: boolean;
  /** Approved sources of an explanation, shown as chips. */
  sources?: { id: string; title: string }[];
  /** The server's verdict on a lesson beat answer (faded example, scene question). */
  lesson_correct?: boolean | null;
  item_id?: string | null;
  skill_id?: string | null;
  hint_level?: number | null;
  text?: string | null;
  correct?: boolean | null;
  ended_reason?: string | null;
  reason?: string | null;
  resumable?: boolean;
  extras?: Record<string, unknown>;
  session_type?: string;
  phase?: string;
  hint_level_shown?: number;
  allow_hint?: boolean;
  can_request_help?: boolean;
  /** Deprecated: use can_request_help. */
  can_request_hint?: boolean;
  can_show_solution?: boolean;
  dont_know_option?: boolean;
  item?: {
    id: string;
    type: string;
    stem: string;
    prediction?: string;
    options?: { id: string; label: string }[];
    steps?: string[];
    answer?: string;
  } | null;
};

export type SessionView = {
  id: string;
  type: string;
  student_id: string;
  action: ActionPayload;
  progress: {
    items_completed: number;
    active_ms: number;
    resumable: boolean;
    ended_reason?: string | null;
  };
};

function store(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

function token(): string {
  return store()?.getItem("yt_token") || "";
}

export function setToken(value: string) {
  store()?.setItem("yt_token", value);
}

export function setStudentId(value: string) {
  store()?.setItem("yt_student", value);
}

export function studentId(): string {
  return store()?.getItem("yt_student") || "";
}

export function locale(): string {
  return store()?.getItem("yt_locale") || "en";
}

export function setLocale(value: string) {
  store()?.setItem("yt_locale", value);
}

async function req(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const auth = token();
  if (auth) headers.set("Authorization", `Bearer ${auth}`);
  const response = await fetch(`${API}${path}`, { ...init, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  const ctype = response.headers.get("content-type") || "";
  if (ctype.includes("text/html")) {
    return response.text();
  }
  return response.json();
}

export async function studentLogin(family_code: string, pin: string) {
  const body = await req("/auth/student-login", {
    method: "POST",
    body: JSON.stringify({ family_code, pin }),
  });
  setToken(body.access_token);
  return body;
}

export type ContextOptions = {
  curricula: {
    id: string;
    grades: { grade: number; subjects: { id: string; books: { id: string; medium: string | null }[] }[] }[];
  }[];
  languages: { code: string; name: string }[];
};

export type GuestStartBody = {
  curriculum_id: string;
  grade: number;
  subject: string;
  home_language: string;
  device_timezone: string;
};

/** The context picker's choices: curriculum, grade, subject and language. No login needed. */
export async function getContextOptions(): Promise<ContextOptions> {
  return req("/context/options");
}

/** Start as a guest: no name, email or school; the reply carries the student's token. */
export async function guestStart(body: GuestStartBody) {
  const out = await req("/guest/start", { method: "POST", body: JSON.stringify(body) });
  setToken(out.token);
  setStudentId(out.student_id);
  setLocale(body.home_language);
  return out;
}

/** Answer the first-run or warm-up re-offer. Resolves with the kind of session to start. */
export async function answerOnboarding(
  choice: "warmup" | "start_beginning" | "not_now",
): Promise<{ next: { session_type: string } }> {
  return req("/students/me/onboarding", { method: "POST", body: JSON.stringify({ choice }) });
}

export async function today() {
  return req("/students/me/today");
}

export type DevScenario = {
  name: string;
  title: string;
  description: string;
  family_code: string;
  pin: string;
  seeded: boolean;
};

/** Dev only: re-create every scenario (takes up to a minute). */
export async function seedDevScenarios(): Promise<{ ok: boolean; output: string }> {
  return req("/dev/seed", { method: "POST" });
}

export type DevLessonRow = {
  id: string;
  skill_id: string;
  title: string;
  source_ref: string;
  status: string;
  beats: string[];
};

/** Dev only (no login): list lessons, fetch one, and let the server check a widget result. */
export async function listDevLessons(): Promise<{ lessons: DevLessonRow[] }> {
  return req("/dev/lessons");
}

export async function getDevLesson(id: string): Promise<Lesson> {
  return req(`/dev/lessons/${encodeURIComponent(id)}`);
}

export async function verifyDevWidget(
  lesson_id: string,
  widget_id: string,
  final_state: unknown,
): Promise<{ ok: boolean; code: string | null }> {
  return req("/dev/widgets/verify", {
    method: "POST",
    body: JSON.stringify({ lesson_id, widget_id, final_state }),
  });
}

/** Dev only: the API answers 404 unless DEV_TOOLS and ALLOW_DRAFT_CONTENT are on. */
export async function listDevScenarios(): Promise<{ scenarios: DevScenario[] }> {
  return req("/dev/scenarios");
}

export async function startSession(
  type: string,
  sid: string,
  chapterId?: string,
): Promise<SessionView> {
  return req("/sessions", {
    method: "POST",
    body: JSON.stringify({ student_id: sid, type, ...(chapterId ? { chapter_id: chapterId } : {}) }),
  });
}

export type ChapterStatus =
  | "not_started"
  | "learning"
  | "can_do_it"
  | "solid"
  | "review_due"
  | "coming_soon";

export type ChapterCard = {
  id: string;
  title: string;
  live: boolean;
  status: ChapterStatus;
  recommended: boolean;
  skills_total: number;
  skills_can_do_it: number;
};

export type SkillStatus = Exclude<ChapterStatus, "coming_soon">;

export type PathSkill = {
  id: string;
  title: string;
  level: number;
  status: SkillStatus;
  unlocked: boolean;
  current: boolean;
  has_lesson: boolean;
};

export async function getChapters(
  sid: string,
): Promise<{ student_id: string; subject: string; chapters: ChapterCard[] }> {
  return req(`/students/${sid}/chapters`);
}

export async function getChapterSkills(
  sid: string,
  chapterId: string,
): Promise<{ chapter: Omit<ChapterCard, "recommended">; skills: PathSkill[] }> {
  return req(`/students/${sid}/chapters/${encodeURIComponent(chapterId)}/skills`);
}

export async function startSkipAhead(
  sid: string,
  chapterId: string,
  skillId: string,
): Promise<SessionView> {
  return req(
    `/students/${sid}/chapters/${encodeURIComponent(chapterId)}/skills/${encodeURIComponent(skillId)}/skip-ahead`,
    { method: "POST" },
  );
}

export async function getSession(id: string): Promise<SessionView> {
  return req(`/sessions/${id}`);
}

export async function postEvent(
  sessionId: string,
  event_type: string,
  payload: Record<string, unknown> = {},
  item_id?: string | null,
): Promise<SessionView & { session_id: string }> {
  return req(`/sessions/${sessionId}/events`, {
    method: "POST",
    body: JSON.stringify({
      client_event_id: crypto.randomUUID(),
      event_type,
      item_id: item_id || null,
      payload,
    }),
  });
}

export async function enrolPilot(body: Record<string, unknown>) {
  return req("/admin/pilot/enrol", {
    method: "POST",
    headers: { "X-Pilot-Key": process.env.NEXT_PUBLIC_PILOT_KEY || "dev-pilot" },
    body: JSON.stringify(body),
  });
}
