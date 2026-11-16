import { Frac } from "./frac";
import { Poly } from "./poly";
import { evalNum, normalizeMath, parseEquation, parseExpr, renameAst, toPoly } from "./parse";
import { type QNum, qApprox, qEq, qNeg, qRat } from "./surd";
import type { Ast, MathCandidate, Solution } from "./types";

/**
 * Deterministic answer-withholding filter. Exact fractions only (no SymPy, no floats). It reads the hint text the
 * student would see, in whatever disguise, and says whether it gives away a root or the final value.
 *
 * Levels 1 to 3 must never contain a root or the final value. Level 1 and 2 may only use numbers that are in the
 * problem itself; level 3 may also show the first worked state. Level 4 is the full answer: never filtered.
 */

export type AnswerSet = {
  /** The student's unknown letters (lower case). */
  letters: string[];
  /** Every answer value: roots, the numeric result, or x and y. */
  values: QNum[];
  /** Each way of assigning the letters that solves the problem. */
  assignments: Map<string, QNum>[];
  /** Absolute values of every number written in the problem. */
  given: Frac[];
  /** The problem's own equations, in the student's letters. */
  relations: { l: Ast; r: Ast }[];
  /** poly_simplify: the simplified result, and the expression as given. */
  resultPoly?: Poly;
  givenPoly?: Poly;
};

export type LeakReason =
  | "literal"
  | "derived_span"
  | "assertion"
  | "solved_form"
  | "later_state"
  | "surd_approx"
  | "derived_number"
  | "result_expression";
export type LeakVerdict = { leaks: boolean; reasons: LeakReason[] };

function collectNums(a: Ast, into: Frac[]): void {
  if (a.t === "num") into.push(a.v.abs());
  else if (a.t === "neg" || a.t === "sqrt") collectNums(a.a, into);
  else if (a.t === "bin") {
    collectNums(a.a, into);
    collectNums(a.b, into);
  }
}

export function answerSetFor(c: MathCandidate, sol: Solution): AnswerSet {
  const letters = c.kind === "linear_system" ? [c.variable[0], c.variable[1]] : c.kind === "arith" ? [] : [c.variable];
  const map = new Map([
    ["x", letters[0] ?? "x"],
    ["y", letters[1] ?? "y"],
  ]);
  const texts: string[] = [];
  if (c.lhsText !== undefined && c.rhsText !== undefined) texts.push(`${c.lhsText}=${c.rhsText}`);
  if (c.expr) texts.push(c.expr);
  if (c.system) texts.push(...c.system.texts);
  const relations: { l: Ast; r: Ast }[] = [];
  const nums: Frac[] = [];
  let givenPoly: Poly | undefined;
  for (const t of texts) {
    if (t.includes("=")) {
      const eq = parseEquation(t);
      if (eq.ok) {
        relations.push({ l: renameAst(eq.lhs, map), r: renameAst(eq.rhs, map) });
        collectNums(eq.lhs, nums);
        collectNums(eq.rhs, nums);
      }
    } else {
      const e = parseExpr(t);
      if (e.ok) {
        collectNums(e.ast, nums);
        const p = toPoly(e.ast, "x");
        if (p.ok) givenPoly = p.poly;
      }
    }
  }
  if (c.claimed) {
    const v = Frac.parse(c.claimed);
    if (v) nums.push(v.abs());
  }
  const assignments: Map<string, QNum>[] = [];
  if (c.kind === "linear_system") assignments.push(new Map(letters.map((l, i) => [l, sol.exact[i]])));
  else if (c.kind === "poly_eq") for (const r of sol.exact) assignments.push(new Map([[letters[0], r]]));
  const resultPoly =
    sol.answer.kind === "expr" ? Poly.parseCoeffs(sol.answer.coeffs) ?? undefined : undefined;
  return { letters, values: sol.exact, assignments, given: nums, relations, resultPoly, givenPoly };
}

// ---- Number words -------------------------------------------------------------------------------------------

const UNITS: Record<string, number> = {
  zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11,
  twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
  twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90,
};
const NW = [...Object.keys(UNITS), "hundred"].join("|");
const NUMBER_RUN = new RegExp(`\\b(?:(minus|negative)\\s+)?((?:${NW})(?:[\\s-]+(?:and\\s+)?(?:${NW}))*)\\b`, "g");

