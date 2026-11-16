import { B0, B1, Frac, bgcd, bpow, B10, uniqueSorted } from "./frac";
import { Poly } from "./poly";
import { canon, parseEquation, parseExpr, showAst, toPoly } from "./parse";
import { type QNum, qAdd, qApprox, qMul, qRat, qToString, sqrtSplit, qEq } from "./surd";
import type { Answer, Ast, MathCandidate, RuleId, Solution, Step } from "./types";

/**
 * Exact solvers. Everything is rational arithmetic on BigInt; roots that are not rational are kept as p + q*sqrt(d).
 * Each solver returns a step trace built from rule ids (wording is authored copy, see copy.en.ts) and then puts every
 * answer back into the original problem exactly.
 */

export const MAX_DEVICE_DEGREE = 4;

export type RootSet = {
  /** Distinct real roots, ascending. */
  roots: QNum[];
  /** True when a quadratic factor has a negative discriminant (non-real roots exist). */
  complexLeft: boolean;
};

// ---- Roots of a polynomial ------------------------------------------------------------------------------

function divisorsOf(n: bigint, cap: bigint): bigint[] | null {
  if (n < B1 || n > cap) return null;
  const out: bigint[] = [];
  for (let i = B1; i * i <= n; i += B1) {
    if (n % i === B0) {
      out.push(i);
      if (i * i !== n) out.push(n / i);
    }
  }
  return out;
}

/** One rational root by the rational-root theorem (exact), or null. Root 0 is handled first. */
export function findRationalRoot(p: Poly): Frac | null {
  if (p.degree < 1) return null;
  if (p.coeff(0).isZero()) return Frac.ZERO;
  const ints = p.toIntegers();
  const a0 = ints[0] < B0 ? -ints[0] : ints[0];
  const an = ints[ints.length - 1] < B0 ? -ints[ints.length - 1] : ints[ints.length - 1];
  const cap = bpow(B10, 12);
  const ps = divisorsOf(a0, cap);
  const qs = divisorsOf(an, cap);
  if (!ps || !qs || ps.length * qs.length > 40000) return null;
  for (const q of qs) {
    for (const pp of ps) {
      if (bgcd(pp, q) !== B1) continue;
      for (const sign of [B1, -B1]) {
        const cand = Frac.of(pp * sign, q);
        if (p.at(cand).isZero()) return cand;
      }
    }
  }
  return null;
}

function quadraticRoots(q: Poly): { roots: QNum[]; complex: boolean } {
  const a = q.coeff(2);
  const b = q.coeff(1);
  const c = q.coeff(0);
  const disc = b.mul(b).sub(Frac.of(4).mul(a).mul(c));
  if (disc.sign < 0) return { roots: [], complex: true };
  const two = Frac.of(2).mul(a);
  const root = disc.sqrt();
  if (root) {
    const r = uniqueSorted([b.neg().sub(root).div(two), b.neg().add(root).div(two)]);
    return { roots: r.map(qRat), complex: false };
  }
  // Irrational: sqrt(disc) = s * sqrt(d) / den after clearing the denominator of disc.
  const split = sqrtSplit(disc.n * disc.d);
  if (!split) throw new RangeError("too_big");
  const q1 = Frac.of(split.s, disc.d).div(two).abs();
  const p0 = b.neg().div(two);
  return {
    roots: [
      { p: p0, q: q1.neg(), d: split.d },
      { p: p0, q: q1, d: split.d },
    ],
    complex: false,
  };
}

export function rootsOf(p: Poly): RootSet | null {
  if (p.degree < 1 || p.degree > MAX_DEVICE_DEGREE) return null;
  try {
    const roots: QNum[] = [];
    let rest = p;
    let complexLeft = false;
    while (rest.degree > 2) {
      const r = findRationalRoot(rest);
      if (!r) return null;
      if (!roots.some((x) => x.d === B0 && x.p.eq(r))) roots.push(qRat(r));
      const next = rest.divideByRoot(r);
      if (!next) return null;
      rest = next;
    }
    if (rest.degree === 2) {
      const qr = quadraticRoots(rest);
      complexLeft = qr.complex;
      for (const r of qr.roots) if (!roots.some((x) => qEq(x, r))) roots.push(r);
    } else if (rest.degree === 1) {
      const r = rest.coeff(0).neg().div(rest.coeff(1));
      if (!roots.some((x) => x.d === B0 && x.p.eq(r))) roots.push(qRat(r));
    }
    roots.sort((x, y) => qApprox(x).cmp(qApprox(y)));
    return { roots, complexLeft };
  } catch {
    return null;
  }
}

