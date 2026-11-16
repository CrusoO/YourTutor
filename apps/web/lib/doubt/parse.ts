import { Frac } from "./frac";
import { Poly } from "./poly";
import {
  type QNum,
  qAdd,
  qDiv,
  qMul,
  qNeg,
  qPow,
  qRat,
  qSqrt,
  qSub,
} from "./surd";
import type { Ast, ParseFail } from "./types";

/**
 * Strict allow-list parser: digits, decimals, one-letter unknowns, + - * / ^ ( ) and the square-root sign.
 * It never calls eval, Function, or any dynamic code, and it rejects everything it does not know.
 */

export type ParseLimits = { maxLen: number; maxDigits: number; maxExponent: number; maxDepth: number };
export const DEFAULT_PARSE_LIMITS: ParseLimits = { maxLen: 400, maxDigits: 18, maxExponent: 64, maxDepth: 24 };

export type Parsed = { ok: true; ast: Ast } | { ok: false; why: ParseFail };
const fail = (why: ParseFail): { ok: false; why: ParseFail } => ({ ok: false, why });

export const FUNCTION_WORDS = new Set([
  "sin", "cos", "tan", "cot", "sec", "csc", "cosec", "log", "ln", "exp", "abs", "sinh", "cosh", "tanh", "lim", "int",
]);

const DIGIT_BLOCKS: [number, number][] = [
  [0x0660, 0x0669], // Arabic-Indic
  [0x06f0, 0x06f9], // Extended Arabic-Indic
  [0x0966, 0x096f], // Devanagari
  [0xff10, 0xff19], // full width
];
const SUPERSCRIPTS: Record<string, string> = {
  "²": "^2", "³": "^3", "⁴": "^4", "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8",
  "⁹": "^9", "⁰": "^0", "¹": "^1",
};
const VULGAR: Record<string, string> = {
  "½": "(1/2)", "⅓": "(1/3)", "⅔": "(2/3)", "¼": "(1/4)", "¾": "(3/4)", "⅕": "(1/5)",
  "⅛": "(1/8)",
};

/** Make equivalent writings identical: Unicode digits, minus signs, times and divide signs, superscripts, LaTeX bits. */
export function normalizeMath(input: string): string {
  let s = input.normalize("NFC");
  s = s.replace(/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, "(($1)/($2))");
  s = s.replace(/\\sqrt\s*\{([^{}]*)\}/g, "√($1)");
  s = s.replace(/\\(?:cdot|times)/g, "*").replace(/\\left|\\right/g, "").replace(/[$]/g, " ");
  let out = "";
  for (const ch of s) {
    const cp = ch.codePointAt(0) as number;
    const block = DIGIT_BLOCKS.find(([lo, hi]) => cp >= lo && cp <= hi);
    if (block) out += String(cp - block[0]);
    else if (SUPERSCRIPTS[ch]) out += SUPERSCRIPTS[ch];
    else if (VULGAR[ch]) out += VULGAR[ch];
    else if (ch === "−" || ch === "–" || ch === "—" || ch === "‒") out += "-";
    else if (ch === "×" || ch === "⋅" || ch === "·" || ch === "∗") out += "*";
    else if (ch === "÷" || ch === "∕") out += "/";
    else if (ch === " " || ch === " " || ch === " " || ch === "​") out += " ";
    else if (ch === "≤" || ch === "≥") out += ch;
    else out += ch;
  }
  return out.replace(/\*\*/g, "^").toLowerCase();
}

type Tok =
  | { k: "num"; v: Frac }
  | { k: "id"; name: string }
  | { k: "op"; op: string }
  | { k: "sqrt" };

