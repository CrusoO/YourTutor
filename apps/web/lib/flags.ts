/** Feature flags read from the build environment. Off unless the variable is exactly "true". */

/** The microphone button. Off until voice input exists; the button used to do nothing. */
export function voiceEnabled(): boolean {
  return process.env.NEXT_PUBLIC_VOICE_ENABLED === "true";
}
