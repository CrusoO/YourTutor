import { prepare, type FinderRules } from "@/lib/chat/finder";
import { detectMath } from "@/lib/doubt/detect";
import { guardCandidate, guardText, routesToPracticeHelp } from "@/lib/doubt/guard";
import { answersFor, detectPushback, finalReply, resolvePushback } from "@/lib/doubt/pushback";
import { solve } from "@/lib/doubt/solve";
import type { DoubtPayload } from "./types";

/**
 * The chat's on-device maths pipeline. Pure: no network, storage or logging. The text has already passed the
 * finder's own screen (distress, blocked, PII) before it reaches here.
 *   guardText -> detectMath -> guardCandidate -> routesToPracticeHelp -> (solve, on the card, after the student
 *   confirms the reading).
 * `null` means "not maths, or the practice screen owns it": the composer then behaves exactly as it did before.
 */
export function readDoubt(text: string, stems: readonly string[] = []): DoubtPayload | null {
  const g = guardText(text);
  if (!g.ok) return { text, outcome: "unsupported" };
  const found = detectMath(text);
  if (found.kind === "none") return null;
  if (found.kind === "unsupported") return { text, outcome: "unsupported" };
  if (!guardCandidate(found.candidate).ok) return { text, outcome: "unsupported" };
  if (routesToPracticeHelp(found.candidate, stems)) return null;
  return { text, outcome: "candidate", candidate: found.candidate };
}

/** "my book says 3": the claimed value is put back into the equation. The deterministic check outranks any reply. */
export function readPushback(payload: DoubtPayload, text: string): string | null {
  const c = payload.candidate;
  if (!c) return null;
  const pb = detectPushback(text);
  if (!pb.pushback) return null;
  const sol = solve(c);
  return finalReply(resolvePushback(c, sol, pb.claim), null, answersFor(c, sol)).text;
}

/**
 * The chat's one entry point. `rules` is the finder's own screen (distress, blocked, PII), so such text is never read
 * as maths. `open` is the card already in the thread, if any: pushback on it updates that card in place (`same`).
 * `null` means "not for the maths card": the composer carries on exactly as before.
 */
export function handle(text: string, rules: FinderRules, open?: DoubtPayload): { doubt: DoubtPayload; same: boolean } | null {
  if (!/[0-9=+\-*/^√×÷]/.test(text)) return null;
  const screened = prepare(text, rules);
  if (screened.kind !== "ok") return null;
  const said = open ? readPushback(open, screened.text) : null;
  if (open && said) return { doubt: { ...open, pushback: said }, same: true };
  const read = readDoubt(screened.text);
  return read ? { doubt: read, same: false } : null;
}
