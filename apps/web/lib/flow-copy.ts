/**
 * Strings for the Done screen and the quick-start loading states. They live here, not in lib/messages.ts, so the shared
 * message table (loaded by the homepage) does not grow. English only for now; other languages show these lines until
 * they are translated.
 */
export const flowEn = {
  doneFinish: "Done for today",
  doneOneMore: "One more",
  doneMoved: "You moved forward on {title}.",
  doneMovedMore: "You moved forward on {title} and {n} more.",
  donePractisedLine: "You practised {title}.",
  donePractisedMore: "You practised {title} and {n} more.",
  doneMinutesLeft: "{n} active minutes left today.",
  // No promise of a count: the Done summary does not say whether a next-day check will exist.
  doneTomorrow: "Come back tomorrow for a quick check.",
  doneSeeCovered: "See what you covered",
  startLoading: "Getting the classes ready.",
  startRetry: "Try again",
} as const;

export type FlowCopy = typeof flowEn;

export function fill(text: string, values: Record<string, string | number>): string {
  return text.replace(/\{(\w+)\}/g, (m, k: string) => (k in values ? String(values[k]) : m));
}
