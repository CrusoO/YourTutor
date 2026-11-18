/**
 * Plain integer arithmetic in a question stem ("Compute 10 + (-7).") and everything the screen says about it.
 * Every number the student sees in the explanation comes from this parse and from this arithmetic, never from model
 * text. There is no eval and no dependency: the stem is matched against one small grammar.
 *
 * Grammar (after trimming): [word] operand op operand [. | = | = ?]
 *   word     Compute | Evaluate | Find | Work out | Calculate | Simplify | What is
 *   operand  whole number, optionally signed, or the same in parentheses: 7  -7  (-7)  (+7)
 *   op       +  -  (also the typographic minus and en dash)
 * Whole numbers only (no decimals, no letters), at most MAX_DIGITS digits each.
 */

export const MAX_DIGITS = 3;

export type IntegerStem = {
  /** The first number, with its own sign. */
  start: number;
  /** The sign written between the two numbers. */
  op: "+" | "-";
  /** The second number, with its own sign as written (-7 in "10 + (-7)"). */
  operand: number;
  /** start op operand, computed here. */
  result: number;
};

const MINUS = /[−–—]/g;
const WORD = "(?:compute|evaluate|find|calculate|simplify|work out|what is)";
const NUM = String.raw`(?:\(\s*[+-]?\s*\d{1,${MAX_DIGITS}}\s*\)|[+-]?\s*\d{1,${MAX_DIGITS}})`;
const STEM = new RegExp(String.raw`^(?:${WORD}\s*:?\s+)?(${NUM})\s*([+-])\s*(${NUM})\s*(?:[.?]|=\s*\??\s*\.?)?$`, "i");

function toInt(raw: string): number {
  const digits = raw.replace(/[()\s]/g, "");
  return Number(digits);
}

/** The parse of a stem that is simple integer arithmetic, or null. */
export function parseIntegerStem(stem: string | null | undefined): IntegerStem | null {
  if (typeof stem !== "string" || stem.length === 0 || stem.length > 80) return null;
  const text = stem.replace(MINUS, "-").trim();
  const m = STEM.exec(text);
  if (!m) return null;
  const start = toInt(m[1]);
  const op = m[2] as "+" | "-";
  const operand = toInt(m[3]);
  if (!Number.isInteger(start) || !Number.isInteger(operand)) return null;
  const result = op === "+" ? start + operand : start - operand;
  return { start, op, operand, result };
}

/** A whole number written the way a student writes it, with a real minus sign for the screen. */
export function fmt(n: number): string {
  return n < 0 ? `−${Math.abs(n)}` : String(n);
}

/** True when the item's answer is the whole number the parse computed. */
export function answerMatches(parse: IntegerStem, answer: string | null | undefined): boolean {
  if (typeof answer !== "string") return false;
  const text = answer.replace(MINUS, "-").trim();
  if (!/^[+-]?\d{1,7}$/.test(text)) return false;
  return Number(text) === parse.result;
}

/** The parse of a stem, only when its computed result equals the item's answer. For the solution screen. */
export function verifiedParse(stem: string | null | undefined, answer: string | null | undefined): IntegerStem | null {
  const parse = parseIntegerStem(stem);
  return parse && answerMatches(parse, answer) ? parse : null;
}

/** How far and which way the dot moves: positive is right. */
export function move(parse: IntegerStem): number {
  return parse.op === "+" ? parse.operand : -parse.operand;
}

export type SignCase = "plus" | "minus" | "add-negative" | "subtract-negative";

export function signCase(parse: IntegerStem): SignCase {
  if (parse.op === "+") return parse.operand < 0 ? "add-negative" : "plus";
  return parse.operand < 0 ? "subtract-negative" : "minus";
}

export type SignCopy = {
  signRule: string;
  signAddNegative: string;
  signSubtractNegative: string;
  signMovePlus: string;
  signMoveMinus: string;
  signMoveNone: string;
  signStart: string;
  signLand: string;
  signAdding: string;
  signSubtracting: string;
  signUnitOne: string;
  signUnitMany: string;
  signStepOne: string;
};

/** The general rule, then the line that fits this sum (null when no extra line is needed). */
export function signRuleLines(parse: IntegerStem, copy: SignCopy): { general: string; specific: string | null } {
  const kind = signCase(parse);
  return {
    general: copy.signRule,
    specific:
      kind === "add-negative" ? copy.signAddNegative : kind === "subtract-negative" ? copy.signSubtractNegative : null,
  };
}

function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => String(values[k] ?? ""));
}

/** The move as a sentence: "Adding -7 means move 7 steps left." */
export function moveSentence(parse: IntegerStem, copy: SignCopy): string {
  const delta = move(parse);
  const verb = parse.op === "+" ? copy.signAdding : copy.signSubtracting;
  const tail =
    delta === 0
      ? copy.signMoveNone
      : fill(delta > 0 ? copy.signMovePlus : copy.signMoveMinus, { n: Math.abs(delta), unit: Math.abs(delta) === 1 ? copy.signUnitOne : copy.signUnitMany });
  return fill(verb, { x: fmt(parse.operand), move: tail });
}

/** "Start at 10." / the move / "You land on 3." The last is left out when `withResult` is false (the hint). */
export function explanationSteps(parse: IntegerStem, copy: SignCopy, withResult = true): string[] {
  const steps = [fill(copy.signStepOne, { start: fmt(parse.start) }), moveSentence(parse, copy)];
  if (withResult) steps.push(fill(copy.signLand, { result: fmt(parse.result) }));
  return steps;
}

/** The Show me on a number line button: only for an integer stem, and only once the student has tried or asked. */
export function showSignHintButton(
  parse: IntegerStem | null,
  state: { wrongOnce: boolean; helpAsked: boolean; hintShown: boolean },
): boolean {
  return parse !== null && (state.wrongOnce || state.helpAsked || state.hintShown);
}

/** A solution step of the form "x = 6" is stray when the question has no letter x in it. */
export function visibleSteps(steps: string[] | undefined, stem: string | null | undefined): string[] {
  const list = steps ?? [];
  if (/\bx\b/i.test(stem ?? "")) return list;
  return list.filter((row) => !/^\s*(?:\d+\s*[.)]\s*)?x\s*=/i.test(row));
}

/** The source chip in plain words. Notes an author wrote are called "the lesson"; "integers" becomes "whole numbers". */
export function plainSourceLabel(title: string): string {
  if (!/authored\s+notes?/i.test(title)) return title;
  const base = title
    .replace(/\s*[([]\s*authored\s+notes?\s*[)\]]/gi, "")
    .replace(/\s*[-–—:,]\s*authored\s+notes?\b/gi, "")
    .replace(/\bauthored\s+notes?\b/gi, "")
    .replace(/\bintegers\b/gi, (w) => (w[0] === "I" ? "Whole numbers" : "whole numbers"))
    .replace(/\s{2,}/g, " ")
    .trim();
  return base ? `From the lesson: ${base}` : "From the lesson";
}