/** Exact value of the polynomial at p + q*sqrt(d). */
export function evalPolyQ(poly: Poly, at: QNum): QNum | null {
  let acc = qRat(Frac.ZERO);
  for (let i = poly.c.length - 1; i >= 0; i--) {
    const m = qMul(acc, at);
    if (!m) return null;
    const s = qAdd(m, qRat(poly.c[i]));
    if (!s) return null;
    acc = s;
  }
  return acc;
}

function isZeroQ(x: QNum | null): boolean {
  return !!x && x.p.isZero() && x.q.isZero();
}

// ---- Display helpers ------------------------------------------------------------------------------------

const f = (v: Frac): string => v.toString();
const term = (coef: Frac, v: string): string => new Poly([Frac.ZERO, coef]).show(v);

function eqShow(l: Poly, r: Poly, v: string): string {
  return `${l.show(v)} = ${r.show(v)}`;
}

function rootFactor(r: Frac, v: string): string {
  if (r.isZero()) return v;
  return r.sign > 0 ? `(${v} - ${f(r)})` : `(${v} + ${f(r.abs())})`;
}

function minimalLeaves(p: Poly): number {
  let n = 0;
  for (let i = 0; i < p.c.length; i++) {
    const co = p.c[i];
    if (co.isZero()) continue;
    const one = co.abs().eq(Frac.ONE);
    n += i === 0 ? 1 : (one ? 0 : 1) + 1 + (i > 1 ? 1 : 0);
  }
  return Math.max(n, 1);
}
function leaves(a: Ast): number {
  if (a.t === "num" || a.t === "var") return 1;
  if (a.t === "neg" || a.t === "sqrt") return leaves(a.a);
  return leaves(a.a) + leaves(a.b);
}
function hasBracket(a: Ast): boolean {
  return canon(a).includes("(");
}

const OK_CHECK = { by: "substitution", exact: true } as const;

function empty(status: Solution["status"], why: string | undefined, steps: Step[], tag: string | null): Solution {
  return { status, why, answer: { kind: "none" }, steps, checked: { ...OK_CHECK, ok: true }, misconceptionTag: tag, exact: [] };
}

// ---- poly_eq ----------------------------------------------------------------------------------------------

function parseSides(c: MathCandidate): { l: Ast; r: Ast } | null {
  if (c.lhsText === undefined || c.rhsText === undefined) return null;
  const eq = parseEquation(`${c.lhsText}=${c.rhsText}`);
  return eq.ok ? { l: eq.lhs, r: eq.rhs } : null;
}

type Tail = { exact: QNum[]; complexLeft: boolean };

function linearTrace(L: Poly, R: Poly, v: string, steps: Step[]): "identity" | "no_solution" | Frac {
  let A = L.coeff(1);
  let B = L.coeff(0);
  let C = R.coeff(1);
  let D = R.coeff(0);
  const state = () => eqShow(new Poly([B, A]), new Poly([D, C]), v);
  if (!C.isZero()) {
    const before = state();
    const rule: RuleId = C.sign > 0 ? "subtract_both_sides" : "add_both_sides";
    const amount = term(C.abs(), v);
    A = A.sub(C);
    C = Frac.ZERO;
    steps.push({ rule, args: { amount }, before, after: state() });
  }
  if (A.isZero()) {
    const before = state();
    const same = B.eq(D);
    steps.push({ rule: same ? "identity" : "no_solution", args: {}, before, after: before });
    return same ? "identity" : "no_solution";
  }
  if (!B.isZero()) {
    const before = state();
    const rule: RuleId = B.sign > 0 ? "subtract_both_sides" : "add_both_sides";
    const amount = f(B.abs());
    D = D.sub(B);
    B = Frac.ZERO;
    steps.push({ rule, args: { amount }, before, after: state() });
  }
  const value = D.div(A);
  if (!A.eq(Frac.ONE)) {
    const before = state();
    const reciprocal = A.n === B1 && A.d > B1;
    steps.push({
      rule: reciprocal ? "multiply_both_sides" : "divide_both_sides",
      args: { factor: reciprocal ? A.d.toString() : f(A) },
      before,
      after: `${v} = ${f(value)}`,
    });
  }
  return value;
}

