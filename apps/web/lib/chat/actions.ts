import type { ActionDirective } from "@/lib/api";

/** A step the chat knows how to run. The list is closed: a directive naming anything else does nothing. */
export type Step =
  | { verb: "start_practice" }
  | { verb: "open_screen"; path: string }
  | { verb: "set_language"; code: string }
  | { verb: "new_chat" };

/** What to show and what to run for a directive from the server. */
export type Plan =
  | { kind: "ignore" }
  | { kind: "say"; text: string }
  | { kind: "run"; text: string; step: Step | null }
  | { kind: "confirm"; text: string; ask: string; step: Step };

/** The screens an action may open. A path from the server is never used; only the key is. */
export const SCREENS: Readonly<Record<string, string>> = { today: "/today", subjects: "/subjects" };

/** The step for a client verb and its arguments, or null when the verb or a value is not one we run. */
export function stepFor(client: string, args: Record<string, string>, isLiveLocale: (code: string) => boolean): Step | null {
  if (client === "start_practice") return { verb: "start_practice" };
  if (client === "new_chat") return { verb: "new_chat" };
  if (client === "open_screen") {
    const path = args.screen ? SCREENS[args.screen] : undefined;
    return path ? { verb: "open_screen", path } : null;
  }
  if (client === "set_language") {
    return args.language && isLiveLocale(args.language) ? { verb: "set_language", code: args.language } : null;
  }
  return null; // "none" (narration only) and anything this version does not know
}

/** Decide what a directive means here. The server already chose from a closed list; this checks again before anything runs. */
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
