/** Hint leak check, a mirror of apps/api/app/content/leak.py. */

import { expressionsEquivalent, normalize } from "./math";

const NUMERIC = /^-?\d+(?:\.\d+)?$/;

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function containsToken(hay: string, needle: string): boolean {
  if (!needle) return false;
  if (NUMERIC.test(needle)) {
    return new RegExp(`(?<![\\d.])${escapeRegExp(needle)}(?![\\d.])`).test(hay);
  }
  return new RegExp(`(?<![A-Za-z])${escapeRegExp(needle)}(?![A-Za-z])`).test(hay);
}

function findNumbers(text: string): string[] {
  return normalize(text).match(/-?\d+(?:\.\d+)?/g) ?? [];
}

/** True if a level 1 or 2 hint contains the answer or an equivalent value. */
export function hintLeaksAnswer(hint: string, forbidden: string): boolean {
  const hay = normalize(hint);
  const needle = normalize(forbidden);
  if (containsToken(hay, needle)) return true;
  if (expressionsEquivalent(hint, forbidden)) return true;
  let answerNumbers: Set<string>;
  try {
    answerNumbers = new Set(findNumbers(forbidden));
  } catch {
    answerNumbers = new Set();
  }
  if (answerNumbers.size === 0) return false;
  const hintNumbers = new Set(findNumbers(hint));
  for (const num of answerNumbers) {
    if (hintNumbers.has(num) && expressionsEquivalent(num, forbidden)) return true;
  }
  return false;
}

/** True when a retry hint (level 1 or 2) leaks the answer. Level 3 is not checked. */
export function leakCheck(hintText: string, answer: string, level: number): boolean {
  if (level >= 3) return false;
  return hintLeaksAnswer(hintText, answer);
}
