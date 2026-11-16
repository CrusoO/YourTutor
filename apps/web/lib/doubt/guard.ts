import { detectMath } from "./detect";
import { Poly } from "./poly";
import { astSize, maxExponent, normalizeMath, parseExpr } from "./parse";
import type { MathCandidate } from "./types";

/** Input limits (reject before any solving) and the check that keeps a doubt from answering an open practice item. */
export const LIMITS = {
  maxChars: 200,
  maxDigits: 9,
  maxExponent: 12,
  maxNodes: 40,
  maxDepth: 8,
  maxDegree: 4,
  maxCoeffDigits: 18,
} as const;

export type GuardWhy =
  | "too_long"
  | "too_big_number"
  | "huge_exponent"
  | "too_deep"
  | "too_many_terms"
  | "high_degree";
export type GuardResult = { ok: true } | { ok: false; why: GuardWhy };
const bad = (why: GuardWhy): GuardResult => ({ ok: false, why });

/** Before parsing: length, digit runs, exponent size. */
export function guardText(text: string): GuardResult {
  if (text.length > LIMITS.maxChars) return bad("too_long");
  const s = normalizeMath(text);
  for (const run of s.match(/\d+/g) ?? []) if (run.length > LIMITS.maxDigits) return bad("too_big_number");
  if (/\^\s*\([^)]*\^/.test(s)) return bad("huge_exponent");
  for (const m of s.matchAll(/\^\s*\(?\s*([-+]?[^\s^()]*)/g)) {
    const num = /^[-+]?(\d+)$/.exec(m[1]);
    if (!num) return bad("huge_exponent");
    if (num[1].length > 3 || Number(num[1]) > LIMITS.maxExponent) return bad("huge_exponent");
  }
  return { ok: true };
}

/** After detection: tree size, degree, coefficient size. */
export function guardCandidate(c: MathCandidate): GuardResult {
  const texts = [c.lhsText, c.rhsText, c.expr, ...(c.system?.texts ?? [])].filter((t): t is string => !!t);
  for (const t of texts) {
    const parts = t.includes("=") ? t.split("=") : [t];
    for (const part of parts) {
      const p = parseExpr(part, { maxDigits: LIMITS.maxCoeffDigits });
      if (!p.ok) return bad("too_many_terms");
      const size = astSize(p.ast);
      if (size.nodes > LIMITS.maxNodes) return bad("too_many_terms");
      if (size.depth > LIMITS.maxDepth * 2) return bad("too_deep");
      if (maxExponent(p.ast) > LIMITS.maxExponent) return bad("huge_exponent");
    }
  }
  for (const co of [c.lhs, c.rhs].filter((x): x is string[] => !!x)) {
    if (co.length - 1 > LIMITS.maxDegree) return bad("high_degree");
    if (co.some((v) => v.replace(/[^0-9]/g, "").length > LIMITS.maxCoeffDigits)) return bad("too_big_number");
  }
  return { ok: true };
}

// ---- Practice item in play ----------------------------------------------------------------------------------

const NUMBER = /\d+(?:\.\d+)?/g;
const MATH_TOKEN = /^[a-z]$|^[\d()+\-*/^.=a-z]*[\d()+\-*/^.=][\d()+\-*/^.=a-z]*$/;

function compact(text: string): string {
  return text.toLowerCase().replace(/\s+/g, "");
}

/** Each equation in the stem with the words around it dropped, spaces removed (mirror of ask/guard.py). */
export function stemEquations(stem: string): string[] {
  const out: string[] = [];
  for (const part of stem.toLowerCase().split(/[.?!;,](?!\d)\s/)) {
    if (!part.includes("=")) continue;
    const piece = part
      .split(/\s+/)
      .filter((t) => MATH_TOKEN.test(t))
      .join("");
    if (piece.includes("=") && piece.length >= 3) out.push(piece);
  }
  return out;
}

/** Mirror of the first two signals of `targets_current_item`: "stem_expression" or "stem_numbers". */
export function targetsCurrentItem(question: string, stem: string | null): "stem_expression" | "stem_numbers" | null {
  if (!stem) return null;
  const asked = question.toLowerCase();
  const lowerStem = stem.toLowerCase();
  for (const eq of stemEquations(lowerStem)) if (compact(asked).includes(eq)) return "stem_expression";
  const a = new Set(lowerStem.match(NUMBER) ?? []);
  const shared = new Set((asked.match(NUMBER) ?? []).filter((n) => a.has(n)));
  return shared.size >= 2 ? "stem_numbers" : null;
}

function sameProblem(a: MathCandidate, b: MathCandidate): boolean {
  if (a.kind !== b.kind) return false;
  if (a.kind === "poly_eq" && a.lhs && a.rhs && b.lhs && b.rhs) {
    const pa = Poly.parseCoeffs(a.lhs)?.sub(Poly.parseCoeffs(a.rhs) ?? new Poly([]));
    const pb = Poly.parseCoeffs(b.lhs)?.sub(Poly.parseCoeffs(b.rhs) ?? new Poly([]));
    return !!pa && !!pb && pa.isMultipleOf(pb);
  }
  if (a.kind === "linear_system" && a.system && b.system) {
    const norm = (s: string[]) => [...s].sort().join("|");
    return norm(a.system.texts) === norm(b.system.texts);
  }
  return !!a.expr && a.expr === b.expr;
}

/**
 * True when the student's expression is the open practice item's own question. Then the chat gives the usual practice
 * help (no solving here), exactly as the server's Ask guard does. `stems` are the question texts the session holds.
 */
export function routesToPracticeHelp(c: MathCandidate, stems: readonly string[]): boolean {
  for (const stem of stems) {
    if (targetsCurrentItem(c.display, stem) === "stem_expression") return true;
    const pieces = [stem, ...stemEquations(stem)];
    for (const piece of pieces) {
      const found = detectMath(piece);
      if (found.kind === "candidate" && sameProblem(c, found.candidate)) return true;
    }
  }
  return false;
}
