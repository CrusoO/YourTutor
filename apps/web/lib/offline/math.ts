/**
 * Offline mirror of the allowlist parser in apps/api/app/content/math_parse.py.
 *
 * Python uses sympy; the browser has no algebra system, so equivalence is decided by evaluating
 * both sides at fixed sample points. That is exact for numbers and for the polynomial and
 * fraction expressions in this curriculum. Anything the allowlist rejects is not equivalent to
 * anything, exactly as in Python. Only items whose answers this code can judge go into packs.
 */

export type NotationProfile = {
  decimal_separator: string;
  multiply_symbols: string[];
  divide_symbols: string[];
};

export const DEFAULT_NOTATION: NotationProfile = {
  decimal_separator: ".",
  multiply_symbols: ["*", "×", "·"],
  divide_symbols: ["/", "÷"],
};

export class ParseError extends Error {}

const MAX_LEN = 64;
const MAX_PARENS = 8;
const ALLOWED = /^([A-Za-z]\s*=\s*)?[0-9A-Za-z+\-*/^()., ]+$/;
const ND = /\p{Nd}/u;

/** Any Unicode decimal digit becomes its ASCII digit (Python: `unicodedata.digit`). */
function asciiDigits(text: string): string {
  let out = "";
  for (const ch of text) {
    if (ND.test(ch)) {
      const cp = ch.codePointAt(0)!;
      let start = cp;
      while (ND.test(String.fromCodePoint(start - 1))) start -= 1;
      out += String((cp - start) % 10);
    } else {
      out += ch;
    }
  }
  return out;
}

export function normalize(text: string, profile: NotationProfile = DEFAULT_NOTATION): string {
  let s = asciiDigits(text.trim());
  s = s.replace(/−/g, "-").replace(/–/g, "-").replace(/—/g, "-");
  for (const sym of profile.multiply_symbols) if (sym !== "*") s = s.split(sym).join("*");
  for (const sym of profile.divide_symbols) if (sym !== "/") s = s.split(sym).join("/");
  if (profile.decimal_separator === ",") {
    s = s.replace(/(\d),(\d)/g, "$1.$2");
  } else if (s.includes(",") && /\d,\d/.test(s)) {
    throw new ParseError("decimal comma not allowed for this notation profile");
  }
  return s.replace(/\s+/g, " ").trim();
}

type Node = (vars: Record<string, number>) => number;

/** The expression as a function of its single-letter variables. */
function compile(expr: string): { run: Node; names: string[] } {
  if (expr.length > MAX_LEN) throw new ParseError("expression too long");
  if ((expr.match(/\(/g) ?? []).length > MAX_PARENS || expr.includes("__")) {
    throw new ParseError("expression rejected");
  }
  if (!ALLOWED.test(expr)) throw new ParseError("expression failed allowlist");
  let body = expr;
  if (expr.includes("=")) {
    const at = expr.indexOf("=");
    const left = expr.slice(0, at).trim();
    const right = expr.slice(at + 1).trim();
    body = /^[A-Za-z]$/.test(left) ? right : `(${left})-(${right})`;
  }
  body = body.replace(/\^/g, "**");
  body = body.replace(/(\d)([A-Za-z(])/g, "$1*$2").replace(/([A-Za-z)])(\()/g, "$1*$2");
  const names = [...new Set(body.match(/[A-Za-z]/g) ?? [])].sort();
  let pos = 0;
  const peek = () => body[pos];
  const skip = () => {
    while (body[pos] === " ") pos += 1;
  };
  const fail = (): never => {
    throw new ParseError("could not parse expression");
  };

  function parseExpr(): Node {
    let left = parseTerm();
    for (;;) {
      skip();
      const op = peek();
      if (op !== "+" && op !== "-") return left;
      pos += 1;
      const right = parseTerm();
      const l = left;
      left = op === "+" ? (v) => l(v) + right(v) : (v) => l(v) - right(v);
    }
  }
  function parseTerm(): Node {
    let left = parseUnary();
    for (;;) {
      skip();
      const op = body[pos] === "*" && body[pos + 1] !== "*" ? "*" : body[pos] === "/" ? "/" : "";
      if (!op) return left;
      pos += 1;
      const right = parseUnary();
      const l = left;
      left = op === "*" ? (v) => l(v) * right(v) : (v) => l(v) / right(v);
    }
  }
  function parseUnary(): Node {
    skip();
    if (peek() === "-") {
      pos += 1;
      const inner = parseUnary();
      return (v) => -inner(v);
    }
    if (peek() === "+") {
      pos += 1;
      return parseUnary();
    }
    return parsePower();
  }
  function parsePower(): Node {
    const base = parseAtom();
    skip();
    if (body[pos] === "*" && body[pos + 1] === "*") {
      pos += 2;
      const exponent = parseUnary();
      return (v) => Math.pow(base(v), exponent(v));
    }
    return base;
  }
  function parseAtom(): Node {
    skip();
    const c = peek();
    if (c === "(") {
      pos += 1;
      const inner = parseExpr();
      skip();
      if (peek() !== ")") fail();
      pos += 1;
      return inner;
    }
    const num = /^\d+(?:\.\d*)?|^\.\d+/.exec(body.slice(pos));
    if (num) {
      if (/^0\d/.test(num[0])) fail(); // Python rejects 05 as a literal
      pos += num[0].length;
      const value = Number(num[0]);
      return () => value;
    }
    if (c !== undefined && /[A-Za-z]/.test(c)) {
      pos += 1;
      return (v) => v[c];
    }
    return fail();
  }
  const run = parseExpr();
  skip();
  if (pos !== body.length) fail();
  return { run, names };
}

const SAMPLES = [2, 3, 5, -1.5, 0.5, 7];

/** A response or answer as a number when it has no free variable (`x = 4` counts as 4). */
export function numericValue(text: string, profile?: NotationProfile): number | null {
  try {
    const { run, names } = compile(normalize(text, profile));
    if (names.length) return null;
    const value = run({});
    return Number.isFinite(value) ? value : null;
  } catch (error) {
    if (error instanceof ParseError) return null;
    throw error;
  }
}

export function expressionsEquivalent(left: string, right: string, profile?: NotationProfile) {
  let a: ReturnType<typeof compile>;
  let b: ReturnType<typeof compile>;
  try {
    a = compile(normalize(left, profile));
    b = compile(normalize(right, profile));
  } catch (error) {
    if (error instanceof ParseError) return false;
    throw error;
  }
  const names = [...new Set([...a.names, ...b.names])].sort();
  const rows = names.length ? SAMPLES.map((_, i) => i) : [0];
  for (const row of rows) {
    const vars: Record<string, number> = {};
    names.forEach((name, k) => {
      vars[name] = SAMPLES[(row + k * 2) % SAMPLES.length];
    });
    const x = a.run(vars);
    const y = b.run(vars);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return false;
    if (Math.abs(x - y) >= 1e-9 * Math.max(1, Math.abs(x), Math.abs(y))) return false;
  }
  return true;
}

export function parses(text: string, profile?: NotationProfile): boolean {
  try {
    compile(normalize(text, profile));
    return true;
  } catch (error) {
    if (error instanceof ParseError) return false;
    throw error;
  }
}
