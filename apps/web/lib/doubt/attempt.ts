import { ATTEMPT_COPY } from "./copy.en";
import { Frac } from "./frac";
import { wordsToDigits } from "./leak";
import { evalNum, normalizeMath, parseEquation, parseExpr, renameAst, toPoly } from "./parse";
import { Poly } from "./poly";
import { solutionSet } from "./solve";
import { type QNum, qEq, qToString } from "./surd";
import type { Ast, MathCandidate, Solution } from "./types";

/**
 * Checks what the student writes against the problem, exactly. Two jobs:
 *  - checkAnswer: is the value (or the set of values) right? Lost and extra roots are caught by comparing sets.
 *  - checkStep: is the student's next line equivalent to the line above AND a legal move?
 * Evidence is always a substitution the student can repeat; the checker never prints the answer.
 */

export type AttemptVerdict = "correct" | "incomplete" | "has_wrong_value" | "wrong" | "unreadable";
export type AttemptResult = { verdict: AttemptVerdict; text: string; evidence: string[]; missing?: number };

const SPLIT = /\s+or\s+|\s+and\s+|\s+aur\s+|[,;]|\n/;

function clean(text: string): string {
  return wordsToDigits(normalizeMath(text));
}

export type Parsed = { letter: string | null; value: QNum };

/** "3", "x = 3", "x=2 or x=3", "2, 3", "-3/2+1/2√5". Null when any part is not exact maths. */
export function parseStudentValues(text: string, letters: string[]): Parsed[] | null {
  let body = clean(text).trim();
  if (/^\([^()]*,[^()]*\)$/.test(body)) body = body.slice(1, -1); // an ordered pair "(3, 2)"
  const parts = body.split(SPLIT).map((p) => p.trim()).filter(Boolean);
  if (parts.length === 0 || parts.length > 6) return null;
  const out: Parsed[] = [];
  for (const raw of parts) {
    const m = new RegExp(`^(?:(${[...letters, "answer", "solution", "root"].join("|")})\\s*(?:=|is|:)\\s*)?(.+)$`).exec(raw);
    if (!m) return null;
    const parsed = parseExpr(m[2].replace(/^\(\s*([^()]*)\s*\)$/, "$1"));
    if (!parsed.ok) return null;
    const v = evalNum(parsed.ast);
    if (!v) return null;
    out.push({ letter: m[1] && letters.includes(m[1]) ? m[1] : null, value: v });
  }
  return out;
}

function relationsOf(c: MathCandidate): { l: Ast; r: Ast }[] {
  const map = new Map([
    ["x", c.variable[0] ?? "x"],
    ["y", c.variable[1] ?? "y"],
  ]);
  const texts: string[] = [];
  if (c.lhsText !== undefined && c.rhsText !== undefined) texts.push(`${c.lhsText}=${c.rhsText}`);
  if (c.system) texts.push(...c.system.texts);
  const out: { l: Ast; r: Ast }[] = [];
  for (const t of texts) {
    const eq = parseEquation(t);
    if (eq.ok) out.push({ l: renameAst(eq.lhs, map), r: renameAst(eq.rhs, map) });
  }
  return out;
}

/** Put values back into every equation of the problem, exactly. */
export function substituteCheck(
  c: MathCandidate,
  env: Map<string, QNum>,
): { ok: boolean; sides: { l: string; r: string; ok: boolean }[] } | null {
  const sides: { l: string; r: string; ok: boolean }[] = [];
  let ok = true;
  for (const rel of relationsOf(c)) {
    const l = evalNum(rel.l, env);
    const r = evalNum(rel.r, env);
    if (!l || !r) return null;
    const same = qEq(l, r);
    sides.push({ l: qToString(l), r: qToString(r), ok: same });
    if (!same) ok = false;
  }
  return sides.length ? { ok, sides } : null;
}

const NONE_WORDS = /^(no solution|none|no real solution|no real roots|nothing|never)$/;
const ALL_WORDS = /^(all|every|any|all values|every value|infinite|infinitely many|always|identity)$/;

