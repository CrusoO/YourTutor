import { Frac } from "./frac";
import {
  canon,
  collectLetters,
  evalNum,
  FUNCTION_WORDS,
  normalizeMath,
  parseExpr,
  renameAst as rename,
  showAst,
  toLinear,
  toPoly,
} from "./parse";
import { DEFAULT_DETECT_WORDS, type DetectWords } from "./rules";
import { qToString } from "./surd";
import type { Ast, Detect, MathCandidate, ParseFail } from "./types";

/**
 * Decides whether typed text contains a solvable maths expression. Pure and on the device: the text never leaves it.
 * A sentence is not a candidate; digit runs of ten or more (phone numbers) are removed before anything is read.
 */
export type DetectOptions = { maxLen?: number; words?: DetectWords };

const MAX_DIGITS = 9;
const OPERATOR = /[+\-*/^=√]/;

function stripPrivate(s: string): string {
  let out = s.replace(/\S*(?:@|https?:|www\.)\S*/g, " ");
  out = out.replace(/\+?\d[\d\s().-]{8,}\d/g, (m) => {
    const digits = m.replace(/\D/g, "").length;
    return digits >= 10 && !/\s[-+]\s/.test(m) ? " " : m;
  });
  return out.replace(/\d{10,}/g, " ");
}


function isMathToken(tok: string): boolean {
  if (!/^[0-9a-z+\-*/^().=√]+$/.test(tok)) return false;
  const runs = tok.match(/[a-z]+/g) ?? [];
  return runs.every((r) => r.length === 1 || r === "sqrt" || FUNCTION_WORDS.has(r));
}

type Seg = { run: string | null; sentence: boolean; stray: string[]; multiRun: boolean };

function analyseSegment(segment: string, fillers: Set<string>): Seg {
  const tokens = segment
    .split(/\s+/)
    .map((t) => t.replace(/[?!:;,]+$/g, "").replace(/\.$/, ""))
    .filter(Boolean);
  const runs: string[][] = [];
  let cur: string[] = [];
  let sentence = false;
  const flush = () => {
    if (cur.length) runs.push(cur);
    cur = [];
  };
  for (const raw of tokens) {
    if (fillers.has(raw)) flush();
    else if (isMathToken(raw)) cur.push(raw);
    else {
      sentence = true;
      flush();
    }
  }
  flush();
  const good: string[] = [];
  const stray: string[] = [];
  for (const r of runs) {
    const joined = r.join(" ");
    const operands = (joined.match(/\d+(?:\.\d+)?|[a-z]/g) ?? []).length;
    if (OPERATOR.test(joined) && operands >= 2) good.push(joined);
    else stray.push(...(joined.match(/[a-z]/g) ?? []), ...(/[+\-*/^=]/.test(joined) ? ["#"] : []));
  }
  return { run: good[0] ?? null, sentence, stray, multiRun: good.length > 1 };
}

type Side = { ast: Ast };
function parseSide(text: string): { ok: true; side: Side } | { ok: false; why: ParseFail } {
  const p = parseExpr(text, { maxDigits: MAX_DIGITS });
  return p.ok ? { ok: true, side: { ast: p.ast } } : p;
}

type Eq = { l: Ast; r: Ast };
function parseRun(run: string): { eq: Eq } | { expr: Ast } | { why: ParseFail } {
  let text = run.replace(/\s*=\s*$/, "").trim();
  const parts = text.split("=");
  if (parts.length > 2) return { why: "parse" };
  if (parts.length === 1) {
    const e = parseSide(text);
    return e.ok ? { expr: e.side.ast } : { why: e.why };
  }
  text = "";
  const l = parseSide(parts[0]);
  if (!l.ok) return { why: l.why };
  const r = parseSide(parts[1]);
  if (!r.ok) return { why: r.why };
  return { eq: { l: l.side.ast, r: r.side.ast } };
}

function lettersOf(...asts: Ast[]): string[] {
  const s = new Set<string>();
  for (const a of asts) collectLetters(a, s);
  return [...s].sort();
}

export function detectMath(text: string, opts: DetectOptions = {}): Detect {
  const maxLen = opts.maxLen ?? 400;
  if (text.length > maxLen) return { kind: "unsupported", why: "too_big" };
  const words = opts.words ?? DEFAULT_DETECT_WORDS;
  const fillers = new Set(words.fillers.map((w) => w.toLowerCase()));
  const splitters = new Set(words.splitters.map((w) => w.toLowerCase()));

  let s = stripPrivate(normalizeMath(text));
  if (/[<>≤≥]/.test(s) && /\d/.test(s)) return { kind: "unsupported", why: "inequality" };
  s = s.replace(/(\d)\s+x\s+(\d)/g, "$1*$2");
  const segments = s
    .split(/[;,\n]+/)
    .flatMap((seg) =>
      seg
        .split(/\s+/)
        .reduce<string[]>(
          (acc, tok) => {
            if (splitters.has(tok)) acc.push("");
            else acc[acc.length - 1] += ` ${tok}`;
            return acc;
          },
          [""],
        ),
    )
    .map((t) => t.trim())
    .filter(Boolean);

  const analysed = segments.map((seg) => analyseSegment(seg, fillers));
  const hasMathy = /\d/.test(s) && /[+*/^=√]/.test(s);
  if (analysed.some((a) => a.sentence)) {
    return hasMathy ? { kind: "unsupported", why: "word_problem" } : { kind: "none" };
  }
  const withRun = analysed.filter((a) => a.run);
  if (withRun.length === 0) return { kind: "none" };
  if (analysed.some((a) => a.multiRun)) return { kind: "unsupported", why: "parse" };
  if (withRun.length > 2) return { kind: "unsupported", why: "multi_unknown" };

  const parsed = withRun.map((a) => parseRun(a.run as string));
  for (const p of parsed) if ("why" in p) return { kind: "unsupported", why: p.why };
  const strayLetters = new Set(analysed.flatMap((a) => a.stray));
  if (strayLetters.has("#")) return { kind: "none" };

  if (withRun.length === 2) return buildSystem(parsed, strayLetters);

  const only = parsed[0];
  if ("eq" in only) {
    const letters = lettersOf(only.eq.l, only.eq.r);
    if (letters.length > 1) return { kind: "unsupported", why: "multi_unknown" };
    if (![...strayLetters].every((l) => letters.includes(l))) return { kind: "none" };
    return letters.length === 0 ? buildArithClaim(only.eq) : buildPolyEq(only.eq, letters[0]);
  }
  if (!("expr" in only)) return { kind: "unsupported", why: "parse" };
  const letters = lettersOf(only.expr);
  if (letters.length > 1) return { kind: "unsupported", why: "multi_unknown" };
  if (![...strayLetters].every((l) => letters.includes(l))) return { kind: "none" };
  return letters.length === 0 ? buildArith(only.expr) : buildSimplify(only.expr, letters[0]);
}