function quadraticTrace(q0: Poly, v: string, steps: Step[]): Tail {
  let q = q0;
  const lcm = q.c.reduce((acc, co) => (acc / bgcd(acc, co.d)) * co.d, B1);
  if (lcm > B1) {
    const before = `${q.show(v)} = 0`;
    q = q.scale(Frac.of(lcm));
    steps.push({ rule: "multiply_both_sides", args: { factor: lcm.toString() }, before, after: `${q.show(v)} = 0` });
  }
  const a = q.coeff(2);
  const b = q.coeff(1);
  const c = q.coeff(0);
  const disc = b.mul(b).sub(Frac.of(4).mul(a).mul(c));
  const start = `${q.show(v)} = 0`;
  if (disc.sign < 0) {
    steps.push({ rule: "discriminant", args: { value: f(disc) }, before: start, after: `D = ${f(disc)}` });
    steps.push({ rule: "no_real_roots", args: {}, before: `D = ${f(disc)}`, after: "no real solutions" });
    return { exact: [], complexLeft: true };
  }
  const root = disc.sqrt();
  const two = Frac.of(2).mul(a);
  if (root) {
    const r1 = b.neg().sub(root).div(two);
    const r2 = b.neg().add(root).div(two);
    const rs = uniqueSorted([r1, r2]);
    const lead = a.eq(Frac.ONE) ? "" : a.eq(Frac.of(-1)) ? "-" : a.isInt() ? f(a) : `(${f(a)})`;
    const prod = rs.length === 1 ? `${rootFactor(rs[0], v)}^2` : `${rootFactor(rs[0], v)}${rootFactor(rs[1], v)}`;
    steps.push({ rule: "factor_quadratic", args: {}, before: start, after: `${lead}${prod} = 0` });
    const zeros = rs.map((r) => `${v} - ${f(r)} = 0`.replace(`${v} - -`, `${v} + `)).join(" or ");
    steps.push({ rule: "zero_product", args: {}, before: `${lead}${prod} = 0`, after: zeros });
    for (const r of rs) {
      const bef = `${v} - ${f(r)} = 0`.replace(`${v} - -`, `${v} + `);
      steps.push({
        rule: r.sign >= 0 ? "add_both_sides" : "subtract_both_sides",
        args: { amount: f(r.abs()) },
        before: bef,
        after: `${v} = ${f(r)}`,
      });
    }
    return { exact: rs.map(qRat), complexLeft: false };
  }
  steps.push({ rule: "discriminant", args: { value: f(disc) }, before: start, after: `D = ${f(disc)}` });
  const sp = sqrtSplit(disc.n * disc.d);
  if (!sp) throw new RangeError("too_big");
  const roots = quadraticRoots(q).roots;
  const bn = f(b.neg());
  steps.push({
    rule: "quadratic_formula",
    args: { a: f(a), b: f(b), c: f(c) },
    before: `D = ${f(disc)}`,
    after: `${v} = (${bn} ± √${f(disc)}) / ${f(two)}`,
  });
  if (disc.isInt() && sp.s > B1) {
    steps.push({
      rule: "simplify_surd",
      args: { d: sp.d.toString() },
      before: `√${f(disc)}`,
      after: `${sp.s}√${sp.d}`,
    });
  }
  steps.push({
    rule: "state_result",
    args: {},
    before: "",
    after: `${v} = ${qToString(roots[0])} or ${v} = ${qToString(roots[1])}`,
  });
  return { exact: roots, complexLeft: false };
}