function tokenize(text: string, lim: ParseLimits): Tok[] | ParseFail {
  const toks: Tok[] = [];
  let i = 0;
  while (i < text.length) {
    const ch = text[i];
    if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r") {
      i++;
    } else if (/[0-9]/.test(ch) || (ch === "." && /[0-9]/.test(text[i + 1] ?? ""))) {
      let j = i;
      while (j < text.length && /[0-9]/.test(text[j])) j++;
      if (text[j] === "." && /[0-9]/.test(text[j + 1] ?? "")) {
        j++;
        while (j < text.length && /[0-9]/.test(text[j])) j++;
      }
      const lit = text.slice(i, j);
      if (lit.replace(".", "").length > lim.maxDigits) return "too_big";
      const v = Frac.parse(lit);
      if (!v) return "parse";
      toks.push({ k: "num", v });
      i = j;
    } else if (/[a-z]/.test(ch)) {
      let j = i;
      while (j < text.length && /[a-z]/.test(text[j])) j++;
      const word = text.slice(i, j);
      if (word === "sqrt") toks.push({ k: "sqrt" });
      else if (FUNCTION_WORDS.has(word)) return "function";
      else if (word.length > 1) return "parse";
      else toks.push({ k: "id", name: word });
      i = j;
    } else if (ch === "√") {
      toks.push({ k: "sqrt" });
      i++;
    } else if ("+-*/^()=".includes(ch)) {
      toks.push({ k: "op", op: ch });
      i++;
    } else if (ch === "π" || ch === "∞") {
      return "irrational";
    } else if (ch === "<" || ch === ">" || ch === "≤" || ch === "≥") {
      return "inequality";
    } else {
      return "parse";
    }
  }
  return toks;
}

class Parser {
  private pos = 0;
  private fails: ParseFail | null = null;
  constructor(
    private readonly toks: Tok[],
    private readonly lim: ParseLimits,
  ) {}

  get error(): ParseFail | null {
    return this.fails;
  }
  atEnd(): boolean {
    return this.pos >= this.toks.length;
  }
  private peek(): Tok | undefined {
    return this.toks[this.pos];
  }
  private isOp(op: string): boolean {
    const t = this.peek();
    return !!t && t.k === "op" && t.op === op;
  }
  private bad(why: ParseFail = "parse"): never {
    this.fails = this.fails ?? why;
    throw new Error("parse");
  }

  run(): Ast | null {
    try {
      const a = this.expr(0);
      return this.atEnd() ? a : this.bad();
    } catch {
      return null;
    }
  }

  private expr(depth: number): Ast {
    if (depth > this.lim.maxDepth) this.bad("too_big");
    let left = this.term(depth);
    while (this.isOp("+") || this.isOp("-")) {
      const op = (this.toks[this.pos++] as { op: string }).op as "+" | "-";
      left = { t: "bin", op, a: left, b: this.term(depth) };
    }
    return left;
  }

  private startsFactor(t: Tok | undefined, afterNumber: boolean): boolean {
    if (!t) return false;
    if (t.k === "id" || t.k === "sqrt") return true;
    if (t.k === "op" && t.op === "(") return true;
    return t.k === "num" && !afterNumber && false;
  }

  private term(depth: number): Ast {
    let left = this.unary(depth);
    for (;;) {
      const t = this.peek();
      if (t && t.k === "op" && (t.op === "*" || t.op === "/")) {
        this.pos++;
        left = { t: "bin", op: t.op as "*" | "/", a: left, b: this.unary(depth) };
      } else if (this.startsFactor(t, false)) {
        left = { t: "bin", op: "*", a: left, b: this.power(depth) };
      } else return left;
    }
  }

  private unary(depth: number): Ast {
    if (this.isOp("-")) {
      this.pos++;
      return { t: "neg", a: this.unary(depth) };
    }
    if (this.isOp("+")) {
      this.pos++;
      return this.unary(depth);
    }
    return this.power(depth);
  }

  private power(depth: number): Ast {
    const base = this.atom(depth);
    if (this.isOp("^")) {
      this.pos++;
      // The exponent may carry a sign and is right-associative: 2^-1, a^b^c.
      let neg = false;
      if (this.isOp("-")) {
        this.pos++;
        neg = true;
      } else if (this.isOp("+")) this.pos++;
      const e = this.power(depth);
      return { t: "bin", op: "^", a: base, b: neg ? { t: "neg", a: e } : e };
    }
    return base;
  }

