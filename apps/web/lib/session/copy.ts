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
  checkedStamp: "Checked",
  checkedStampHint: "A rule worked this answer out and it agreed.",
  notCheckedStamp: "Not checked",
  stepsOpen: "Show your working",
  stepsClose: "Hide your working",
  stepsTitle: "Your working",
  stepsEquation: "Equation",
  stepsPrivacy:
    "When you tap Check step, this equation and your lines are sent to be checked by a rule, not by a model. Nothing is saved.",
  stepLineLabel: "Step {n}",
  stepCheck: "Check step",
  stepChecking: "Checking",
  stepBackspace: "Delete",
  stepKeypad: "Maths keys",
  stepNoRoots: "no real roots",
  stepOk: "Correct step",
  stepWrong: "Look at this step again",
  stepUnreadable: "I could not read this. Write it in full, like 3 + 2.",
  stepSkipped: "Not checked yet",
  verdictCorrect: "Your last line is the right answer. A rule checked it.",
  verdictWrong: "Your last line is not the answer yet. Look at the step marked above.",
  verdictNotFinal: "Keep going until the last line says what x is.",
  verdictUnchecked: "This question cannot be checked step by step.",
  stepRefusalDisabled: "Checking steps is not switched on.",
  stepRefusalConsent: "Checking steps needs your guardian to allow maths checking. Ask them to turn it on.",
  stepRefusalRate: "That is a lot of checks. Try again a little later.",
  stepRefusalInvalid: "That cannot be checked here. Use numbers, x, + − ( ) and = only.",
  stepRefusalFailed: "Could not check just now. Try again.",
  notCheckedStampHint: "No rule could check this answer. Compare it with your book or teacher.",
};

export type SessionCopy = Messages & typeof sessionEn;

/** The shared messages for a language plus the session strings (English until translated). */
export function withSession(copy: Messages): SessionCopy {
  return { ...sessionEn, ...copy };
}
