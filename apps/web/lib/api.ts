const API =
  typeof window === "undefined"
    ? process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : "/api";

import type { FinderRules } from "./chat/finder";
import type { Lesson } from "./lessons/types";
import { setLocale } from "./locale";

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

/** An anonymous guest is kept for this tab only: closing the tab forgets them. A real sign-in uses the device store. */
function tab(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function read(key: string): string {
  return tab()?.getItem(key) || store()?.getItem(key) || "";
}

function token(): string {
  return read("yt_token");
}

/** Is a student (or guest) token stored on this device? */
export function hasStudentToken(): boolean {
  return token() !== "";
}

export function setToken(value: string) {
  tab()?.removeItem("yt_token"); // a real sign-in replaces any guest of this tab
  tab()?.removeItem("yt_student");
  store()?.setItem("yt_token", value);
}

/** Forget the student (or guest) on this device. */
export function clearStudent() {
  store()?.removeItem("yt_token");
  store()?.removeItem("yt_student");
  tab()?.removeItem("yt_token");
  tab()?.removeItem("yt_student");
}

export function setStudentId(value: string) {
  store()?.setItem("yt_student", value);
}

export function studentId(): string {
  return read("yt_student");
}

/** The interface language and its setter live in lib/locale.ts (one store, live languages only); re-exported here. */
export { currentLocale as locale, setLocale } from "./locale";

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
  setStaffToken(""); // one role per device: a student sign-in replaces any guardian or teacher sign-in
  setToken(body.access_token);
  return body;
}

