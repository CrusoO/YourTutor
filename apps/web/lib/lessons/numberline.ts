/**
 * Pure number-line maths and wording for integer moves. No React, no browser, no model:
 * the component draws what these functions return, and the narration is built from the numbers.
 * Wording here is original and English; dynamic sentences are built from the numbers only.
 */

export const NUMBER_LINE_LIMIT = 20;
const MINUS = "−";

export type Direction = "right" | "left";

/** A whole number in -20..20. */
export function isSafeInt(n: unknown): n is number {
  return typeof n === "number" && Number.isInteger(n) && Math.abs(n) <= NUMBER_LINE_LIMIT;
}

/** The figure can be drawn: whole numbers, a real move, and the start and landing both on the line. */
export function isSafeFigure(start: unknown, delta: unknown): boolean {
  return isSafeInt(start) && isSafeInt(delta) && delta !== 0 && isSafeInt(start + delta);
}

export function landing(start: number, delta: number): number {
  return start + delta;
}

/** Positive moves right (adding), negative moves left (subtracting). */
export function directionOf(delta: number): Direction {
  return delta >= 0 ? "right" : "left";
}

/** Every position the marker visits, start to landing inclusive: one entry per hop plus the start. */
export function pathPoints(start: number, delta: number): number[] {
  const step = delta >= 0 ? 1 : -1;
  const out = [start];
  for (let i = 0; i < Math.abs(delta); i++) out.push(start + step * (i + 1));
  return out;
}

export function clampToLine(n: number, min = -NUMBER_LINE_LIMIT, max = NUMBER_LINE_LIMIT): number {
  return Math.max(min, Math.min(max, Math.round(n)));
}

/** The part of the line to draw: covers zero, start, landing and any guess, with room either side. */
export function viewWindow(points: number[]): { min: number; max: number } {
  let min = Math.min(0, ...points) - 1;
  let max = Math.max(0, ...points) + 1;
  while (max - min < 10) {
    min -= 1;
    max += 1;
  }
  min = Math.max(-NUMBER_LINE_LIMIT, min);
  max = Math.min(NUMBER_LINE_LIMIT, max);
  return { min, max };
}

/** Map a horizontal pixel position inside the drawn line to the nearest whole number in the window. */
export function valueFromX(
  x: number,
  left: number,
  width: number,
  win: { min: number; max: number },
  padFraction = 0,
): number {
  if (width <= 0) return win.min;
  const pad = width * padFraction;
  const usable = Math.max(1, width - 2 * pad);
  const t = Math.max(0, Math.min(1, (x - left - pad) / usable));
  return clampToLine(win.min + t * (win.max - win.min), win.min, win.max);
}

/** A number as drawn: a real minus sign, never a hyphen. */
export function fmt(n: number): string {
  return n < 0 ? `${MINUS}${Math.abs(n)}` : String(n);
}

/** The sum as written: "−8 + 5" or "3 − 7". */
export function expression(start: number, delta: number): string {
  return `${fmt(start)} ${delta >= 0 ? "+" : MINUS} ${Math.abs(delta)}`;
}

/** The token on the line: "+5" or "−7". */
export function tokenText(delta: number): string {
  return delta >= 0 ? `+${delta}` : `${MINUS}${Math.abs(delta)}`;
}

const ONES = [
  "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
  "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
  "nineteen", "twenty",
];

