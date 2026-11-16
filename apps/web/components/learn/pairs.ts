/**
 * Every token pair the learn components use, for tests/learn/contrast.test.ts. Text 4.5:1, borders and focus rings 3:1.
 * Add a pair here whenever a component starts using a new fg/bg combination.
 */
export type LearnPair = { fg: string; bg: string; min: number; label: string };

export const LEARN_PAIRS: LearnPair[] = [
  // text on surfaces
  { fg: "--c-text", bg: "--c-surface", min: 4.5, label: "ink on card (question, option, ink text)" },
  { fg: "--c-text", bg: "--c-surface-2", min: 4.5, label: "ink on raised surface (equation area, hover)" },
  { fg: "--c-muted", bg: "--c-surface", min: 4.5, label: "muted on card (eyebrow, progress text, tab label)" },
  { fg: "--c-muted", bg: "--c-surface-2", min: 4.5, label: "muted on raised surface" },
  { fg: "--c-text", bg: "--c-accent-soft", min: 4.5, label: "ink on selected option / hint card" },
  { fg: "--c-text", bg: "--c-success-soft", min: 4.5, label: "ink on correct option / feedback" },
  { fg: "--c-text", bg: "--c-warning-soft", min: 4.5, label: "ink on look-again option / feedback" },
  // coloured text
  { fg: "--c-accent-ink", bg: "--c-surface", min: 4.5, label: "accent text on card (I don't know, current tab)" },
  { fg: "--c-accent-ink", bg: "--c-accent-soft", min: 4.5, label: "accent text on tint (hint title, current tab pill)" },
  { fg: "--c-accent-fg", bg: "--c-accent", min: 4.5, label: "label on accent fill (confidence, primary, hint button)" },
  { fg: "--c-success", bg: "--c-success-soft", min: 4.5, label: "Correct label / checked chip on green tint" },
  { fg: "--c-warning", bg: "--c-warning-soft", min: 4.5, label: "Look again label on amber tint" },
  { fg: "--c-neutral", bg: "--c-neutral-soft", min: 4.5, label: "not-verified chip text" },
  { fg: "--c-accent-ink", bg: "--c-surface", min: 4.5, label: "empty-state icon on card" },
  // borders, focus rings, meaningful icons
  { fg: "--c-input-line", bg: "--c-surface", min: 3, label: "option / card border on card" },
  { fg: "--c-input-line", bg: "--c-bg", min: 3, label: "option / card border on page" },
  { fg: "--c-input-line", bg: "--c-surface-2", min: 3, label: "border on raised surface" },
  { fg: "--c-accent", bg: "--c-surface", min: 3, label: "selected border on card" },
  { fg: "--c-accent", bg: "--c-accent-soft", min: 3, label: "selected border on its tint" },
  { fg: "--c-success", bg: "--c-surface", min: 3, label: "correct border on page card" },
  { fg: "--c-success", bg: "--c-success-soft", min: 3, label: "correct border and icon on its tint" },
  { fg: "--c-warning", bg: "--c-warning-soft", min: 3, label: "look-again border and icon on its tint" },
  { fg: "--c-focus", bg: "--c-surface", min: 3, label: "focus ring on card" },
  { fg: "--c-focus", bg: "--c-bg", min: 3, label: "focus ring on page" },
  { fg: "--c-focus", bg: "--c-surface-2", min: 3, label: "focus ring on raised surface" },
  // The ring is drawn with a 2 px offset, so it sits on the page or card around a filled accent control, never on the fill.
];