/** English number words become digits ("minus twenty-one" -> "-21"; "half" -> "1/2"). */
export function wordsToDigits(s: string): string {
  const out = s.replace(NUMBER_RUN, (_m, neg: string | undefined, run: string) => {
    let total = 0;
    let cur = 0;
    for (const w of run.split(/[\s-]+/)) {
      if (w === "and") continue;
      if (w === "hundred") cur = (cur === 0 ? 1 : cur) * 100;
      else {
        total += cur;
        cur = UNITS[w];
        if (cur >= 20 || cur === 0) {
          total += cur;
          cur = 0;
        }
      }
    }
    return ` ${neg ? "-" : ""}${total + cur} `;
  });
  return out.replace(/\b(?:a|one)?\s*half\b/g, " (1/2) ");
}

// ---- Tokens and spans ---------------------------------------------------------------------------------------

type Tok =
  | { k: "num"; v: Frac; pct: boolean; raw: string; decimals: number }
  | { k: "var" | "op" | "word"; raw: string }
  | { k: "brk"; raw: string };

function tokenize(s: string, letters: string[]): Tok[] {
  const out: Tok[] = [];
  let i = 0;
  while (i < s.length) {
    const ch = s[i];
    if (/\s/.test(ch)) {
      out.push({ k: "brk", raw: " " });
      i++;
    } else if (/[0-9]/.test(ch) || (ch === "." && /[0-9]/.test(s[i + 1] ?? "") && !/[0-9]/.test(s[i - 1] ?? ""))) {
      let j = i;
      while (/[0-9]/.test(s[j] ?? "")) j++;
      let decimals = 0;
      if (s[j] === "." && /[0-9]/.test(s[j + 1] ?? "")) {
        j++;
        const st = j;
        while (/[0-9]/.test(s[j] ?? "")) j++;
        decimals = j - st;
      }
      const raw = s.slice(i, j);
      const v = Frac.parse(raw.startsWith(".") ? `0${raw}` : raw);
      let pct = false;
      if (s[j] === "%") {
        pct = true;
        j++;
      }
      if (v) out.push({ k: "num", v, pct, raw, decimals });
      i = j;
    } else if (/[a-z]/.test(ch)) {
      let j = i;
      while (/[a-z]/.test(s[j] ?? "")) j++;
      const w = s.slice(i, j);
      if (w === "sqrt") out.push({ k: "op", raw: "√" });
      else if (w.length === 1 && letters.includes(w)) out.push({ k: "var", raw: w });
      else out.push({ k: "word", raw: w });
      i = j;
    } else if ("+-*/^()=√".includes(ch)) {
      out.push({ k: "op", raw: ch });
      i++;
    } else if (/\p{L}/u.test(ch)) {
      out.push({ k: "word", raw: ch });
      i++;
    } else {
      out.push({ k: "brk", raw: ch });
      i++;
    }
  }
  return out;
}

/** Maximal runs of maths tokens (numbers, the unknown, operators), cut at words, punctuation and "3 4". */
function spansOf(toks: Tok[]): string[] {
  const spans: string[] = [];
  let cur: string[] = [];
  let lastOperand = false;
  let sawSpace = false;
  const flush = () => {
    if (cur.length) spans.push(cur.join(" "));
    cur = [];
    lastOperand = false;
    sawSpace = false;
  };
  for (const t of toks) {
    if (t.k === "brk") {
      if (t.raw === " ") sawSpace = true;
      else flush();
      continue;
    }
    if (t.k === "word") {
      flush();
      continue;
    }
    const operand = t.k === "num" || t.k === "var";
    if (operand && lastOperand && sawSpace && t.k === "num") flush();
    cur.push(t.k === "num" ? t.raw : t.raw);
    lastOperand = operand || (t.k === "op" && t.raw === ")");
    sawSpace = false;
  }
  flush();
  return spans;
}

function sub(a: Ast, into: Ast[]): void {
  if (a.t === "num" || a.t === "var") return;
  into.push(a);
  if (a.t === "neg" || a.t === "sqrt") sub(a.a, into);
  else if (a.t === "bin") {
    sub(a.a, into);
    sub(a.b, into);
  }
}

