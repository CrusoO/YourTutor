/**
 * Typed commands ("practice", "switch to Hindi"), matched in the browser.
 *
 * The phrase table comes from `GET /actions/rules` (no user text is sent, like the topic finder's rules);
 * what a student types is matched here and never leaves the device for this. The decision must agree with
 * the Python reference in apps/api/tests/actions, case for case: packages/shared/fixtures/actions/cases.json.
 */

export type Tier = "guest" | "student";

export type ActionRules = {
  language: string;
  max_chars: number;
  max_words: number;
  fillers: string[];
  denied_default: string;
  actions: Record<string, { client: string; risk: "safe" | "confirm"; tiers: string[]; narration: string; confirm?: string; denied?: string }>;
  phrases: Record<string, { name: string; args: Record<string, string> }>;
};

/** What a typed command means, chosen only from the server's table. */
export type ActionDirective =
  | { kind: "none" }
  | { kind: "denied"; name: string; narration: string }
  | { kind: "action"; name: string; client: string; args: Record<string, string>; risk: "safe" | "confirm"; narration: string; confirm?: string };

/** A step the chat knows how to run. The list is closed: a directive naming anything else does nothing. */
export type Step =
  | { verb: "start_practice" }
  | { verb: "open_screen"; path: string }
  | { verb: "set_language"; code: string }
  | { verb: "new_chat" };

/** What to show and what to run for a directive. */
export type Plan =
  | { kind: "ignore" }
  | { kind: "say"; text: string }
  | { kind: "run"; text: string; step: Step | null }
  | { kind: "confirm"; text: string; ask: string; step: Step };

/** The screens an action may open. A path from the server is never used; only the key is. */
export const SCREENS: Readonly<Record<string, string>> = { today: "/today", subjects: "/subjects" };

const own = (object: object, key: string) => Object.prototype.hasOwnProperty.call(object, key);

/** Lower-case, drop punctuation and symbols (by Unicode category, so Indic combining marks survive) and filler words. */
export function normalise(text: string, fillers: readonly string[]): string {
  const skip = new Set(fillers);
  const folded = text.normalize("NFKC").toLowerCase().replace(/['’]/g, "");
  return folded
    .replace(/[\p{P}\p{S}]/gu, " ")
    .split(/\s+/)
    .filter((word) => word && !skip.has(word))
    .join(" ");
}

/** The decision for a typed message: an action, a reason it is not allowed here, or nothing (it is a question). */
export function decide(text: string, rules: ActionRules, tier: Tier): ActionDirective {
  const cleaned = text.split(/\s+/).filter(Boolean).join(" ");
  if (!cleaned || cleaned.length > rules.max_chars) return { kind: "none" };
  const key = normalise(cleaned, rules.fillers);
  if (!key || key.split(" ").length > rules.max_words) return { kind: "none" };
  if (!own(rules.phrases, key)) return { kind: "none" };
  const hit = rules.phrases[key]!;
  if (!own(rules.actions, hit.name)) return { kind: "none" };
  const row = rules.actions[hit.name]!;
  if (!row.tiers.includes(tier)) return { kind: "denied", name: hit.name, narration: row.denied ?? rules.denied_default };
  return {
    kind: "action",
    name: hit.name,
    client: row.client,
    args: hit.args,
    risk: row.risk,
    narration: row.narration,
    ...(row.confirm ? { confirm: row.confirm } : {}),
  };
}

/** The step for a client verb and its arguments, or null when the verb or a value is not one we run. */
export function stepFor(client: string, args: Record<string, string>, isLiveLocale: (code: string) => boolean): Step | null {
  if (client === "start_practice") return { verb: "start_practice" };
  if (client === "new_chat") return { verb: "new_chat" };
  if (client === "open_screen") {
    const path = args.screen && own(SCREENS, args.screen) ? SCREENS[args.screen] : undefined;
    return path ? { verb: "open_screen", path } : null;
  }
  if (client === "set_language") {
    return args.language && isLiveLocale(args.language) ? { verb: "set_language", code: args.language } : null;
  }
  return null; // "none" (narration only) and anything this version does not know
}

/** Decide what a directive does here. The table is a closed list, but this checks again before anything runs. */
export function planAction(directive: ActionDirective, isLiveLocale: (code: string) => boolean): Plan {
  if (directive.kind === "denied") return directive.narration ? { kind: "say", text: directive.narration } : { kind: "ignore" };
  if (directive.kind !== "action" || !directive.narration) return { kind: "ignore" };
  const step = stepFor(directive.client, directive.args ?? {}, isLiveLocale);
  if (directive.client !== "none" && !step) return { kind: "ignore" }; // an unknown verb is a no-op, never a guess
  if (directive.risk === "confirm") {
    if (!step || !directive.confirm) return { kind: "ignore" }; // a confirm-level action must be able to ask
    return { kind: "confirm", text: directive.narration, ask: directive.confirm, step };
  }
  return { kind: "run", text: directive.narration, step };
}
