const API =
  typeof window === "undefined"
    ? process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL || "/api";

import type { ActionRules } from "./chat/actions";
import type { FinderRules } from "./chat/finder";
import type { AiBlock, LessonOpeningResult, LessonRestResult, LessonResult } from "./lessons/ai-lesson";
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
  /** The formative grade of an explain-back (never part of mastery): good, partly or not_yet. */
  grade?: string | null;
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

/**
 * Storage that never throws. Order: localStorage, then sessionStorage, then an in-memory map. Some browsers
 * (private mode, blocked site data) make window.localStorage throw on access or on write; the app must still work.
 */
const memory = new Map<string, string>();

const memoryStore: Storage = {
  get length() {
    return memory.size;
  },
  clear: () => memory.clear(),
  getItem: (key) => memory.get(key) ?? null,
  key: (index) => [...memory.keys()][index] ?? null,
  removeItem: (key) => void memory.delete(key),
  setItem: (key, value) => void memory.set(key, String(value)),
};

function usable(pick: () => Storage): Storage | null {
  try {
    const candidate = pick();
    const probe = "yt_probe";
    candidate.setItem(probe, "1");
    candidate.removeItem(probe);
    return candidate;
  } catch {
    return null;
  }
}

/** The one safe browser store: the device, else this tab, else memory. It never throws. */
export function safeStorage(): Storage | null {
  return store();
}

export type StorageMode = "device" | "tab" | "memory";

/** Where sign-in is kept right now: the device, only this tab, or only until the page reloads. */
export function storageMode(): StorageMode {
  if (typeof window === "undefined") return "device";
  if (usable(() => window.localStorage)) return "device";
  return usable(() => window.sessionStorage) ? "tab" : "memory";
}

function store(): Storage | null {
  if (typeof window === "undefined") return null;
  return (
    usable(() => window.localStorage) ?? usable(() => window.sessionStorage) ?? memoryStore
  );
}

/** An anonymous guest is kept for this tab only: closing the tab forgets them. A real sign-in uses the device store. */
function tab(): Storage | null {
  if (typeof window === "undefined") return null;
  return usable(() => window.sessionStorage) ?? memoryStore;
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

async function authedFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const auth = token();
  if (auth) headers.set("Authorization", `Bearer ${auth}`);
  return fetch(`${API}${path}`, { ...init, headers });
}

