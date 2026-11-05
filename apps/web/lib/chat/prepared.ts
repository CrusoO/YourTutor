/**
 * Prepared lessons: a short shelf of lessons and videos built before the student asks, for questions many students ask.
 * Matching is done here, in the browser, on the typed text: the text is never sent anywhere for this.
 * The feature is off unless NEXT_PUBLIC_PREPARED_LESSONS is exactly "true".
 */
import type { AiBlock } from "@/lib/lessons/ai-lesson";
import { PREPARED_TRAIN_BLOCKS } from "@/lib/lessons/prepared-train";

export type PreparedLesson = {
  id: string;
  title: string;
  /** Every one of these must be in the normalised text. */
  all: string[];
  /** The longest normalised text that may match: a long text only contains the words, it is not this question. */
  maxChars: number;
  video: string;
  preparedOn: string;
  blocks: AiBlock[];
};

export const PREPARED: PreparedLesson[] = [
  {
    id: "train-360-km",
    title: "The train, the hour, and the secret",
    all: ["train", "360 km", "uniform speed", "5 km/h", "1 hour"],
    maxChars: 500,
    video: "/prepared/train-360-km.mp4",
    preparedOn: "2026-11-05",
    blocks: PREPARED_TRAIN_BLOCKS,
  },
];

export function preparedEnabled(value: string | undefined = process.env.NEXT_PUBLIC_PREPARED_LESSONS): boolean {
  return value === "true";
}

/** Lower case, one kind of minus and apostrophe, single spaces. */
export function normalise(text: string): string {
  return text
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[−–—]/g, "-")
    .replace(/[‘’]/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** The prepared lesson for this typed question, or null. Pure; no network, storage or logging. */
export function findPrepared(text: string): PreparedLesson | null {
  const t = normalise(text);
  if (!t) return null;
  return PREPARED.find((p) => t.length <= p.maxChars && p.all.every((needle) => t.includes(needle))) ?? null;
}
