import type { MathCandidate, RuleId, Step } from "./types";
import { RULE_IDS } from "./rules";

/**
 * Optional server check (ADR 0005, Stage 2). This module holds no network code: the caller passes a `transport`
 * (the API module owns the one network call). It builds the only thing that may leave the device, `doubt-expr/1`: exact numbers and
 * two enumerated words, never the student's text, the display string or any letter. It validates the object again
 * just before it is handed over, and it reads the reply defensively (the server is trusted for the kernel verdict, not
 * for the shape of its JSON).
 */

const NUMBER = /^-?[0-9]{1,9}(\/[0-9]{1,9})?$/;
const MAX_SIDE = 5;

export type DoubtExprWire =
  | { schema: "doubt-expr/1"; kind: "poly_eq"; lhs: string[]; rhs: string[] }
  | { schema: "doubt-expr/1"; kind: "linear_system"; system: { coeffs: string[][]; consts: string[] } };

export type ServerAnswer =
  | { kind: "values"; values: string[] }
  | { kind: "pair"; x: string; y: string }
  | { kind: "none" };

export type ServerResult =
  | { verified: true; answer: ServerAnswer; steps: Step[] }
  | { verified: false; reason: string };

export type ServerRefusal = "disabled" | "consent" | "rate" | "invalid" | "failed";

export type Outcome = { ok: true; result: ServerResult } | { ok: false; refusal: ServerRefusal };

/** A server call: POST this JSON text to /doubt/solve, return the status and parsed JSON (null when not JSON). */
export type Transport = (body: string) => Promise<{ status: number; json: unknown }>;

const numbersOk = (xs: readonly string[]): boolean => xs.every((s) => typeof s === "string" && NUMBER.test(s) && !/\/0+$/.test(s));

/** The wire object for a candidate, or null when this kind is not sent (arithmetic and simplifying stay on the device). */
export function toDoubtExpr(c: MathCandidate): DoubtExprWire | null {
  let wire: DoubtExprWire | null = null;
  if (c.kind === "poly_eq" && c.lhs && c.rhs) {
    wire = { schema: "doubt-expr/1", kind: "poly_eq", lhs: [...c.lhs], rhs: [...c.rhs] };
  } else if (c.kind === "linear_system" && c.system && c.system.coeffs.length === 2) {
    wire = {
      schema: "doubt-expr/1",
      kind: "linear_system",
      system: { coeffs: c.system.coeffs.map((r) => [...r]), consts: [...c.system.consts] },
    };
  }
  return wire && valid(wire) ? wire : null;
}

export function valid(w: DoubtExprWire): boolean {
  if (w.kind === "poly_eq") {
    return [w.lhs, w.rhs].every((s) => s.length >= 1 && s.length <= MAX_SIDE && numbersOk(s));
  }
  const { coeffs, consts } = w.system;
  return coeffs.length === 2 && coeffs.every((r) => r.length === 2 && numbersOk(r)) && consts.length === 2 && numbersOk(consts);
}

const isStr = (v: unknown): v is string => typeof v === "string";
const isStrArray = (v: unknown): v is string[] => Array.isArray(v) && v.every(isStr);

function readAnswer(a: unknown): ServerAnswer | null {
  if (!a || typeof a !== "object") return null;
  const o = a as Record<string, unknown>;
  if (o.kind === "values" && isStrArray(o.values)) return { kind: "values", values: o.values };
  if (o.kind === "pair" && isStr(o.x) && isStr(o.y)) return { kind: "pair", x: o.x, y: o.y };
  if (o.kind === "none") return { kind: "none" };
  return null;
}

function readSteps(s: unknown): Step[] | null {
  if (!Array.isArray(s)) return null;
  const known = new Set<string>(RULE_IDS);
  const out: Step[] = [];
  for (const raw of s) {
    if (!raw || typeof raw !== "object") return null;
    const o = raw as Record<string, unknown>;
    if (!isStr(o.rule) || !known.has(o.rule) || !isStr(o.before) || !isStr(o.after)) return null;
    const args: Record<string, string> = {};
    for (const [k, v] of Object.entries((o.args as Record<string, unknown>) ?? {})) if (isStr(v)) args[k] = v;
    out.push({ rule: o.rule as RuleId, args, before: o.before, after: o.after });
  }
  return out;
}

/**
 * Read a `doubt-result/1` reply. Only a reply that says verified, carries the kernel's own proof block and parses
 * cleanly counts as verified; anything else is an honest "could not check".
 */
export function readResult(json: unknown): ServerResult {
  const o = json && typeof json === "object" ? (json as Record<string, unknown>) : null;
  if (!o || o.schema !== "doubt-result/1") return { verified: false, reason: "bad_reply" };
  if (o.verified !== true) return { verified: false, reason: isStr(o.reason) ? o.reason : "not_verified" };
  const proof = o.proof as Record<string, unknown> | null;
  const answer = readAnswer(o.answer);
  const steps = readSteps(o.steps);
  if (o.label !== "checked_by_code" || !proof || !isStr(proof.kernel) || !answer || !steps) {
    return { verified: false, reason: "bad_reply" };
  }
  return { verified: true, answer, steps };
}

export function refusalOf(status: number, json: unknown): ServerRefusal {
  const code = (json as { detail?: { code?: unknown } } | null)?.detail?.code;
  if (status === 404) return "disabled";
  if (status === 429) return "rate";
  if (status === 403) return code === "math_check_consent_required" ? "consent" : "disabled";
  if (status === 413 || status === 422) return "invalid";
  return "failed";
}

/**
 * Send one confirmed candidate. Call it only after the student has confirmed the reading and tapped the explicit
 * "check on the server" control. Returns without calling the transport when the candidate cannot be expressed.
 */
export async function checkOnServer(c: MathCandidate, transport: Transport): Promise<Outcome | null> {
  const wire = toDoubtExpr(c);
  if (!wire) return null;
  try {
    const { status, json } = await transport(JSON.stringify(wire));
    if (status >= 200 && status < 300) return { ok: true, result: readResult(json) };
    return { ok: false, refusal: refusalOf(status, json) };
  } catch {
    return { ok: false, refusal: "failed" };
  }
}
