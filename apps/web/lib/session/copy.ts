import type { Messages } from "@/lib/messages";

/**
 * Strings for the practice-session refresh. They live here, not in lib/messages.ts, so the shared message table (loaded
 * by the homepage) does not grow: this file is only imported by the session route. English only for now; other
 * languages show these English lines until they are translated.
 */
export const sessionEn = {
  feedbackCorrectBody: "You got it. Keep going.",
  feedbackWrongBody: "A wrong answer is how we find the tricky part. Look at it again, or ask for a hint.",
  hintHeadingWrong: "Not quite. Here is a hint.",
  hintHeading: "Here is a hint.",
  answerLabel: "Answer",
  stepsLabel: "Steps",
  moreStepsLabel: "See the lesson's steps",
  practiceLabel: "Practice",
  questionNumber: "Question {n}",
  progressDone: "{n} done so far",
  signTitle: "What does the sign mean?",
  signRule: "A plus sign means go right. A minus sign means go left.",
  signAddNegative: "Adding a negative number moves you left, the same as taking away.",
  signSubtractNegative: "Taking away a negative moves you right.",
  signAdding: "Adding {x} means {move}",
  signSubtracting: "Subtracting {x} means {move}",
  signMovePlus: "move {n} {unit} right.",
  signMoveMinus: "move {n} {unit} left.",
  signMoveNone: "you do not move.",
  signUnitOne: "step",
  signUnitMany: "steps",
  signStepOne: "Start at {start}.",
  signLand: "You land on {result}.",
  signStart: "start",
  signLandLabel: "you land here",
  signShowButton: "Show me on a number line",
  signHintTitle: "Try it on a number line",
  signHintClose: "Hide the number line",
  signHintNote: "Count the steps along the line. Where do you stop?",
  signLineName: "Number line from {min} to {max}.",
  signLineStart: "Start at {start}.",
  signLineMove: "Move {n} {unit} {dir}.",
  signLineLand: "You land on {result}.",
  signDirRight: "right",
  signDirLeft: "left",
};

export type SessionCopy = Messages & typeof sessionEn;

/** The shared messages for a language plus the session strings (English until translated). */
export function withSession(copy: Messages): SessionCopy {
  return { ...sessionEn, ...copy };
}
