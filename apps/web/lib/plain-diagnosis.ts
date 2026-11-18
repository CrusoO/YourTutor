/**
 * A guard for the one sentence that says what the learner may have done wrong. That sentence comes from
 * content we do not own here; if it is too long or leans on textbook words, show the gentle generic line.
 */
const JARGON = [
  "inverse",
  "coefficient",
  "variable",
  "integer",
  "commutative",
  "distributive",
  "constant term",
  "expression",
  "evaluate",
];

const MAX_WORDS = 25;
const JARGON_RE = new RegExp(String.raw`\b(${JARGON.join("|")})(s|es)?\b`, "i");

/** True when the sentence is short and plain enough to show a student as it is. */
export function isPlainSentence(text: unknown): text is string {
  if (typeof text !== "string") return false;
  const clean = text.trim();
  if (!clean) return false;
  if (clean.split(/\s+/).length > MAX_WORDS) return false;
  return !JARGON_RE.test(clean);
}

/** The described mistake to show, or null when there is none or it is not plain enough. */
export function plainMistake(diagnosis: { description?: unknown; misconception_text?: unknown } | undefined): string | null {
  for (const candidate of [diagnosis?.description, diagnosis?.misconception_text]) {
    if (isPlainSentence(candidate)) return candidate.trim();
  }
  return null;
}
