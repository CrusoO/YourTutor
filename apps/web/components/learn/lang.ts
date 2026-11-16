/** Languages whose scripts stack marks above and below the line (Devanagari and kin): they need 1.7 or more. */
const TALL_SCRIPTS = new Set(["hi", "ne", "mr", "bn", "as"]);

/** Line height for running text in `lang`: 1.7 for Devanagari-family scripts, 1.5 otherwise (UI standard). */
export function lineHeightFor(lang?: string | null): number {
  const base = (lang ?? "").toLowerCase().split("-")[0];
  return TALL_SCRIPTS.has(base) ? 1.7 : 1.5;
}

/** The props every learn component puts on its root so child text inherits the right language and line height. */
export function langProps(lang?: string): { lang?: string; style: { lineHeight: number } } {
  return { lang, style: { lineHeight: lineHeightFor(lang) } };
}
