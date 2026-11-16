import type { MathCandidate } from "@/lib/doubt/types";

/** What the chat holds for a doubt card. Memory only: never stored, never sent, gone on refresh. */
export type DoubtPayload = {
  /** What the student typed (after the device's own PII screen), kept only so Edit and the explain hand-off work. */
  text: string;
  outcome: "candidate" | "unsupported";
  candidate?: MathCandidate;
  /** The deterministic substitution check for a pushback message, shown on the card. */
  pushback?: string;
};
