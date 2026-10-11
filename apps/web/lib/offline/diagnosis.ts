/**
 * Diagnosis engine, a mirror of apps/api/app/orchestrator/diagnosis.py (ARCHITECTURE section 10).
 * Why was the answer wrong? First match wins: misconception, slip, prerequisite gap, incomplete
 * procedure, disengagement, generic. A correct answer is class `none`. The shared fixture
 * packages/shared/fixtures/diagnosis/classify.json runs against both.
 */

import { expressionsEquivalent, numericValue } from "./math";
import { level } from "./ladder";
import { type CatalogItem, type LearnerState, primarySkill, type SessionState } from "./types";

export const SLIP_MIN_LEVEL = 4;
export const FAST_STREAK_LIMIT = 3;
export const HELP_WITHOUT_ATTEMPT_LIMIT = 3;
const DEFAULT_OFF_BY = 1.0;

export type Diagnosis = { class: string; detail: string | null };

const VAR_PREFIX = /^\s*[a-zA-Z]\s*=\s*(?!=)/;
const stripPrefix = (text: string) => text.trim().replace(VAR_PREFIX, "");
const squash = (text: string) => text.replace(/\s+/g, "").toLowerCase();

function value(text: string): number | null {
  const stripped = stripPrefix(text);
  if (!stripped) return null;
  return numericValue(stripped);
}

function sameValue(left: string, right: string): boolean {
  const a = stripPrefix(left);
  const b = stripPrefix(right);
  if (!a || !b) return false;
  if (squash(a) === squash(b)) return true;
  return expressionsEquivalent(a, b);
}

function matchesAny(response: string, values: unknown[]): string | null {
  for (const candidate of values) {
    if (sameValue(response, String(candidate))) return String(candidate);
  }
  return null;
}

function misconception(item: CatalogItem, response: string): string | null {
  const text = response.trim();
  for (const [mid, answers] of item.misconception_rules) {
    if (answers.includes(text) || matchesAny(text, answers) !== null) return mid;
  }
  return null;
}

function slip(item: CatalogItem, response: string): string | null {
  const got = value(response);
  const want = value(item.answer_sympy);
  for (const pattern of item.slip_patterns) {
    const kind = String(pattern.kind);
    if (kind === "values" && matchesAny(response, (pattern.values as unknown[]) ?? []) !== null) {
      return kind;
    }
    if (got === null || want === null) continue;
    if (kind === "sign_flip" && want !== 0 && Math.abs(got + want) < 1e-9) return kind;
    if (kind === "off_by") {
      const limit = Number(pattern.max_distance ?? DEFAULT_OFF_BY);
      const gap = Math.abs(got - want);
      if (gap > 0 && gap <= limit + 1e-9) return kind;
    }
  }
  return null;
}

function prerequisite(
  item: CatalogItem,
  response: string,
  matched: string | null,
  session: SessionState,
): string | null {
  if (matched !== null) {
    const remedial = session.misconception_remedial[matched];
    if (remedial && (session.prerequisites[primarySkill(item)] ?? []).includes(remedial)) {
      return remedial;
    }
  }
  for (const signature of item.prereq_signatures) {
    if (matchesAny(response, (signature.values as unknown[]) ?? []) !== null) {
      return String(signature.skill_id);
    }
  }
  return null;
}

export function classify(
  item: CatalogItem,
  response: string,
  verifierResult: boolean,
  learner: LearnerState,
  session: SessionState,
): Diagnosis {
  if (verifierResult) return { class: "none", detail: null };
  const text = response || "";
  const matched = text ? misconception(item, text) : null;
  if (matched !== null) {
    const remedial = prerequisite(item, text, matched, session);
    if (remedial !== null) return { class: "prerequisite_gap", detail: remedial };
    return { class: "misconception", detail: matched };
  }
  const ladder = learner.ladders.get(primarySkill(item));
  const firstAttempt = session.last_wrong_item_id !== item.id;
  if (text && ladder !== undefined && level(ladder) >= SLIP_MIN_LEVEL && firstAttempt) {
    const found = slip(item, text);
    if (found !== null) return { class: "slip", detail: found };
  }
  if (text) {
    const remedial = prerequisite(item, text, null, session);
    if (remedial !== null) return { class: "prerequisite_gap", detail: remedial };
    const step = matchesAny(text, item.intermediate_values);
    if (step !== null) return { class: "incomplete_procedure", detail: step };
  }
  if (session.fast_streak >= FAST_STREAK_LIMIT) {
    return { class: "disengagement", detail: "fast_answers" };
  }
  if (session.help_without_attempt >= HELP_WITHOUT_ATTEMPT_LIMIT) {
    return { class: "disengagement", detail: "help_without_attempt" };
  }
  return { class: "generic", detail: null };
}