function finishRoots(c: MathCandidate, p: Poly, steps: Step[], exact: QNum[], complexLeft: boolean, tag: string): Solution {
  exact.sort((x, y) => qApprox(x).cmp(qApprox(y)));
  if (exact.length === 0) return empty("no_solution", complexLeft ? "no_real_roots" : "none", steps, tag);
  const ok = exact.every((r) => isZeroQ(evalPolyQ(p, r)));
  const v = c.variable;
  steps.push({
    rule: "substitute_check",
    args: { values: exact.map(qToString).join(", ") },
    before: c.display,
    after: "both sides are equal",
  });
  void v;
  const rational = exact.filter((r) => r.d === B0).map((r) => f(r.p));
  const surds = exact.filter((r) => r.d !== B0).map(qToString);
  const answer: Answer = surds.length ? { kind: "surd", values: rational, surds } : { kind: "values", values: rational };
  return {
    status: "solved",
    answer,
    steps,
    checked: { ...OK_CHECK, ok },
    misconceptionTag: tag,
    exact,
  };
}

function solvePolyEq(c: MathCandidate): Solution {
  const sides = parseSides(c);
  if (!sides) return empty("unsupported", "parse", [], null);
  const pl = toPoly(sides.l, "x");
  const pr = toPoly(sides.r, "x");
  if (!pl.ok || !pr.ok) return empty("unsupported", "parse", [], null);
  const L = pl.poly;
  const R = pr.poly;
  const p = L.sub(R);
  const v = c.variable;
  const steps: Step[] = [];
  const maxSide = Math.max(L.degree, R.degree);
  if (p.isZero()) {
    steps.push({ rule: "identity", args: {}, before: c.display, after: c.display });
    return empty("identity", "always_true", steps, null);
  }
  if (p.degree === 0) {
    steps.push({ rule: "no_solution", args: {}, before: c.display, after: c.display });
    return empty("no_solution", "never_true", steps, null);
  }
  if (p.degree > MAX_DEVICE_DEGREE) return empty("unsupported", "too_big", [], null);

  // Tidy each side when the writing is longer than it needs to be.
  const simplifiable =
    leaves(sides.l) + leaves(sides.r) > minimalLeaves(L) + minimalLeaves(R) || hasBracket(sides.l) || hasBracket(sides.r);
  if (simplifiable) {
    const bracket = hasBracket(sides.l) || hasBracket(sides.r);
    steps.push({
      rule: bracket ? "expand_bracket" : "collect_like_terms",
      args: {},
      before: c.display,
      after: eqShow(L, R, v),
    });
  }

  if (p.degree === 1) {
    let l = L;
    let r = R;
    if (maxSide > 1) {
      steps.push({ rule: "write_standard_form", args: {}, before: eqShow(L, R, v), after: `${p.show(v)} = 0` });
      l = p;
      r = new Poly([]);
    }
    const out = linearTrace(l, r, v, steps);
    if (out === "identity") return empty("identity", "always_true", steps, null);
    if (out === "no_solution") return empty("no_solution", "never_true", steps, null);
    steps.push({ rule: "state_result", args: {}, before: "", after: `${v} = ${f(out)}` });
    return finishRoots(c, p, steps, [qRat(out)], false, "ALG.LIN.INVERSE_OPS");
  }

  if (!R.isZero() || maxSide > p.degree || !L.equals(p)) {
    steps.push({ rule: "write_standard_form", args: {}, before: eqShow(L, R, v), after: `${p.show(v)} = 0` });
  }
  let rest = p;
  const exact: QNum[] = [];
  while (rest.degree > 2) {
    const r = findRationalRoot(rest);
    if (!r) return empty("unsupported", "no_rational_root", steps, null);
    const next = rest.divideByRoot(r);
    if (!next) return empty("unsupported", "no_rational_root", steps, null);
    steps.push({
      rule: "rational_root",
      args: { root: f(r) },
      before: `${rest.show(v)} = 0`,
      after: `${rootFactor(r, v)}(${next.show(v)}) = 0`,
    });
    if (!exact.some((x) => x.d === B0 && x.p.eq(r))) exact.push(qRat(r));
    rest = next;
  }
  let complexLeft = false;
  try {
    if (rest.degree === 2) {
      const tail = quadraticTrace(rest, v, steps);
      complexLeft = tail.complexLeft;
      for (const r of tail.exact) if (!exact.some((x) => qEq(x, r))) exact.push(r);
    } else {
      const out = linearTrace(rest, new Poly([]), v, steps);
      if (out instanceof Frac && !exact.some((x) => x.d === B0 && x.p.eq(out))) exact.push(qRat(out));
    }
  } catch {
    return empty("unsupported", "too_big", [], null);
  }
  return finishRoots(c, p, steps, exact, complexLeft, p.degree === 2 ? "ALG.QUAD.ZERO_PRODUCT" : "ALG.POLY.FACTOR");
}