export function checkAnswer(c: MathCandidate, sol: Solution, text: string): AttemptResult {
  const unreadable: AttemptResult = { verdict: "unreadable", text: ATTEMPT_COPY.unreadable, evidence: [] };
  const norm = clean(text).trim();
  if (sol.status === "unsupported") return unreadable;
  if (c.kind === "poly_eq" || c.kind === "linear_system") {
    if (NONE_WORDS.test(norm)) {
      return sol.status === "no_solution"
        ? { verdict: "correct", text: ATTEMPT_COPY.noSolutionRight, evidence: [] }
        : { verdict: "wrong", text: ATTEMPT_COPY.wrong, evidence: [] };
    }
    if (ALL_WORDS.test(norm)) {
      return sol.status === "identity"
        ? { verdict: "correct", text: ATTEMPT_COPY.identityRight, evidence: [] }
        : { verdict: "wrong", text: ATTEMPT_COPY.wrong, evidence: [] };
    }
  }
  if (c.kind === "arith") {
    const p = parseStudentValues(text, []);
    if (!p || p.length !== 1) return unreadable;
    const right = qEq(p[0].value, sol.exact[0]);
    return right
      ? { verdict: "correct", text: ATTEMPT_COPY.arithRight, evidence: [] }
      : { verdict: "wrong", text: ATTEMPT_COPY.arithWrong(qToString(p[0].value)), evidence: [] };
  }
  if (c.kind === "poly_simplify") {
    const parsed = parseExpr(clean(text));
    const mine = sol.answer.kind === "expr" ? Poly.parseCoeffs(sol.answer.coeffs) : null;
    if (!parsed.ok || !mine) return unreadable;
    const theirs = toPoly(renameAst(parsed.ast, new Map([[c.variable, "x"]])), "x");
    if (!theirs.ok) return unreadable;
    return theirs.poly.equals(mine)
      ? { verdict: "correct", text: ATTEMPT_COPY.correct, evidence: [] }
      : { verdict: "wrong", text: ATTEMPT_COPY.wrong, evidence: [] };
  }

  const letters = c.kind === "linear_system" ? [c.variable[0], c.variable[1]] : [c.variable];
  const parsed = parseStudentValues(text, letters);
  if (!parsed) return unreadable;

  if (c.kind === "linear_system") {
    if (parsed.length !== 2) return unreadable;
    const env = new Map<string, QNum>();
    parsed.forEach((p, i) => env.set(p.letter ?? letters[i], p.value));
    if (env.size !== 2) return unreadable;
    const chk = substituteCheck(c, env);
    if (!chk) return unreadable;
    const evidence = chk.sides.map((s, i) => (s.ok ? `Equation ${i + 1} works: ${s.l} = ${s.r}.` : `Equation ${i + 1}: the left side is ${s.l} but the right side is ${s.r}.`));
    return chk.ok && sol.status === "solved"
      ? { verdict: "correct", text: ATTEMPT_COPY.correct, evidence }
      : { verdict: "wrong", text: ATTEMPT_COPY.wrong, evidence };
  }

  // One unknown: compare the set of values with the exact roots.
  const evidence: string[] = [];
  const good: QNum[] = [];
  let bad = 0;
  for (const p of parsed) {
    const chk = substituteCheck(c, new Map([[c.variable, p.value]]));
    if (!chk) return unreadable;
    const shown = qToString(p.value);
    const { l, r } = chk.sides[0];
    if (chk.ok) {
      evidence.push(ATTEMPT_COPY.works(c.variable, shown, l, r));
      if (!good.some((g) => qEq(g, p.value))) good.push(p.value);
    } else {
      evidence.push(ATTEMPT_COPY.fails(c.variable, shown, l, r));
      bad++;
    }
  }
  if (bad > 0) {
    return { verdict: good.length ? "has_wrong_value" : "wrong", text: good.length ? ATTEMPT_COPY.hasWrong : ATTEMPT_COPY.wrong, evidence };
  }
  const missing = sol.exact.filter((root) => !good.some((g) => qEq(g, root))).length;
  if (missing > 0) return { verdict: "incomplete", text: ATTEMPT_COPY.incomplete(missing), evidence, missing };
  return { verdict: "correct", text: ATTEMPT_COPY.correct, evidence };
}