function matchesAnswer(v: QNum, a: AnswerSet): boolean {
  return a.values.some((x) => qEq(v, x) || qEq(v, qNeg(x)));
}
function isGiven(v: Frac, a: AnswerSet): boolean {
  return a.given.some((g) => g.eq(v.abs()));
}

const SAMPLES = [7, 11, -5, 13];
function samplesFor(letters: string[], j: number): Map<string, QNum> {
  return new Map(letters.map((l, i) => [l, qRat(Frac.of(SAMPLES[(j + i) % SAMPLES.length]))]));
}

function sameRelation(r1: { l: Ast; r: Ast }, r2: { l: Ast; r: Ast }, letters: string[]): boolean {
  const pts: Map<string, QNum>[] = [];
  const grid = [-3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8];
  if (letters.length <= 1) for (const g of grid) pts.push(new Map(letters.map((l) => [l, qRat(Frac.of(g))])));
  else for (const g of [-1, 0, 1, 2, 3, 5]) for (const h of [-2, 0, 1, 4, 6]) pts.push(new Map([[letters[0], qRat(Frac.of(g))], [letters[1], qRat(Frac.of(h))]]));
  let k: Frac | null = null;
  for (const env of pts) {
    const a1 = evalNum(r1.l, env);
    const b1 = evalNum(r1.r, env);
    const a2 = evalNum(r2.l, env);
    const b2 = evalNum(r2.r, env);
    if (!a1 || !b1 || !a2 || !b2 || a1.d || b1.d || a2.d || b2.d) return false;
    const f1 = a1.p.sub(b1.p);
    const f2 = a2.p.sub(b2.p);
    if (f2.isZero()) {
      if (!f1.isZero()) return false;
      continue;
    }
    const ratio = f1.div(f2);
    if (ratio.isZero()) return false;
    if (!ratio.abs().eq(Frac.ONE)) return false;
    if (k === null) k = ratio;
    else if (!k.eq(ratio)) return false;
  }
  return k !== null;
}

function satisfied(rel: { l: Ast; r: Ast }, env: Map<string, QNum>): boolean {
  const l = evalNum(rel.l, env);
  const r = evalNum(rel.r, env);
  return !!l && !!r && qEq(l, r);
}

function isBareVar(a: Ast, letters: string[]): string | null {
  return a.t === "var" && letters.includes(a.name) ? a.name : null;
}

const ASSERT_WORDS = "answer|solution|result|roots?|value|unknown";
function assertionRegex(letters: string[]): RegExp {
  const ls = letters.length ? `|${letters.join("|")}` : "";
  return new RegExp(
    `\\b(${ASSERT_WORDS}${ls})\\s*(?:is|are|=|equals?|equal to|comes? to|will be|becomes?|must be|gives?|:)\\s*([-+]?\\s*[0-9(\\u221a][0-9.+\\-*/^()\\u221a\\s]*)`,
    "g",
  );
}

type Claim = { letter: string | null; value: QNum };
function claimsIn(norm: string, letters: string[]): Claim[] {
  const out: Claim[] = [];
  for (const m of norm.matchAll(assertionRegex(letters))) {
    let body = m[2].trim().replace(/[+\-*/^.\s]+$/, "");
    let parsed = parseExpr(body);
    if (!parsed.ok) {
      body = body.split(/\s+/)[0];
      parsed = parseExpr(body);
    }
    if (!parsed.ok) continue;
    const v = evalNum(parsed.ast);
    if (v) out.push({ letter: letters.includes(m[1]) ? m[1] : null, value: v });
  }
  return out;
}