/** Roots of the equation lhs = rhs given as polynomials (no steps). Null when outside the device solvers. */
export function solutionSet(lhs: Poly, rhs: Poly): { status: "identity" | "no_solution" | "roots"; roots: QNum[] } | null {
  const p = lhs.sub(rhs);
  if (p.isZero()) return { status: "identity", roots: [] };
  if (p.degree === 0) return { status: "no_solution", roots: [] };
  const rs = rootsOf(p);
  if (!rs) return null;
  return { status: rs.roots.length ? "roots" : "no_solution", roots: rs.roots };
}

// ---- arithmetic ---------------------------------------------------------------------------------------------

function foldNeg(a: Ast): Ast {
  if (a.t === "neg") {
    const inner = foldNeg(a.a);
    return inner.t === "num" ? { t: "num", v: inner.v.neg() } : { t: "neg", a: inner };
  }
  if (a.t === "sqrt") return { t: "sqrt", a: foldNeg(a.a) };
  if (a.t === "bin") return { t: "bin", op: a.op, a: foldNeg(a.a), b: foldNeg(a.b) };
  return a;
}

type Reduced = { node: Ast; op?: { a: string; b?: string; sym: string; result: string } };

function reduceOnce(n: Ast): Reduced | null {
  if (n.t === "num" || n.t === "var") return null;
  if (n.t === "neg") {
    const r = reduceOnce(n.a);
    return r ? { node: { t: "neg", a: r.node }, op: r.op } : null;
  }
  if (n.t === "sqrt") {
    const r = reduceOnce(n.a);
    if (r) return { node: { t: "sqrt", a: r.node }, op: r.op };
    if (n.a.t === "num") {
      const root = n.a.v.sqrt();
      if (!root) return null;
      return { node: { t: "num", v: root }, op: { a: f(n.a.v), sym: "√", result: f(root) } };
    }
    return null;
  }
  const l = reduceOnce(n.a);
  if (l) return { node: { t: "bin", op: n.op, a: l.node, b: n.b }, op: l.op };
  const r = reduceOnce(n.b);
  if (r) return { node: { t: "bin", op: n.op, a: n.a, b: r.node }, op: r.op };
  if (n.a.t !== "num" || n.b.t !== "num") return null;
  const x = n.a.v;
  const y = n.b.v;
  let res: Frac;
  if (n.op === "+") res = x.add(y);
  else if (n.op === "-") res = x.sub(y);
  else if (n.op === "*") res = x.mul(y);
  else if (n.op === "/") res = x.div(y);
  else res = x.pow(Number(y.n));
  return { node: { t: "num", v: res }, op: { a: f(x), b: f(y), sym: n.op, result: f(res) } };
}