/** Spoken form: "minus eight". Safe numbers only. */
export function numberWords(n: number): string {
  if (!isSafeInt(n)) return String(n);
  return n < 0 ? `minus ${ONES[-n]}` : ONES[n];
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const stepsWord = (n: number) => `${numberWords(n)} ${n === 1 ? "step" : "steps"}`;

/** "Start at minus eight. Add five: five steps to the right." */
export function setupScript(start: number, delta: number): string {
  const n = Math.abs(delta);
  const verb = delta >= 0 ? "Add" : "Subtract";
  return `Start at ${numberWords(start)}. ${verb} ${numberWords(n)}: ${stepsWord(n)} to the ${directionOf(delta)}.`;
}

/** The full script read aloud: setup, every stop along the way, then the landing. */
export function narrationScript(start: number, delta: number): string {
  if (!isSafeFigure(start, delta)) return "";
  const stops = pathPoints(start, delta).slice(1).map(numberWords).join(", ");
  return `${setupScript(start, delta)} ${cap(stops)}. You land on ${numberWords(start + delta)}.`;
}

/** What is read before the answer is known. */
export function predictScript(start: number, delta: number): string {
  if (!isSafeFigure(start, delta)) return "";
  return `${setupScript(start, delta)} Where do you think you land?`;
}

/** Short line for a screen reader after each hop: "Hop 2 of 5: minus six." */
export function hopAnnouncement(hop: number, total: number, position: number): string {
  if (hop <= 0) return `Start at ${numberWords(position)}.`;
  const base = `Hop ${hop} of ${total}: ${numberWords(position)}.`;
  return hop === total ? `${base} You land on ${numberWords(position)}.` : base;
}

export type PredictionKind = "correct" | "other_way" | "other_side_of_zero" | "forgot_start" | "stayed" | "off";

export type PredictionResult = {
  correct: boolean;
  kind: PredictionKind;
  landing: number;
  guess: number;
  /** Plain words. Says what the move does; never a scold. */
  reason: string;
};

/** Compare a guess with the true landing and explain the gap in plain words. */
export function checkPrediction(start: number, delta: number, guess: number): PredictionResult {
  const land = start + delta;
  const n = Math.abs(delta);
  const dir = directionOf(delta);
  const verb = delta >= 0 ? "Adding" : "Subtracting";
  const base = { landing: land, guess };
  if (guess === land) {
    return { ...base, correct: true, kind: "correct", reason: `Yes. ${expression(start, delta)} lands on ${fmt(land)}.` };
  }
  const truth = `${verb} ${n} moves ${n} ${n === 1 ? "step" : "steps"} ${dir} from ${fmt(start)}, so it lands on ${fmt(land)}.`;
  if (guess === start) {
    return { ...base, correct: false, kind: "stayed", reason: `The dot has not moved yet. ${truth}` };
  }
  if (guess === start - delta) {
    const other = delta >= 0 ? "left" : "right";
    return {
      ...base,
      correct: false,
      kind: "other_way",
      reason: `${fmt(guess)} is the same number of steps, but ${other}. ${truth}`,
    };
  }
  if (land !== 0 && guess === -land) {
    return {
      ...base,
      correct: false,
      kind: "other_side_of_zero",
      reason: `${fmt(guess)} is the right distance from zero, but on the other side of it. ${truth}`,
    };
  }
  if (guess === delta) {
    return {
      ...base,
      correct: false,
      kind: "forgot_start",
      reason: `${fmt(guess)} is where the move would end if it began at zero. This one begins at ${fmt(start)}. ${truth}`,
    };
  }
  const gap = Math.abs(guess - land);
  return {
    ...base,
    correct: false,
    kind: "off",
    reason: `You picked ${fmt(guess)}, which is ${gap} ${gap === 1 ? "step" : "steps"} from where it lands. ${truth}`,
  };
}

/** Marker position as a spoken value for a slider: "minus three". */
export function valueText(n: number): string {
  return numberWords(n);
}

/**
 * Turn a number the learner placed into the value string of a predict choice, when one matches
 * (choices may use a typographic minus); otherwise the plain integer as text.
 */
export function guessToChoiceValue(guess: number, choices: { value: string }[]): string {
  const hit = choices.find((c) => Number(c.value.replace(/[−–]/g, "-")) === guess);
  return hit ? hit.value : String(guess);
}

/** The reverse: the number a choice value stands for, or null when it is not a whole number. */
export function choiceValueToNumber(value: string): number | null {
  const plain = value.trim().replace(/[−–]/g, "-");
  return /^-?\d+$/.test(plain) ? Number(plain) : null;
}