function checkConst(ast: Ast): ParseFail | null {
  const p = toPoly(ast, null);
  return p.ok ? null : p.why;
}

function buildArith(ast: Ast, claimedAst?: Ast): Detect {
  const bad = checkConst(ast);
  if (bad) return { kind: "unsupported", why: bad };
  const candidate: MathCandidate = { schema: "doubt-expr/1", kind: "arith", variable: "x", display: showAst(ast), expr: canon(ast) };
  if (claimedAst) {
    const c = evalNum(claimedAst);
    if (!c || c.d !== BigInt(0)) return { kind: "unsupported", why: "parse" };
    candidate.claimed = qToString(c);
    candidate.display = `${showAst(ast)} = ${showAst(claimedAst)}`;
  }
  return { kind: "candidate", candidate };
}

function buildArithClaim(eq: Eq): Detect {
  const bad = checkConst(eq.r);
  return bad ? { kind: "unsupported", why: bad } : buildArith(eq.l, eq.r);
}

function buildSimplify(ast: Ast, letter: string): Detect {
  const p = toPoly(rename(ast, new Map([[letter, "x"]])), "x");
  if (!p.ok) return { kind: "unsupported", why: p.why };
  return {
    kind: "candidate",
    candidate: {
      schema: "doubt-expr/1",
      kind: "poly_simplify",
      variable: letter,
      display: showAst(ast),
      expr: canon(rename(ast, new Map([[letter, "x"]]))),
    },
  };
}

function buildPolyEq(eq: Eq, letter: string): Detect {
  const map = new Map([[letter, "x"]]);
  const l = rename(eq.l, map);
  const r = rename(eq.r, map);
  const pl = toPoly(l, "x");
  if (!pl.ok) return { kind: "unsupported", why: pl.why };
  const pr = toPoly(r, "x");
  if (!pr.ok) return { kind: "unsupported", why: pr.why };
  return {
    kind: "candidate",
    candidate: {
      schema: "doubt-expr/1",
      kind: "poly_eq",
      variable: letter,
      display: `${showAst(eq.l)} = ${showAst(eq.r)}`,
      lhsText: canon(l),
      rhsText: canon(r),
      lhs: pl.poly.toStrings(),
      rhs: pr.poly.toStrings(),
    },
  };
}

function buildSystem(parsed: ({ eq: Eq } | { expr: Ast } | { why: ParseFail })[], stray: Set<string>): Detect {
  const eqs: Eq[] = [];
  for (const p of parsed) {
    if (!("eq" in p)) return { kind: "unsupported", why: "parse" };
    eqs.push(p.eq);
  }
  const letters = lettersOf(...eqs.flatMap((e) => [e.l, e.r]));
  if (letters.length !== 2) return { kind: "unsupported", why: "multi_unknown" };
  if (![...stray].every((l) => letters.includes(l))) return { kind: "none" };
  const map = new Map([
    [letters[0], "x"],
    [letters[1], "y"],
  ]);
  const coeffs: string[][] = [];
  const consts: string[] = [];
  const texts: string[] = [];
  for (const e of eqs) {
    const l = rename(e.l, map);
    const r = rename(e.r, map);
    const a = toLinear(l);
    const b = toLinear(r);
    if (!a.ok) return { kind: "unsupported", why: a.why };
    if (!b.ok) return { kind: "unsupported", why: b.why };
    const cx = (a.lin.coef.get("x") ?? zero()).sub(b.lin.coef.get("x") ?? zero());
    const cy = (a.lin.coef.get("y") ?? zero()).sub(b.lin.coef.get("y") ?? zero());
    coeffs.push([cx.toString(), cy.toString()]);
    consts.push(b.lin.c.sub(a.lin.c).toString());
    texts.push(`${canon(l)}=${canon(r)}`);
  }
  return {
    kind: "candidate",
    candidate: {
      schema: "doubt-expr/1",
      kind: "linear_system",
      variable: `${letters[0]}${letters[1]}`,
      display: eqs.map((e) => `${showAst(e.l)} = ${showAst(e.r)}`).join(";  "),
      system: { coeffs, consts, texts },
    },
  };
}

function zero(): Frac {
  return Frac.ZERO;
}
