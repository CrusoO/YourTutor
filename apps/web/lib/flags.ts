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