async function req(path: string, init: RequestInit = {}) {
  const response = await authedFetch(path, init);
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

/** A support line the API may show (config/helplines.yaml). Hours are null until the owner confirms them. */
export type Helpline = { id: string; kind: string; name: string; number: string; hours: string | null; verified: boolean };

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
  | { kind: "refused" | "distress" | "out_of_scope"; message: string; helplines?: Helpline[] }
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
  | { kind: "refused" | "distress" | "out_of_scope"; message: string; reason?: string; helplines?: Helpline[] }
  | { kind: "empty" };

/** The in-depth, first-principles explanation of a typed question. The question is never kept by the page. */
export async function explainQuestion(prompt: string, language: "en" | "hi"): Promise<Explanation> {
  return req("/explain", { method: "POST", body: JSON.stringify({ prompt, language }) });
}

/** The question built as an interactive lesson: hook, predict, widgets, checks, recap (see lib/lessons/ai-lesson.ts). */
export async function explainLesson(prompt: string, language: "en" | "hi"): Promise<LessonResult> {
  return req("/explain/lesson", { method: "POST", body: JSON.stringify({ prompt, language }) });
}

/** Just a hook and a prediction, fast, so the first question is on screen within seconds. */
export async function explainLessonOpening(prompt: string, language: "en" | "hi"): Promise<LessonOpeningResult> {
  return req("/explain/lesson/opening", { method: "POST", body: JSON.stringify({ prompt, language }) });
}

/** The rest of the lesson, written knowing the opening the student has already seen. */
export async function explainLessonRest(prompt: string, language: "en" | "hi", opening: AiBlock[]): Promise<LessonRestResult> {
  return req("/explain/lesson", { method: "POST", body: JSON.stringify({ prompt, language, opening }) });
}

export type GroupLesson = {
  code: string;
  prompt: string;
  language: "en" | "hi";
  blocks: AiBlock[];
  closed: boolean;
  /** Whether this page may offer to send results back (off while there is no age gate to rely on). */
  results_open: boolean;
};

/** A shared lesson, opened by its code. No sign-in and no model: it is the lesson the organiser checked. */
export async function openGroup(code: string): Promise<GroupLesson> {
  return req(`/groups/${encodeURIComponent(code)}`);
}

export type GroupAnswer = { question: string; kind: "predict" | "check"; right: boolean; confidence: "sure" | "unsure" | null; idea: string | null };

/** How the learner did, with no name or account. Sending again replaces the earlier answer. */
export async function sendGroupResults(code: string, items: GroupAnswer[]): Promise<{ accepted: number }> {
  return req(`/groups/${encodeURIComponent(code)}/results`, { method: "POST", body: JSON.stringify({ items }) });
}

export async function publishGroup(prompt: string, language: "en" | "hi", blocks: AiBlock[]): Promise<{ code: string; path: string }> {
  return req("/groups", { method: "POST", body: JSON.stringify({ prompt, language, blocks }) });
}

export type GroupListing = { code: string; path: string; prompt: string; created_at: string; closed: boolean; participants: number };

export async function myGroups(): Promise<{ groups: GroupListing[] }> {
  return req("/groups");
}

export type GroupSummary = {
  code: string;
  prompt: string;
  participants: number;
  minimum: number;
  cell: number;
  ready: boolean;
  questions: { question: string; kind: string; answered: number; wrong: number | null; sure_wrong: number | null; ideas: { idea: string; count: number }[] }[];
};

export async function groupSummary(code: string): Promise<GroupSummary> {
  return req(`/groups/${encodeURIComponent(code)}/summary`);
}

export async function closeGroup(code: string): Promise<{ closed: boolean }> {
  return req(`/groups/${encodeURIComponent(code)}/close`, { method: "POST" });
}

export type TutorTurn = { role: "user" | "assistant"; content: string };
/** What Brownie says when it cannot answer: an authored line and the next choices (ids the client knows). */
export type TutorFallback = { reason: string; text: string; offers: { id: string; label: string }[] };
export type TutorReply =
  | { kind: "reply"; text: string; language?: string }
  | { kind: "unavailable"; reason: string; fallback?: TutorFallback }
  | { kind: "refused" | "distress" | "out_of_scope"; message: string; reason?: string; helplines?: Helpline[] }
  | { kind: "empty" };

/**
 * A short Socratic reply to a follow-up question. The client sends the conversation each time; nothing is kept.
 * With `onDelta` the reply arrives as it is written, one checked sentence at a time; the returned reply is
 * always the final one and replaces whatever was shown (it differs only if the server had to step in).
 */
export async function explainChat(
  prompt: string,
  language: "en" | "hi",
  history: TutorTurn[],
  onDelta?: (text: string) => void,
): Promise<TutorReply> {
  const body = JSON.stringify({ prompt, language, history });
  if (!onDelta) return req("/explain/chat", { method: "POST", body });
  return streamChat(body, onDelta);
}

const DELIM = String.fromCharCode(10, 10); // a blank line ends one server-sent event

async function streamChat(body: string, onDelta: (text: string) => void): Promise<TutorReply> {
  const response = await authedFetch("/explain/chat/stream", { method: "POST", body });
  if (!response.ok) throw new Error((await response.text()) || response.statusText);
  if (!response.body || !(response.headers.get("content-type") || "").includes("text/event-stream")) {
    return response.json(); // a server or proxy that does not stream: the plain reply
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  let result: TutorReply | null = null;
  for (;;) {
    const { done, value } = await reader.read();
    pending += decoder.decode(value, { stream: !done });
    const events = pending.split(DELIM);
    pending = done ? "" : (events.pop() ?? "");
    for (const raw of events) {
      const line = raw.trim();
      if (!line.startsWith("data:")) continue;
      let event: { type?: string; text?: string; result?: TutorReply };
      try {
        event = JSON.parse(line.slice(5));
      } catch {
        continue;
      }
      if (event.type === "delta" && typeof event.text === "string") onDelta(event.text);
      else if (event.type === "final" && event.result) result = event.result;
    }
    if (done) break;
  }
  if (!result) throw new Error("the reply stopped early");
  return result;
}

/** The words that mean a command, matched in the browser on typed text (a GET: no user text is sent). */
export async function getActionRules(language: string): Promise<ActionRules> {
  return req(`/actions/rules?language=${encodeURIComponent(language)}`);
}

/** The learning card a signed-in learner chose to keep in their account (a guest is refused). */
export async function keepLessonRecords(records: unknown[]): Promise<{ saved: number }> {
  return req("/students/me/lesson-records", { method: "POST", body: JSON.stringify({ records }) });
}

export async function clearLessonRecords(): Promise<{ cleared: boolean }> {
  return req("/students/me/lesson-records", { method: "DELETE" });
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
  if (!response.ok) throw await apiError(response);
  return response.json();
}

/** A failed API call. `code` is the API's machine code when it sent one, e.g. "email_unavailable". */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string = "",
  ) {
    super(message);
  }
}

export async function apiError(response: Response): Promise<ApiError> {
  const text = await response.text();
  let code = "";
  try {
    const detail = JSON.parse(text)?.detail;
    if (detail && typeof detail === "object" && typeof detail.code === "string") code = detail.code;
  } catch {
    /* not JSON */
  }
  return new ApiError(text || response.statusText, response.status, code);
}

/** True when the sign-in code could not be sent (the API answered 503 email_unavailable). */
export function isEmailUnavailable(error: unknown): boolean {
  return error instanceof ApiError && error.code === "email_unavailable";
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
