import { ApiError, apiError, authFetch, staffReq } from "./api";

const API =
  typeof window === "undefined"
    ? process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL || "/api";

export type CatalogItem = { id: string; required: boolean; scope: string | null };
export type Catalog = { role: string; version: string; items: CatalogItem[] };
export type MyAgreements = {
  version: string;
  agreements: { role: string; version: string; items: string[]; granted_at: string; complete: boolean }[];
  needed: string[];
};
export type AuthOptions = { phone_signin: boolean; child_profiles: boolean };

/** A call with no sign-in (the catalog, the options, the guardian's link): never sends a token. */
async function open(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const response = await fetch(`${API}${path}`, { ...init, headers });
  if (!response.ok) throw await apiError(response);
  return response.json();
}

export const getCatalog = (role: string): Promise<Catalog> => open(`/agreements/${role}`);
export const getAuthOptions = (): Promise<AuthOptions> => open("/auth/options");
export const myAgreements = (): Promise<MyAgreements> => staffReq("/agreements/me");
export const acceptAgreement = (role: string, version: string, items: string[]): Promise<MyAgreements> =>
  staffReq(`/agreements/${role}`, { method: "POST", body: JSON.stringify({ version, items }) });
export const withdrawItem = (role: string, item: string): Promise<MyAgreements> =>
  staffReq(`/agreements/${role}/withdraw`, { method: "POST", body: JSON.stringify({ item }) });

export type AdultStart = {
  version: string;
  accepted: string[];
  declared_adult: boolean | null;
  birth_year: number | null;
  grade: number;
  board: string;
};
export const startAdult = (body: AdultStart): Promise<{ student_id: string; token: string }> =>
  staffReq("/adult/start", { method: "POST", body: JSON.stringify(body) });

/** A returning adult learner: a learner session for their own profile (404 when they have not set one up yet). */
export const adultSession = (): Promise<{ student_id: string; token: string }> =>
  staffReq("/adult/session", { method: "POST" });

export type ChildStart = {
  nickname: string;
  curriculum_id: string;
  grade: number;
  home_language: string;
  guardian_contact: string;
  acknowledged: string[];
  device_timezone?: string;
};
export const startChild = (body: ChildStart): Promise<{ student_id: string; token: string; state: string }> =>
  open("/children/start", { method: "POST", body: JSON.stringify(body) });

export type ChildStatus = { state: "pending" | "expired" | "approved" | "none"; display_name?: string };
export async function childStatus(): Promise<ChildStatus> {
  const response = await authFetch("/children/me/status", { headers: { "Content-Type": "application/json" } });
  if (!response.ok) throw await apiError(response);
  return response.json();
}
export async function resendChildLink(): Promise<void> {
  const response = await authFetch("/children/me/resend", { method: "POST", headers: { "Content-Type": "application/json" } });
  if (!response.ok) throw await apiError(response);
}

export type ApprovalView = {
  nickname: string;
  grade: number;
  curriculum_id: string;
  expires_at: string;
  agreement: Catalog;
};
export const lookupApproval = (token: string): Promise<ApprovalView> =>
  open("/approvals/lookup", { method: "POST", body: JSON.stringify({ token }) });
export const approveChild = (body: {
  token: string;
  version: string;
  accepted: string[];
  grade?: number;
  curriculum_id?: string;
}): Promise<{ access_token: string; student_id: string; display_name: string }> =>
  open("/approvals/approve", { method: "POST", body: JSON.stringify(body) });
export const declineChild = (token: string): Promise<{ status: string }> =>
  open("/approvals/decline", { method: "POST", body: JSON.stringify({ token }) });

export const makeLoginDetails = (studentId: string): Promise<{ username: string; pin: string }> =>
  staffReq(`/students/${studentId}/login-details`, { method: "POST" });

export { ApiError };
