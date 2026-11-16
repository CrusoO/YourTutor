/**
 * The only place the trust-chip wording lives. "Checked by code" is a claim that a factory-stamped, code-verified
 * item backs the content; no other string may say it. Translations are added here only after the owner reviews them.
 */
export type TrustVariant = "checked-by-code" | "hints-from-verified-steps" | "not-verified";

export const TRUST_LABELS: Readonly<Record<TrustVariant, string>> = {
  "checked-by-code": "Checked by code",
  "hints-from-verified-steps": "Hints from verified steps",
  "not-verified": "Not verified yet",
};