function solveArith(c: MathCandidate): Solution {
  const parsed = c.expr ? parseExpr(c.expr) : null;
  if (!parsed || !parsed.ok) return empty("unsupported", "parse", [], null);
  const value = toPoly(parsed.ast, null);
  if (!value.ok) return empty("unsupported", value.why, [], null);
  const answerValue = value.poly.coeff(0);
  const steps: Step[] = [];
  let cur = foldNeg(parsed.ast);
  for (let guard = 0; guard < 40; guard++) {
    const r = reduceOnce(cur);
    if (!r) break;
    steps.push({
      rule: "eval_operation",
      args: { a: r.op?.a ?? "", b: r.op?.b ?? "", op: r.op?.sym ?? "", result: r.op?.result ?? "" },
      before: showAst(cur),
      after: showAst(r.node),
    });
    cur = r.node;
  }
  const claim = c.claimed !== undefined ? Frac.parse(c.claimed) : null;
  const sol: Solution = {
    status: "solved",
    answer: { kind: "values", values: [f(answerValue)] },
    steps,
    checked: { ...OK_CHECK, ok: true },
    misconceptionTag: "ARITH.ORDER_OF_OPERATIONS",
    exact: [qRat(answerValue)],
  };
  if (claim) sol.claimTrue = claim.eq(answerValue);
  return sol;
}

// ---- poly_simplify ----------------------------------------------------------------------------------------

function solveSimplify(c: MathCandidate): Solution {
  const parsed = c.expr ? parseExpr(c.expr) : null;
  if (!parsed || !parsed.ok) return empty("unsupported", "parse", [], null);
  const p = toPoly(parsed.ast, "x");
  if (!p.ok) return empty("unsupported", p.why, [], null);
  const v = c.variable;
  const steps: Step[] = [];
  const shown = p.poly.show(v);
  if (leaves(parsed.ast) > minimalLeaves(p.poly) || hasBracket(parsed.ast)) {
    steps.push({
      rule: hasBracket(parsed.ast) ? "expand_bracket" : "collect_like_terms",
      args: {},
      before: c.display,
      after: shown,
    });
  }
  steps.push({ rule: "state_result", args: {}, before: "", after: shown });
  return {
    status: "solved",
    answer: { kind: "expr", value: shown, coeffs: p.poly.toStrings() },
    steps,
    checked: { ...OK_CHECK, ok: true },
    misconceptionTag: "ALG.EXPR.LIKE_TERMS",
    exact: [],
  };
}

// ---- 2x2 system -------------------------------------------------------------------------------------------

function lin(a: Frac, b: Frac, x: string, y: string): string {
  const parts: string[] = [];
  const add = (co: Frac, name: string) => {
    if (co.isZero()) return;
    const mag = co.abs().eq(Frac.ONE) ? "" : f(co.abs());
    const body = `${mag}${name}`;
    parts.push(parts.length === 0 ? (co.sign < 0 ? `-${body}` : body) : `${co.sign < 0 ? "-" : "+"} ${body}`);
  };
  add(a, x);
  add(b, y);
  return parts.length ? parts.join(" ") : "0";
}

