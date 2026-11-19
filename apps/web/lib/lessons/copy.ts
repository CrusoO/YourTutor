/**
 * Words for the flow-based lesson screens. They live here, not in lib/messages.ts, so the shared message table
 * (loaded by the homepage) does not grow: only the lazy lesson player imports this file. English only for now;
 * other languages show these English lines until they are translated.
 */
export const lessonFlowEn = {
  hopRight: "Hop right",
  hopLeft: "Hop left",
  hopProgress: "Hop {n} of {total}",
  undo: "Undo",
  hint: "Hint",
  anotherHint: "Another hint",
  another: "Another one",
  exampleOf: "Example {n} of {total}",
  signLink: "What do + and − mean?",
  signHide: "Hide this",
  signTitle: "What + and − mean",
  signPlus: "Plus (+) moves right.",
  signMinus: "Minus (−) moves left.",
  signAddNeg: "Adding a negative number moves left too.",
  signNoteMinus: "A minus sign moves you left.",
  signNoteNegative: "Numbers below zero sit to the left of 0.",
  typeInstead: "Type the answer instead",
  useLine: "Use the number line",
  notQuite: "Not quite. Try again.",
  replay: "Replay",
  playAgain: "Play again",
  tryYourself: "Move it yourself",
  skipHops: "Jump to the answer",
  nextHop: "Next hop",
  readAloud: "Read aloud",
  listen: "Listen",
  hintDragCount: "Move the dot {n} steps {dir}. Use the +1 or −1 step buttons if dragging is hard.",
  placeDotCheck: "Place the dot, then press Check.",
  typeFirst: "Type your answer first, then press Check.",
} as const;

export type LessonFlowCopy = typeof lessonFlowEn;

/** Fill {name} slots. */
export function fill(text: string, vars: Record<string, string | number>): string {
  return text.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? ""));
}