  private atom(depth: number): Ast {
    const t = this.toks[this.pos++];
    if (!t) return this.bad();
    if (t.k === "num") return { t: "num", v: t.v };
    if (t.k === "id") return { t: "var", name: t.name };
    if (t.k === "sqrt") return { t: "sqrt", a: this.atom(depth) };
    if (t.k === "op" && t.op === "(") {
      const inner = this.expr(depth + 1);
      if (!this.isOp(")")) this.bad();
      this.pos++;
      return inner;
    }
    return this.bad();
  }
}

export function parseExpr(text: string, limits: Partial<ParseLimits> = {}): Parsed {
  const lim = { ...DEFAULT_PARSE_LIMITS, ...limits };
  if (text.length > lim.maxLen) return fail("too_big");
  const toks = tokenize(normalizeMath(text), lim);
  if (typeof toks === "string") return fail(toks);
  if (toks.length === 0) return fail("parse");
  if (toks.some((t) => t.k === "op" && t.op === "=")) return fail("parse");
  const parser = new Parser(toks, lim);
  const ast = parser.run();
  return ast ? { ok: true, ast } : fail(parser.error ?? "parse");
}

export type ParsedEquation = { ok: true; lhs: Ast; rhs: Ast } | { ok: false; why: ParseFail };

/** "lhs = rhs" with exactly one equals sign. */
export function parseEquation(text: string, limits: Partial<ParseLimits> = {}): ParsedEquation {
  const norm = normalizeMath(text);
  const parts = norm.split("=");
  if (parts.length !== 2) return fail("parse");
  const l = parseExpr(parts[0], limits);
  if (!l.ok) return l;
  const r = parseExpr(parts[1], limits);
  if (!r.ok) return r;
  return { ok: true, lhs: l.ast, rhs: r.ast };
}

export function collectLetters(ast: Ast, into: Set<string> = new Set()): Set<string> {
  if (ast.t === "var") into.add(ast.name);
  else if (ast.t === "neg" || ast.t === "sqrt") collectLetters(ast.a, into);
  else if (ast.t === "bin") {
    collectLetters(ast.a, into);
    collectLetters(ast.b, into);
  }
  return into;
}

export function astSize(ast: Ast): { nodes: number; depth: number } {
  if (ast.t === "num" || ast.t === "var") return { nodes: 1, depth: 1 };
  if (ast.t === "neg" || ast.t === "sqrt") {
    const s = astSize(ast.a);
    return { nodes: s.nodes + 1, depth: s.depth + 1 };
  }
  const a = astSize(ast.a);
  const b = astSize(ast.b);
  return { nodes: a.nodes + b.nodes + 1, depth: Math.max(a.depth, b.depth) + 1 };
}

/** Largest literal exponent anywhere in the tree (Infinity when an exponent is not a plain integer). */
export function maxExponent(ast: Ast): number {
  if (ast.t === "num" || ast.t === "var") return 0;
  if (ast.t === "neg" || ast.t === "sqrt") return maxExponent(ast.a);
  const inner = Math.max(maxExponent(ast.a), maxExponent(ast.b));
  if (ast.op !== "^") return inner;
  const e = constOf(ast.b);
  if (!e || !e.isInt() || e.n > BigInt(1_000_000) || e.n < BigInt(-1_000_000)) return Infinity;
  return Math.max(inner, Math.abs(Number(e.n)));
}

function constOf(ast: Ast): Frac | null {
  if (ast.t === "num") return ast.v;
  if (ast.t === "neg") {
    const v = constOf(ast.a);
    return v ? v.neg() : null;
  }
  return null;
}

// ---- Polynomial conversion ------------------------------------------------------------------------------

export const MAX_DEGREE = 8;
export type PolyResult = { ok: true; poly: Poly } | { ok: false; why: ParseFail };

/** One unknown letter (or none, for arithmetic). Division only by non-zero constants; powers only by whole numbers. */
export function toPoly(ast: Ast, letter: string | null, maxDegree = MAX_DEGREE): PolyResult {
  const out = polyOf(ast, letter, maxDegree);
  return typeof out === "string" ? { ok: false, why: out } : { ok: true, poly: out };
}