function solveSystem(c: MathCandidate): Solution {
  const sys = c.system;
  if (!sys || sys.coeffs.length !== 2) return empty("unsupported", "parse", [], null);
  const n = (s: string): Frac => Frac.parse(s) ?? Frac.ZERO;
  const [a1, b1] = sys.coeffs[0].map(n);
  const [a2, b2] = sys.coeffs[1].map(n);
  const [c1, c2] = sys.consts.map(n);
  const X = c.variable[0] ?? "x";
  const Y = c.variable[1] ?? "y";
  const e1 = (a: Frac, b: Frac, k: Frac) => `${lin(a, b, X, Y)} = ${f(k)}`;
  const steps: Step[] = [];
  const det = a1.mul(b2).sub(a2.mul(b1));
  if (det.isZero()) {
    // Same line (every multiple of one row) or parallel lines.
    const consistent = a1.mul(c2).eq(a2.mul(c1)) && b1.mul(c2).eq(b2.mul(c1));
    const zeroRows = [a1, b1, a2, b2].every((q) => q.isZero());
    const same = consistent && !zeroRows;
    steps.push({ rule: same ? "identity" : "no_solution", args: {}, before: c.display, after: c.display });
    return empty(same ? "identity" : "no_solution", same ? "same_line" : "parallel", steps, "ALG.SYS.ELIMINATION");
  }
  // Remove y: make the y terms the same size, then add or subtract the equations.
  let xv: Frac;
  if (b1.isZero() || b2.isZero()) {
    const [ua, uc] = b1.isZero() ? [a1, c1] : [a2, c2];
    xv = uc.div(ua);
    steps.push({
      rule: "divide_both_sides",
      args: { factor: f(ua) },
      before: b1.isZero() ? e1(a1, b1, c1) : e1(a2, b2, c2),
      after: `${X} = ${f(xv)}`,
    });
  } else {
    let m1: Frac;
    let m2: Frac;
    if (b1.isInt() && b2.isInt()) {
      const big = (b1.n < B0 ? -b1.n : b1.n) * (b2.n < B0 ? -b2.n : b2.n);
      const l = big / bgcd(b1.n, b2.n);
      m1 = Frac.of(l, b1.n < B0 ? -b1.n : b1.n);
      m2 = Frac.of(l, b2.n < B0 ? -b2.n : b2.n);
    } else {
      m1 = b2.abs();
      m2 = b1.abs();
    }
    const r1 = [a1.mul(m1), b1.mul(m1), c1.mul(m1)];
    const r2 = [a2.mul(m2), b2.mul(m2), c2.mul(m2)];
    if (!m1.eq(Frac.ONE)) {
      steps.push({ rule: "multiply_both_sides", args: { factor: f(m1), which: "1" }, before: e1(a1, b1, c1), after: e1(r1[0], r1[1], r1[2]) });
    }
    if (!m2.eq(Frac.ONE)) {
      steps.push({ rule: "multiply_both_sides", args: { factor: f(m2), which: "2" }, before: e1(a2, b2, c2), after: e1(r2[0], r2[1], r2[2]) });
    }
    const subtract = r1[1].eq(r2[1]);
    const ax = subtract ? r1[0].sub(r2[0]) : r1[0].add(r2[0]);
    const ck = subtract ? r1[2].sub(r2[2]) : r1[2].add(r2[2]);
    steps.push({
      rule: "eliminate_unknown",
      args: { unknown: Y, op: subtract ? "subtract" : "add" },
      before: `${e1(r1[0], r1[1], r1[2])};  ${e1(r2[0], r2[1], r2[2])}`,
      after: `${lin(ax, Frac.ZERO, X, Y)} = ${f(ck)}`,
    });
    xv = ck.div(ax);
    if (!ax.eq(Frac.ONE)) {
      steps.push({ rule: "divide_both_sides", args: { factor: f(ax) }, before: `${lin(ax, Frac.ZERO, X, Y)} = ${f(ck)}`, after: `${X} = ${f(xv)}` });
    }
  }
  // Put x back into whichever equation has a y term.
  const useFirst = !b1.isZero();
  const [ua, ub, uc] = useFirst ? [a1, b1, c1] : [a2, b2, c2];
  const rest = uc.sub(ua.mul(xv));
  steps.push({
    rule: "substitute_back",
    args: { value: f(xv), unknown: X },
    before: e1(ua, ub, uc),
    after: `${lin(ub, Frac.ZERO, Y, Y)} = ${f(rest)}`,
  });
  const yv = rest.div(ub);
  steps.push({ rule: "solve_one_unknown", args: {}, before: `${lin(ub, Frac.ZERO, Y, Y)} = ${f(rest)}`, after: `${Y} = ${f(yv)}` });
  const ok = a1.mul(xv).add(b1.mul(yv)).eq(c1) && a2.mul(xv).add(b2.mul(yv)).eq(c2);
  steps.push({ rule: "substitute_check", args: { values: `${f(xv)}, ${f(yv)}` }, before: c.display, after: "both equations are equal" });
  return {
    status: "solved",
    answer: { kind: "pair", x: f(xv), y: f(yv) },
    steps,
    checked: { ...OK_CHECK, ok },
    misconceptionTag: "ALG.SYS.ELIMINATION",
    exact: [qRat(xv), qRat(yv)],
  };
}

export function solve(c: MathCandidate): Solution {
  try {
    switch (c.kind) {
      case "arith":
        return solveArith(c);
      case "poly_eq":
        return solvePolyEq(c);
      case "poly_simplify":
        return solveSimplify(c);
      case "linear_system":
        return solveSystem(c);
    }
  } catch {
    return empty("unsupported", "too_big", [], null);
  }
}
