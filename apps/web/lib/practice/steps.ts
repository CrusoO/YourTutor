/**
 * Step entry for quadratics practice (practice loop, slice 1). Pure helpers: which equation a stem holds, what a line
 * state looks like on screen, the keypad, and the one request body. Nothing here touches the network or storage.
 */

export type LineState = "ok" | "wrong_step" | "unreadable" | "skipped";
export type Verdict = "correct" | "wrong" | "not_final" | "unreadable" | "none" | "unchecked";

export type StepReport = {
  supported: boolean;
  lines: { state: LineState; hint_key?: string }[];
  verdict: Verdict;
};

export type LineView = {
  tone: "good" | "try" | "muted";
  icon: "check" | "return" | "question" | "dots";
  /** The key of the words in the session copy; the words, not the colour, carry the meaning. */
  copyKey: "stepOk" | "stepWrong" | "stepUnreadable" | "stepSkipped";
};

const VIEWS: Record<LineState, LineView> = {
  ok: { tone: "good", icon: "check", copyKey: "stepOk" },
  wrong_step: { tone: "try", icon: "return", copyKey: "stepWrong" },
  unreadable: { tone: "muted", icon: "question", copyKey: "stepUnreadable" },
  skipped: { tone: "muted", icon: "dots", copyKey: "stepSkipped" },
};

/** An unknown state from a newer or hostile server reads as "not checked yet", never as correct. */
export function lineView(state: string): LineView {
  return VIEWS[state as LineState] ?? VIEWS.skipped;
}

export const MINUS = "−";
export const MAX_LINES = 12;

export type Key = { id: string; label: string; insert: string };

const digits = "0123456789".split("").map((d) => ({ id: `d${d}`, label: d, insert: d }));
export const KEYS: Key[] = [
  ...digits,
  { id: "x", label: "x", insert: "x" },
  { id: "x2", label: "x²", insert: "x^2" },
  { id: "plus", label: "+", insert: " + " },
  { id: "minus", label: MINUS, insert: ` ${MINUS} ` },
  { id: "open", label: "(", insert: "(" },
  { id: "close", label: ")", insert: ")" },
  { id: "eq", label: "=", insert: " = " },
  { id: "or", label: "or", insert: " or " },
];

export type Edit = { value: string; caret: number };

/** Put `text` at the caret (or over the selection). */
export function insertAt(value: string, start: number, end: number, text: string): Edit {
  const a = Math.max(0, Math.min(start, value.length));
  const b = Math.max(a, Math.min(end, value.length));
  return { value: value.slice(0, a) + text + value.slice(b), caret: a + text.length };
}

/** Delete the selection, or the character before the caret. */
export function backspaceAt(value: string, start: number, end: number): Edit {
  const a = Math.max(0, Math.min(start, value.length));
  const b = Math.max(a, Math.min(end, value.length));
  if (b > a) return { value: value.slice(0, a) + value.slice(b), caret: a };
  if (a === 0) return { value, caret: 0 };
  return { value: value.slice(0, a - 1) + value.slice(a), caret: a - 1 };
}

const EQ_CHAR = /[0-9x²³^+\-−–*/().\s]/;
const QUAD_SKILL = "MATH.ALG.QUAD.";

/**
 * The one equation in a quadratics question's stem ("... the equation x² - 3x = 0?"), or null. Step entry is offered
 * only for a quadratics skill and only when the stem holds exactly one equation in x.
 */
export function equationFromStem(stem: string | null | undefined, skillIds?: string[] | null): string | null {
  if (!stem || !(skillIds ?? []).some((s) => s.startsWith(QUAD_SKILL))) return null;
  const text = stem.replace(/ /g, " ");
  const at = text.indexOf("=");
  if (at < 0 || text.indexOf("=", at + 1) >= 0) return null;
  let a = at;
  while (a > 0 && EQ_CHAR.test(text[a - 1])) a--;
  let b = at + 1;
  while (b < text.length && EQ_CHAR.test(text[b])) b++;
  const eq = text.slice(a, b).trim().replace(/^[.\s]+|[.\s]+$/g, "");
  const [left, right] = eq.split("=");
  if (!left?.trim() || !right?.trim() || !/x/.test(eq) || eq.length > 64) return null;
  return eq;
}

/** The JSON text of a `step-check/1` request. Only the equation and the lines the student chose to check. */
export function stepRequest(question: string, lines: string[]): string {
  return JSON.stringify({ schema: "step-check/1", question, lines });
}

export type Refusal = "disabled" | "consent" | "rate" | "invalid" | "failed";

export function refusalOf(status: number, json: unknown): Refusal {
  const code = (json as { detail?: { code?: unknown } } | null)?.detail?.code;
  if (status === 404) return "disabled";
  if (status === 429) return "rate";
  if (status === 403) return code === "math_check_consent_required" ? "consent" : "disabled";
  if (status === 413 || status === 422) return "invalid";
  return "failed";
}

const STATES = new Set<string>(["ok", "wrong_step", "unreadable", "skipped"]);
const VERDICTS = new Set<string>(["correct", "wrong", "not_final", "unreadable", "none", "unchecked"]);

/** Read the server's answer defensively; anything odd gives null (shown as "could not check"). */
export function readReport(json: unknown): StepReport | null {
  const o = json as { supported?: unknown; lines?: unknown; verdict?: unknown } | null;
  if (!o || !Array.isArray(o.lines) || typeof o.verdict !== "string" || !VERDICTS.has(o.verdict)) return null;
  const lines: StepReport["lines"] = [];
  for (const l of o.lines) {
    const state = (l as { state?: unknown } | null)?.state;
    if (typeof state !== "string" || !STATES.has(state)) return null;
    lines.push({ state: state as LineState });
  }
  return { supported: o.supported !== false, lines, verdict: o.verdict as Verdict };
}