export type ContextOptions = {
  /** Every class the product knows about (from config), so empty ones can say "coming soon". */
  grades?: number[];
  curricula: {
    id: string;
    titles?: Record<string, string>;
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

/** The checks the topic finder runs in the browser on typed text (a GET: no user text is sent). */
export async function getFinderRules(language: string): Promise<FinderRules> {
  return req(`/context/finder-rules?language=${encodeURIComponent(language)}`);
}

/** Start as a guest: no name, email or school; the reply carries the student's token. */
export async function guestStart(body: GuestStartBody) {
  const out = await req("/guest/start", { method: "POST", body: JSON.stringify(body) });
  store()?.removeItem("yt_token");
  store()?.removeItem("yt_student");
  tab()?.setItem("yt_token", out.token);
  tab()?.setItem("yt_student", out.student_id);
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

// ── video jobs ────────────────────────────────────────────────────────────────

export type VideoJobTopic = {
  node_id: string;
  chapter_title: string;
  section_title: string;
  page_start: number | null;
  page_end: number | null;
};

export type VideoJob = {
  id: string;
  node_id: string;
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  stage: string | null;
  stage_label: string | null;
  error_code: string | null;
  error_message: string | null;
  events: unknown[];
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export async function getVideoJobTopics(
  nodePrefix = "cbse.10.maths",
): Promise<{ topics: VideoJobTopic[] }> {
  return req(`/video-jobs/topics?node_prefix=${encodeURIComponent(nodePrefix)}`);
}

export async function createVideoJob(
  nodeId: string,
  idempotencyKey: string,
): Promise<VideoJob> {
  return req("/video-jobs", {
    method: "POST",
    body: JSON.stringify({ node_id: nodeId, idempotency_key: idempotencyKey }),
  });
}

/** A video for a typed question: the engine matches the words to a topic and may answer "not available". */
export async function createPromptVideoJob(prompt: string, idempotencyKey: string): Promise<VideoJob> {
  return req("/video-jobs", {
    method: "POST",
    body: JSON.stringify({ prompt, idempotency_key: idempotencyKey }),
  });
}

export type VideoSource = { title: string; sections: { heading: string; body: string }[] };

/** A video made from the explanation just written: the API accepts only text it signed for this student. */
export async function createSourceVideoJob(video: { source: VideoSource; proof: string }, idempotencyKey: string): Promise<VideoJob> {
  return req("/video-jobs", {
    method: "POST",
    body: JSON.stringify({ source: video.source, source_proof: video.proof, idempotency_key: idempotencyKey }),
  });
}

export type StoryResult =
  | { kind: "story"; story: Record<string, unknown>; proof: string }
  | { kind: "unavailable"; reason: string }
  | { kind: "refused" | "distress" | "out_of_scope"; message: string }
  | { kind: "empty" };

/** The question planned as an animated story and written scene by scene (shapes, motion and narration). */
export async function explainStory(prompt: string, language: "en" | "hi"): Promise<StoryResult> {
  return req("/explain/story", { method: "POST", body: JSON.stringify({ prompt, language }) });
}

/** A video from a story this API wrote and signed for this student: the engine draws and animates it. */
export async function createStoryVideoJob(story: Record<string, unknown>, proof: string, idempotencyKey: string): Promise<VideoJob> {
  return req("/video-jobs", {
    method: "POST",
    body: JSON.stringify({ story, story_proof: proof, idempotency_key: idempotencyKey }),
  });
}

export type Explanation =
  | {
      kind: "explanation";
      title: string;
      sections: { heading: string; body: string }[];
      /**
       * The video content signed by the API for this student.
       * `story` = animated story (preferred, ADR 0091); `source` = text-card fallback.
       */
      video?: { story: Record<string, unknown>; proof: string } | { source: VideoSource; proof: string };
    }
  | { kind: "unavailable"; reason: string }
  | { kind: "refused" | "distress" | "out_of_scope"; message: string; reason?: string }
  | { kind: "empty" };

/** The in-depth, first-principles explanation of a typed question. The question is never kept by the page. */
export async function explainQuestion(prompt: string, language: "en" | "hi"): Promise<Explanation> {
  return req("/explain", { method: "POST", body: JSON.stringify({ prompt, language }) });
}

export async function getVideoJob(jobId: string): Promise<VideoJob> {
  return req(`/video-jobs/${jobId}`);
}

export async function cancelVideoJob(jobId: string): Promise<VideoJob> {
  return req(`/video-jobs/${jobId}/cancel`, { method: "POST" });
}

/**
 * Low-level authenticated fetch for non-JSON responses (e.g. MP4 blobs).
 * Caller is responsible for checking response.ok.
 */
export async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const auth = token();
  if (auth) headers.set("Authorization", `Bearer ${auth}`);
  return fetch(`${API}${path}`, { ...init, headers });
}

// ── pilot enrol ───────────────────────────────────────────────────────────────

export async function enrolPilot(body: Record<string, unknown>) {
  return req("/admin/pilot/enrol", {
    method: "POST",
    headers: { "X-Pilot-Key": process.env.NEXT_PUBLIC_PILOT_KEY || "dev-pilot" },
    body: JSON.stringify(body),
  });
}

/** The offline pack for the signed-in student's chapter. */
export async function getPack() {
  return req("/students/me/pack");
}

/** Send queued offline events; the reply carries the server's recomputed learner state. */
export async function postSync(body: unknown) {
  return req("/sync/events", { method: "POST", body: JSON.stringify(body) });
}

// ---- guardians and teachers (their own sign-in; the student token is left alone) -------------

const STAFF_KEY = "yt_staff_token";

export function staffToken(): string {
  return store()?.getItem(STAFF_KEY) || "";
}

export function setStaffToken(value: string) {
  if (value) store()?.setItem(STAFF_KEY, value);
  else store()?.removeItem(STAFF_KEY);
}

async function staffReq(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const auth = staffToken();
  if (auth) headers.set("Authorization", `Bearer ${auth}`);
  const response = await fetch(`${API}${path}`, { ...init, headers });
  if (!response.ok) throw new Error((await response.text()) || response.statusText);
  return response.json();
}

export async function requestStaffCode(email: string) {
  return staffReq("/auth/request-otp", { method: "POST", body: JSON.stringify({ email }) });
}

export async function verifyStaffCode(email: string, code: string) {
  const out = await staffReq("/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify({ email, code }),
  });
  clearStudent(); // one role per device: a guardian or teacher sign-in replaces any student sign-in
  setStaffToken(out.access_token);
  return out;
}

export const whoAmI = () => staffReq("/auth/me");
export const familyExport = () => staffReq("/parents/me/export");
export const deleteFamily = () => staffReq("/parents/me", { method: "DELETE" });
export const guardianView = (studentId: string, lang?: string) =>
  staffReq(`/students/${studentId}/guardian-view${lang ? `?lang=${encodeURIComponent(lang)}` : ""}`);
export const setChildLanguage = (studentId: string, home_language: string) =>
  staffReq(`/students/${studentId}/language`, { method: "PUT", body: JSON.stringify({ home_language }) });
export const teacherClasses = () => staffReq("/teacher/classes");
export const classView = (classId: string, kind: "heatmap" | "stuck" | "alerts") =>
  staffReq(`/teacher/classes/${classId}/${kind}`);
export const reviewQueue = () => staffReq("/teacher/review-queue");
export const decideReview = (id: string, decision: "ok" | "bad") =>
  staffReq(`/teacher/review-queue/${id}`, { method: "POST", body: JSON.stringify({ decision }) });

/** Dev only: a token for a preview guardian or teacher (404 unless DEV_TOOLS is on). */
export async function devStaffToken(role: "parent" | "teacher", scenario?: string) {
  const out = await staffReq("/dev/staff-token", {
    method: "POST",
    body: JSON.stringify({ role, scenario }),
  });
  clearStudent();
  setStaffToken(out.token);
  return out as { token: string; email: string; role: string };
}
