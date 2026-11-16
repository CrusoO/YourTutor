import { PUSHBACK_COPY } from "./copy.en";
import { substituteCheck } from "./attempt";
import { type AnswerSet, answerSetFor, contradictsKey, wordsToDigits } from "./leak";
import { evalNum, normalizeMath, parseExpr } from "./parse";
import { type QNum, qToString } from "./surd";
import type { MathCandidate, Solution } from "./types";

/**
 * When a student pushes back ("my book says 3"), the answer is not a debate: the claimed value is put back into the
 * equation, exactly. A contradicts_key result outranks any chat reply, so a model can reword but never overrule.
 * Phrases are data (like the finder rules) and matching is on the device.
 */

export const DEFAULT_PUSHBACK_PHRASES: string[] = [
  "that's wrong", "thats wrong", "that is wrong", "this is wrong", "wrong answer", "you are wrong", "youre wrong",
  "not correct", "incorrect", "not right", "my book says", "book says", "teacher said", "teacher says", "my teacher",
  "answer key", "i got", "i think it is", "are you sure", "galat", "ghalat", "गलत", "ग़लत",
];

export type PushbackDetect = { pushback: boolean; claim: string | null };

export function detectPushback(text: string, phrases: readonly string[] = DEFAULT_PUSHBACK_PHRASES): PushbackDetect {
  const norm = wordsToDigits(normalizeMath(text)).replace(/[’‘]/g, "'");
  if (!phrases.some((p) => norm.includes(p.toLowerCase()))) return { pushback: false, claim: null };
  const re = /(?:=|\bis\b|\bsays?\b|\bsaid\b|\bgot\b|\banswer\b|\bgives?\b)\s*([-+]?\s*[0-9(√][0-9.+\-*/^()√\s]*)/g;
  let claim: string | null = null;
  for (const m of norm.matchAll(re)) {
    const body = m[1].trim().replace(/[+\-*/^\s]+$/, "");
    if (parseExpr(body).ok) claim = body;
  }
  return { pushback: true, claim };
}

export type PushbackVerdict = "claim_fails" | "claim_works" | "unreadable";
export type PushbackResult = {
  verdict: PushbackVerdict;
  /** Deterministic reply. Always safe to show. */
  text: string;
  /** True when the claim, or a chat reply checked with `checkChatReply`, contradicts the key. */
  contradictsKey: boolean;
};

export function resolvePushback(c: MathCandidate, sol: Solution, claim: string | null): PushbackResult {
  const unreadable: PushbackResult = { verdict: "unreadable", text: PUSHBACK_COPY.unreadable, contradictsKey: false };
  if (!claim || (c.kind !== "poly_eq" && c.kind !== "linear_system")) return unreadable;
  const parsed = parseExpr(claim);
  const value: QNum | null = parsed.ok ? evalNum(parsed.ast) : null;
  if (!value || c.kind === "linear_system" || sol.status !== "solved") return unreadable;
  const chk = substituteCheck(c, new Map([[c.variable, value]]));
  if (!chk) return unreadable;
  const shown = qToString(value);
  if (chk.ok) return { verdict: "claim_works", text: PUSHBACK_COPY.claimWorks(c.variable, shown), contradictsKey: false };
  return {
    verdict: "claim_fails",
    text: PUSHBACK_COPY.claimFails(c.variable, shown, chk.sides[0].l, chk.sides[0].r),
    contradictsKey: true,
  };
}

/** Does a chat model's reply state a value that is not an answer? Then the deterministic text replaces it. */
export function checkChatReply(reply: string, answers: AnswerSet): boolean {
  return contradictsKey(reply, answers).contradicts;
}

/** The text the thread shows. A contradicts_key result always wins over the chat reply. */
export function finalReply(result: PushbackResult, chatReply: string | null, answers: AnswerSet | null): { text: string; source: "deterministic" | "chat" } {
  const replyBad = chatReply !== null && answers !== null && checkChatReply(chatReply, answers);
  if (result.contradictsKey || replyBad || chatReply === null) return { text: result.text, source: "deterministic" };
  return { text: chatReply, source: "chat" };
}

/** Convenience for the chat wiring: build the answer set once per card. */
export function answersFor(c: MathCandidate, sol: Solution): AnswerSet {
  return answerSetFor(c, sol);
}