// ---- Steps ----------------------------------------------------------------------------------------------------

export type StepVerdict =
  | "ok"
  | "equivalent_not_a_move"
  | "lost_roots"
  | "extra_roots"
  | "not_equivalent"
  | "unreadable";
export type StepResult = { verdict: StepVerdict; equivalent: boolean; legal: boolean; text: string };

type Side = { polys: { l: Poly; r: Poly }[] };

function readLine(text: string, letter: string): Side | null {
  const pieces = clean(text).split(/\s+or\s+/);
  const polys: { l: Poly; r: Poly }[] = [];
  for (const piece of pieces) {
    const eq = parseEquation(piece);
    if (!eq.ok) return null;
    const l = toPoly(eq.lhs, letter);
    const r = toPoly(eq.rhs, letter);
    if (!l.ok || !r.ok) return null;
    polys.push({ l: l.poly, r: r.poly });
  }
  return { polys };
}

function setOf(side: Side): { all: boolean; none: boolean; keys: Set<string> } | null {
  const keys = new Set<string>();
  let all = false;
  for (const { l, r } of side.polys) {
    const s = solutionSet(l, r);
    if (!s) return null;
    if (s.status === "identity") all = true;
    for (const root of s.roots) keys.add(qToString(root));
  }
  return { all, none: !all && keys.size === 0, keys };
}

function diffProduct(side: Side): Poly {
  return side.polys.reduce((acc, { l, r }) => acc.mul(l.sub(r)), Poly.constant(Frac.ONE));
}

/** Is `next` equivalent to `previous` (same solutions, none lost or gained) and one legal balanced move? */
export function checkStep(c: MathCandidate, previous: string, next: string): StepResult {
  const bad: StepResult = { verdict: "unreadable", equivalent: false, legal: false, text: ATTEMPT_COPY.stepUnreadable };
  if (c.kind !== "poly_eq") return bad;
  const letter = c.variable;
  const a = readLine(previous, letter);
  const b = readLine(next, letter);
  if (!a || !b) return bad;
  const sa = setOf(a);
  const sb = setOf(b);
  const legal = diffProduct(b).isMultipleOf(diffProduct(a));
  if (!sa || !sb) {
    return legal
      ? { verdict: "ok", equivalent: true, legal, text: ATTEMPT_COPY.stepOk }
      : { verdict: "not_equivalent", equivalent: false, legal, text: ATTEMPT_COPY.stepNotEquivalent };
  }
  const subset = (x: Set<string>, y: Set<string>) => [...x].every((k) => y.has(k));
  const same = sa.all === sb.all && sa.keys.size === sb.keys.size && subset(sa.keys, sb.keys);
  if (same) {
    return legal
      ? { verdict: "ok", equivalent: true, legal: true, text: ATTEMPT_COPY.stepOk }
      : { verdict: "equivalent_not_a_move", equivalent: true, legal: false, text: ATTEMPT_COPY.stepSkipped };
  }
  const lost = !sb.all && (sa.all || [...sa.keys].some((k) => !sb.keys.has(k)));
  const extra = !sa.all && (sb.all || [...sb.keys].some((k) => !sa.keys.has(k)));
  if (lost && !extra) return { verdict: "lost_roots", equivalent: false, legal: false, text: ATTEMPT_COPY.stepLost };
  if (extra && !lost) return { verdict: "extra_roots", equivalent: false, legal: false, text: ATTEMPT_COPY.stepExtra };
  return { verdict: "not_equivalent", equivalent: false, legal: false, text: ATTEMPT_COPY.stepNotEquivalent };
}