export function hintLeaks(
  text: string,
  level: 1 | 2 | 3 | 4,
  a: AnswerSet,
  opts: { allowedStates?: string[] } = {},
): LeakVerdict {
  if (level === 4) return { leaks: false, reasons: [] };
  const reasons = new Set<LeakReason>();
  const norm = wordsToDigits(normalizeMath(text));
  const toks = tokenize(norm, a.letters);
  const allowed: { l: Ast; r: Ast }[] = [];
  for (const st of level === 3 ? (opts.allowedStates ?? []) : []) {
    const eq = parseEquation(st);
    if (eq.ok) allowed.push({ l: eq.lhs, r: eq.rhs });
  }

  // 1. Literals (and, at levels 1 and 2, any number that is not in the problem).
  for (const t of toks) {
    if (t.k !== "num") continue;
    const candidates = t.pct ? [t.v, t.v.div(Frac.of(100))] : [t.v];
    for (const v of candidates) {
      if (matchesAnswer(qRat(v), a) && !isGiven(v, a)) reasons.add("literal");
    }
    if (level <= 2 && !isGiven(t.v, a)) reasons.add("derived_number");
    if (t.decimals >= 2) {
      for (const root of a.values) {
        if (root.d !== BigInt(0)) {
          const diff = qApprox(root).sub(t.v).abs();
          const diffNeg = qApprox(qNeg(root)).sub(t.v).abs();
          const lim = Frac.of(1, 100);
          if (diff.cmp(lim) < 0 || diffNeg.cmp(lim) < 0) reasons.add("surd_approx");
        }
      }
    }
  }

  // 2. Maths spans: derived values, relations, solved and factored forms.
  for (const span of spansOf(toks)) {
    const parts = span.split("=");
    const sides: Ast[] = [];
    let ok = true;
    for (const p of parts) {
      const parsed = parseExpr(p.replace(/^[\s+*/^]+|[\s+\-*/^]+$/g, ""));
      if (!parsed.ok) {
        ok = false;
        continue;
      }
      sides.push(parsed.ast);
    }
    for (const s of sides) {
      const nodes: Ast[] = [];
      sub(s, nodes);
      for (const n of nodes) {
        const v = evalNum(n);
        if (v && matchesAnswer(v, a)) reasons.add("derived_span");
      }
      if (a.resultPoly && a.givenPoly && !a.resultPoly.equals(a.givenPoly)) {
        const p = toPoly(s, a.letters[0] ?? null);
        if (p.ok && p.poly.degree >= 1 && p.poly.equals(a.resultPoly)) reasons.add("result_expression");
      }
    }
    if (!ok || sides.length !== parts.length || parts.length < 2) continue;
    for (let i = 0; i + 1 < sides.length; i++) {
      const rel = { l: sides[i], r: sides[i + 1] };
      const bare = isBareVar(rel.l, a.letters) ?? isBareVar(rel.r, a.letters);
      if (bare) {
        const other = isBareVar(rel.l, a.letters) ? rel.r : rel.l;
        const v = evalNum(other);
        if (v) {
          const hit = a.assignments.length
            ? a.assignments.some((asg) => asg.get(bare) && qEq(asg.get(bare) as QNum, v))
            : matchesAnswer(v, a);
          if (hit) reasons.add("solved_form");
        }
      }
      if (a.assignments.length === 0) continue;
      if (!a.assignments.some((env) => satisfied(rel, env))) continue;
      // True at a root. Harmless when it is true everywhere, restates the problem, or is the allowed first state.
      if ([0, 1, 2].some((j) => satisfied(rel, samplesFor(a.letters, j)))) continue;
      if (a.relations.some((g) => sameRelation(rel, g, a.letters))) continue;
      if (allowed.some((g) => sameRelation(rel, g, a.letters))) continue;
      if (!bare) reasons.add("later_state");
    }
  }

  // 3. Phrases such as "the answer is 2" or "x equals two".
  for (const claim of claimsIn(norm, a.letters)) {
    const hit =
      claim.letter && a.assignments.length === 1 && a.assignments[0].has(claim.letter)
        ? qEq(claim.value, a.assignments[0].get(claim.letter) as QNum)
        : matchesAnswer(claim.value, a);
    if (hit) reasons.add("assertion");
  }

  return { leaks: reasons.size > 0, reasons: [...reasons] };
}

/** A chat reply that states `unknown = value` for a value that is not an answer contradicts the key. */
export function contradictsKey(reply: string, a: AnswerSet): { contradicts: boolean; claims: string[] } {
  const norm = wordsToDigits(normalizeMath(reply));
  const bad: string[] = [];
  for (const claim of claimsIn(norm, a.letters)) {
    if (!claim.letter) continue;
    const roots = a.assignments.length === 1 && a.assignments[0].has(claim.letter)
      ? [a.assignments[0].get(claim.letter) as QNum]
      : a.values;
    if (!roots.some((r) => qEq(r, claim.value))) bad.push(`${claim.letter} = ${claim.value.p.toString()}`);
  }
  return { contradicts: bad.length > 0, claims: bad };
}
