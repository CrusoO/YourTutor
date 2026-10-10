/**
 * Offline answer check, a mirror of apps/api/app/verifier/check.py for the item types a pack
 * may contain: exact and accept-list matches, multiple choice, and numeric or simple algebraic
 * equivalence. The client's own verdict is a convenience only; the server re-checks on sync.
 */

import {
  DEFAULT_NOTATION,
  expressionsEquivalent,
  normalize,
  type NotationProfile,
} from "./math";

export type VerifyItem = {
  type: string;
  answer_sympy: string;
  accept?: string[];
  options?: { id: string; en?: string }[];
};

/** The phrases the server treats as "I don't know" (the pack carries the server's own list). */
export const DONT_KNOW = [
  "i don't know",
  "i dont know",
  "don't know",
  "dont know",
  "idk",
  "i do not know",
];

export function isDontKnow(response: string | null | undefined, list = DONT_KNOW): boolean {
  if (!response) return false;
  let text: string;
  try {
    text = normalize(response);
  } catch {
    text = response.trim();
  }
  return list.includes(text.toLowerCase());
}

export function verifyResponse(
  response: string,
  item: VerifyItem,
  profile: NotationProfile = DEFAULT_NOTATION,
  dontKnow: string[] = DONT_KNOW,
): boolean {
  if (isDontKnow(response, dontKnow)) return false;
  let text: string;
  let expected: string;
  let accepted: string[];
  try {
    text = normalize(response, profile);
    expected = normalize(item.answer_sympy, profile);
    accepted = (item.accept ?? []).map((a) => normalize(a, profile));
  } catch {
    return false;
  }
  if (text === expected || accepted.includes(text)) return true;
  if (item.type === "mcq") return mcqMatch(text, expected, item.options ?? []);
  if (expressionsEquivalent(text, item.answer_sympy, profile)) return true;
  if (text.includes("=")) {
    const rhs = text.slice(text.lastIndexOf("=") + 1);
    if (expressionsEquivalent(rhs, item.answer_sympy, profile)) return true;
  }
  return false;
}

function mcqMatch(text: string, expected: string, options: { id: string; en?: string }[]) {
  if (text === expected) return true;
  for (const option of options) {
    const oid = normalize(String(option.id ?? ""));
    const label = normalize(String(option.en ?? ""));
    if ((text === oid || text === label) && oid === expected) return true;
  }
  return false;
}
