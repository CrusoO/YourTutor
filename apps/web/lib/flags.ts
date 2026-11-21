/** Feature flags read from the build environment. Off unless the variable is exactly "true". */

/** The microphone button. Off until voice input exists; the button used to do nothing. */
export function voiceEnabled(): boolean {
  return process.env.NEXT_PUBLIC_VOICE_ENABLED === "true";
}

/**
 * The on-device maths doubt card in the Ask Brownie composer (ADR 0005, Stage 0). Nothing leaves the device.
 * Off in production unless NEXT_PUBLIC_DOUBT_DEVICE is exactly "true"; on by default only in `next dev`; a preview
 * build turns it on by setting the variable. "false" always wins.
 */
export function doubtDeviceEnabled(): boolean {
  const v = process.env.NEXT_PUBLIC_DOUBT_DEVICE;
  if (v === "true") return true;
  if (v === "false") return false;
  return process.env.NODE_ENV === "development";
}

/**
 * The optional server check on the doubt card (ADR 0005, Stage 2): a confirmed, structured expression goes to
 * `POST /doubt/solve` after an explicit tap, only for a learner whose guardian granted `math_check`. Off unless the
 * variable is exactly "true" (and the API has SCOPE_MATH_CHECK_ENABLED on). Needs the device doubt card too.
 */
export function doubtServerEnabled(): boolean {
  return process.env.NEXT_PUBLIC_DOUBT_SERVER === "true";
}

/**
 * Quick start: the first visit asks only class and subject, then goes straight to one question. On unless
 * NEXT_PUBLIC_QUICK_START_ENABLED is exactly "false", which restores the full setup (class, state, board, medium, subject).
 */
export function quickStartEnabled(): boolean {
  return process.env.NEXT_PUBLIC_QUICK_START_ENABLED !== "false";
}

/**
 * "Show my week" on the Today page: seven dots, Monday to Sunday, kept on the device only. Off unless the variable is
 * exactly "true", and even then the student must switch it on themselves.
 */
export function weekDotsEnabled(): boolean {
  return process.env.NEXT_PUBLIC_WEEK_DOTS === "true";
}

/**
 * Practice loop, slice 1: a "Show your working" panel on quadratics practice questions, with a step-by-step check
 * (`POST /practice/check-steps`, needs STEP_CHECK_ENABLED and the math_check scope on the API). Off unless the variable
 * is exactly "true".
 */
export function stepEntryEnabled(): boolean {
  return process.env.NEXT_PUBLIC_STEP_ENTRY === "true";
}
