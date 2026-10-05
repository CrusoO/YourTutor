const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ActionPayload = {
  type: string;
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

/** Dev only: the API answers 404 unless DEV_TOOLS and ALLOW_DRAFT_CONTENT are on. */
export async function listDevScenarios(): Promise<{ scenarios: DevScenario[] }> {
  return req("/dev/scenarios");
}

export async function startSession(type: string, sid: string): Promise<SessionView> {
  return req("/sessions", {
    method: "POST",
    body: JSON.stringify({ student_id: sid, type }),
  });
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