function polyOf(ast: Ast, letter: string | null, maxDegree: number): Poly | ParseFail {
  switch (ast.t) {
    case "num":
      return Poly.constant(ast.v);
    case "var":
      return letter !== null && ast.name === letter ? Poly.x() : "multi_unknown";
    case "neg": {
      const a = polyOf(ast.a, letter, maxDegree);
      return typeof a === "string" ? a : a.neg();
    }
    case "sqrt": {
      const a = polyOf(ast.a, letter, maxDegree);
      if (typeof a === "string") return a;
      if (!a.isConstant()) return "nonlinear";
      const root = a.coeff(0).sqrt();
      return root ? Poly.constant(root) : "irrational";
    }
    case "bin": {
      const a = polyOf(ast.a, letter, maxDegree);
      if (typeof a === "string") return a;
      const b = polyOf(ast.b, letter, maxDegree);
      if (typeof b === "string") return b;
      let r: Poly;
      if (ast.op === "+") r = a.add(b);
      else if (ast.op === "-") r = a.sub(b);
      else if (ast.op === "*") r = a.mul(b);
      else if (ast.op === "/") {
        if (!b.isConstant()) return "rational_function";
        if (b.isZero()) return "div_zero";
        r = a.scale(b.coeff(0).inv());
      } else {
        if (!b.isConstant()) return "nonlinear";
        const e = b.coeff(0);
        if (!e.isInt() || e.n > BigInt(64) || e.n < BigInt(-64)) return "too_big";
        const k = Number(e.n);
        if (a.isConstant()) {
          if (a.isZero() && k < 0) return "div_zero";
          r = Poly.constant(a.coeff(0).pow(k));
        } else {
          if (k < 0) return "rational_function";
          if (a.degree * k > maxDegree) return "too_big";
          r = a.pow(k);
        }
      }
      return r.degree > maxDegree ? "too_big" : r;
    }
  }
}

export type Lin = { coef: Map<string, Frac>; c: Frac };
export type LinResult = { ok: true; lin: Lin } | { ok: false; why: ParseFail };

/** Linear form over any letters: sum of coef*letter + c. Anything nonlinear is refused. */
export function toLinear(ast: Ast): LinResult {
  const out = linOf(ast);
  return typeof out === "string" ? { ok: false, why: out } : { ok: true, lin: out };
}

function linOf(ast: Ast): Lin | ParseFail {
  const k = (v: Lin, f: Frac): Lin => ({
    coef: new Map([...v.coef].map(([n, c]) => [n, c.mul(f)])),
    c: v.c.mul(f),
  });
  const isConst = (v: Lin) => [...v.coef.values()].every((c) => c.isZero());
  switch (ast.t) {
    case "num":
      return { coef: new Map(), c: ast.v };
    case "var":
      return { coef: new Map([[ast.name, Frac.ONE]]), c: Frac.ZERO };
    case "neg": {
      const a = linOf(ast.a);
      return typeof a === "string" ? a : k(a, Frac.of(-1));
    }
    case "sqrt": {
      const a = linOf(ast.a);
      if (typeof a === "string") return a;
      if (!isConst(a)) return "nonlinear";
      const r = a.c.sqrt();
      return r ? { coef: new Map(), c: r } : "irrational";
    }
    case "bin": {
      const a = linOf(ast.a);
      if (typeof a === "string") return a;
      const b = linOf(ast.b);
      if (typeof b === "string") return b;
      if (ast.op === "+" || ast.op === "-") {
        const sb = ast.op === "-" ? k(b, Frac.of(-1)) : b;
        const coef = new Map(a.coef);
        for (const [n, c] of sb.coef) coef.set(n, (coef.get(n) ?? Frac.ZERO).add(c));
        return { coef, c: a.c.add(sb.c) };
      }
      if (ast.op === "*") {
        if (isConst(a)) return k(b, a.c);
        if (isConst(b)) return k(a, b.c);
        return "nonlinear";
      }
      if (ast.op === "/") {
        if (!isConst(b)) return "rational_function";
        return b.c.isZero() ? "div_zero" : k(a, b.c.inv());
      }
      if (!isConst(b) || !b.c.isInt()) return "nonlinear";
      if (isConst(a)) {
        if (b.c.n > BigInt(64) || b.c.n < BigInt(-64)) return "too_big";
        if (a.c.isZero() && b.c.sign < 0) return "div_zero";
        return { coef: new Map(), c: a.c.pow(Number(b.c.n)) };
      }
      return b.c.eq(Frac.ONE) ? a : "nonlinear";
    }
  }
}

