/**
 * English default copy for the learn components, so a screen (and the /dev/components preview) can pass one object.
 * Components themselves hold no copy: every string arrives through props. The follow-up that wires these into
 * screens moves these keys into lib/messages.ts, where hi and ne wording is reviewed by the owner before approval.
 */
export const LEARN_COPY_EN = {
  correct: "Correct",
  lookAgain: "Look again",
  correctTitle: "Yes, that works",
  lookAgainTitle: "Not quite, let's look at this",
  confidenceLegend: "How sure are you?",
  confidence: { guessing: "Guessing", thinkSo: "Think so", sure: "Sure" },
  idk: "I don't know, give me a hint",
  hint: { first: "Show a hint", next: "Show the next hint", steps: "Show full steps", stepsLocked: "Open a hint first" },
  loading: "Loading",
  tabs: { home: "Home", practice: "Practice", progress: "Progress", lessons: "Lessons" },
  navLabel: "Main",
  resume: "Continue",
} as const;
