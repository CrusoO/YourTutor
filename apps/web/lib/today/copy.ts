/**
 * Words for the "days this week" view on the Today page. They live here, not in lib/messages.ts, so the shared message
 * table loaded by the homepage does not grow. English only: other languages show these English lines until reviewed.
 * No counter, no loss wording, no comparison (a copy-lint test checks the words).
 */
export const weekEn = {
  switchLabel: "Show my week",
  switchHint: "Seven dots for the days you practise. It stays on this device.",
  title: "This week",
  dayNames: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
  dayShort: ["M", "T", "W", "T", "F", "S", "S"],
  practised: "practised",
  rest: "rest day",
  notYet: "not yet",
  noPractice: "no practice",
  restLine: "{day} was a rest day.",
  rhythm: "{n} days this week. Nice rhythm.",
  listLabel: "Days this week",
} as const;

export type WeekCopy = typeof weekEn;