// ---- Exact evaluation with surds (used by the leak filter and substitution checks) ------------------------

/** Evaluate at an assignment of letters to exact numbers. Null when it cannot be done exactly. */
export function evalNum(ast: Ast, env: ReadonlyMap<string, QNum> = new Map()): QNum | null {
  switch (ast.t) {
    case "num":
      return qRat(ast.v);
    case "var":
      return env.get(ast.name) ?? null;
    case "neg": {
      const a = evalNum(ast.a, env);
      return a ? qNeg(a) : null;
    }
    case "sqrt": {
      const a = evalNum(ast.a, env);
      return a ? qSqrt(a) : null;
    }
    case "bin": {
      const a = evalNum(ast.a, env);
      const b = evalNum(ast.b, env);
      if (!a || !b) return null;
      if (ast.op === "+") return qAdd(a, b);
      if (ast.op === "-") return qSub(a, b);
      if (ast.op === "*") return qMul(a, b);
      if (ast.op === "/") return qDiv(a, b);
      if (b.d !== BigInt(0) || !b.p.isInt()) return null;
      if (b.p.n > BigInt(64) || b.p.n < BigInt(-64)) return null;
      return qPow(a, Number(b.p.n));
    }
  }
}

// ---- Printing -------------------------------------------------------------------------------------------

const PREC = { "+": 1, "-": 1, "*": 2, "/": 2, "^": 3 } as const;

function render(ast: Ast, pretty: boolean): string {
  const mul = pretty ? " × " : "*";
  const div = pretty ? " ÷ " : "/";
  const go = (n: Ast, parentPrec: number, rightOfNonComm: boolean, leftmost: boolean): string => {
    if (n.t === "num") {
      const s = n.v.toString();
      return n.v.isInt() ? (n.v.sign < 0 ? `(${s})` : s) : `(${s})`;
    }
    if (n.t === "var") return n.name;
    if (n.t === "sqrt") return `√${n.a.t === "num" && n.a.v.isInt() && n.a.v.sign >= 0 ? go(n.a, 0, false, false) : `(${go(n.a, 0, false, true)})`}`;
    if (n.t === "neg") {
      const inner = `-${go(n.a, 2, false, false)}`;
      return leftmost && parentPrec <= 1 ? inner : `(${inner})`;
    }
    const p = PREC[n.op];
    const l = go(n.a, p, false, leftmost && true);
    const r = go(n.b, p, n.op === "-" || n.op === "/" || n.op === "^", false);
    const sym = n.op === "*" ? mul : n.op === "/" ? div : n.op === "^" ? "^" : ` ${n.op} `;
    let text: string;
    if (n.op === "^") {
      const lt = n.a.t === "bin" || n.a.t === "neg" ? `(${go(n.a, 0, false, true)})` : l;
      const rt = n.b.t === "bin" && n.b.op !== "^" ? `(${go(n.b, 0, false, true)})` : r;
      text = `${lt}^${rt}`;
    } else text = `${l}${sym}${r}`;
    const need = p < parentPrec || (rightOfNonComm && p === parentPrec);
    return need ? `(${text})` : text;
  };
  return go(ast, 0, false, true);
}

/** Canonical explicit text: parseable by this parser and by Python's ast after `^` becomes `**`. */
export function canon(ast: Ast): string {
  return render(ast, false);
}
/** Readable text with multiplication and division signs. */
export function showAst(ast: Ast): string {
  return render(ast, true);
}

export function renameAst(ast: Ast, map: ReadonlyMap<string, string>): Ast {
  if (ast.t === "var") return { t: "var", name: map.get(ast.name) ?? ast.name };
  if (ast.t === "neg" || ast.t === "sqrt") return { t: ast.t, a: renameAst(ast.a, map) };
  if (ast.t === "bin") return { t: "bin", op: ast.op, a: renameAst(ast.a, map), b: renameAst(ast.b, map) };
  return ast;
}
