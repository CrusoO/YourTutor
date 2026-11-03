/**
 * A small, safe evaluator for the formulas a model writes into interactive lesson widgets
 * (`slider_sim`, `graph_explore`). It is a recursive-descent parser over a fixed grammar: numbers,
 * the variables the caller names, + - * / ^, brackets and a short list of functions. There is no
 * eval, no `new Function` and no property access, so a formula can compute and nothing else.
 *
 * This is deliberately separate from lib/offline/math.ts, which mirrors the Python answer-checking
 * allowlist and must stay in step with it.
 */

export type Env = Readonly<Record<string, number>>;
export type Formula = (env: Env) => number;

const MAX_LENGTH = 200;
const MAX_DEPTH = 12;

// Maps, not object literals: a name like "constructor" must never resolve through Object.prototype.
const FUNCTIONS: ReadonlyMap<string, (x: number) => number> = new Map([
  ["sqrt", Math.sqrt],
  ["exp", Math.exp],
  ["ln", Math.log],
  ["log", Math.log10],
  ["abs", Math.abs],
  ["sin", Math.sin],
  ["cos", Math.cos],
  ["tan", Math.tan],
]);
const CONSTANTS: ReadonlyMap<string, number> = new Map([
  ["pi", Math.PI],
  ["e", Math.E],
]);

class FormulaError extends Error {}

type Token = { kind: "num"; value: number } | { kind: "id"; name: string } | { kind: "op"; op: string };

function tokenise(src: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < src.length) {
    const ch = src[i]!;
    if (/\s/.test(ch)) {
      i += 1;
    } else if (/[0-9.]/.test(ch)) {
      const match = /^(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/.exec(src.slice(i));
      if (!match) throw new FormulaError("bad number");
      tokens.push({ kind: "num", value: Number(match[0]) });
      i += match[0].length;
    } else if (/[A-Za-z_]/.test(ch)) {
      const match = /^[A-Za-z_][A-Za-z0-9_]*/.exec(src.slice(i))!;
      tokens.push({ kind: "id", name: match[0] });
      i += match[0].length;
    } else if (ch === "*" && src[i + 1] === "*") {
      tokens.push({ kind: "op", op: "^" });
      i += 2;
    } else if ("+-*/^()".includes(ch)) {
      tokens.push({ kind: "op", op: ch });
      i += 1;
    } else {
      throw new FormulaError(`unexpected character ${ch}`);
    }
  }
  return tokens;
}

/**
 * Compile a formula over the named variables. Returns null for anything outside the grammar, an unknown
 * name, or an expression that is too long or too deeply nested; it never throws.
 */
export function compileFormula(src: string, variables: readonly string[]): Formula | null {
  if (typeof src !== "string" || src.length === 0 || src.length > MAX_LENGTH) return null;
  const allowed = new Set(variables);
  try {
    const tokens = tokenise(src);
    let pos = 0;
    let depth = 0;
    const peekOp = (): string | null => {
      const t = tokens[pos];
      return t && t.kind === "op" ? t.op : null;
    };
    const enter = () => {
      depth += 1;
      if (depth > MAX_DEPTH) throw new FormulaError("too deep");
    };
    const leave = () => {
      depth -= 1;
    };

    const parseExpr = (): Formula => {
      let left = parseTerm();
      for (let op = peekOp(); op === "+" || op === "-"; op = peekOp()) {
        pos += 1;
        const l = left;
        const r = parseTerm();
        left = op === "+" ? (env) => l(env) + r(env) : (env) => l(env) - r(env);
      }
      return left;
    };
    const parseTerm = (): Formula => {
      let left = parseUnary();
      for (let op = peekOp(); op === "*" || op === "/"; op = peekOp()) {
        pos += 1;
        const l = left;
        const r = parseUnary();
        left = op === "*" ? (env) => l(env) * r(env) : (env) => l(env) / r(env);
      }
      return left;
    };
    const parseUnary = (): Formula => {
      const op = peekOp();
      if (op === "-" || op === "+") {
        pos += 1;
        enter();
        const inner = parseUnary();
        leave();
        return op === "-" ? (env) => -inner(env) : inner;
      }
      return parsePower();
    };
    const parsePower = (): Formula => {
      const base = parseAtom();
      if (peekOp() === "^") {
        pos += 1;
        enter();
        const exponent = parseUnary();
        leave();
        return (env) => Math.pow(base(env), exponent(env));
      }
      return base;
    };
    const parseAtom = (): Formula => {
      const token = tokens[pos];
      if (!token) throw new FormulaError("unexpected end");
      pos += 1;
      if (token.kind === "num") {
        const value = token.value;
        return () => value;
      }
      if (token.kind === "id") {
        const fn = FUNCTIONS.get(token.name);
        if (fn && peekOp() === "(") {
          pos += 1;
          enter();
          const arg = parseExpr();
          leave();
          if (peekOp() !== ")") throw new FormulaError("missing )");
          pos += 1;
          return (env) => fn(arg(env));
        }
        const constant = CONSTANTS.get(token.name);
        if (constant !== undefined && !allowed.has(token.name)) return () => constant;
        if (!allowed.has(token.name)) throw new FormulaError(`unknown name ${token.name}`);
        const name = token.name;
        return (env) => (Object.hasOwn(env, name) ? env[name]! : Number.NaN);
      }
      if (token.op === "(") {
        enter();
        const inner = parseExpr();
        leave();
        if (peekOp() !== ")") throw new FormulaError("missing )");
        pos += 1;
        return inner;
      }
      throw new FormulaError(`unexpected ${token.op}`);
    };

    const formula = parseExpr();
    if (pos !== tokens.length) return null;
    return formula;
  } catch (error) {
    if (error instanceof FormulaError) return null;
    throw error;
  }
}

/** `n` evenly spaced values from lo to hi inclusive. */
export function linspace(lo: number, hi: number, n: number): number[] {
  if (n < 2) return [lo];
  return Array.from({ length: n }, (_, i) => lo + ((hi - lo) * i) / (n - 1));
}

/** True when the formula gives a finite number at every sample of its variable (guards a widget from NaN or Infinity). */
export function finiteOver(formula: Formula, variable: string, lo: number, hi: number, base: Env = {}): boolean {
  return linspace(lo, hi, 25).every((x) => Number.isFinite(formula({ ...base, [variable]: x })));
}
