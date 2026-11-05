/**
 * Prepared lessons: a short shelf of lessons and videos built before the student asks, for questions many students ask.
 * Matching is done here, in the browser, on the typed text: the text is never sent anywhere for this.
 * The feature is off unless NEXT_PUBLIC_PREPARED_LESSONS is exactly "true".
 */
import type { AiBlock } from "@/lib/lessons/ai-lesson";
import type { LessonArtKey } from "@/components/chat/lesson/LessonArt";
import { PREPARED_TRAIN_ART, PREPARED_TRAIN_BLOCKS, PREPARED_TRAIN_SPEECH } from "@/lib/lessons/prepared-train";

export type PreparedLesson = {
  id: string;
  title: string;
  /** Every one of these must be in the normalised text. */
  all: string[];
  /** The longest normalised text that may match: a long text only contains the words, it is not this question. */
  maxChars: number;
  video: string;
  poster: string;
  preparedOn: string;
  blocks: AiBlock[];
  /** What Brownie says for each block, in order (the recordings were made from exactly these). */
  speech: string[];
  /** The small picture beside each block, in order. */
  art: readonly LessonArtKey[];
  /** Where in the video (seconds) to open when the learner gets block i wrong; a block not listed opens at the start. */
  videoAt: Readonly<Record<number, number>>;
  /** Where the recording for block i is. */
  audio: (i: number) => string;
};

export const PREPARED: PreparedLesson[] = [
  {
    id: "train-360-km",
    title: "The train, the hour, and the secret",
    all: ["train", "360 km", "uniform speed", "5 km/h", "1 hour"],
    maxChars: 500,
    video: "/prepared/train-360-km.mp4",
    poster: "/prepared/train-360-km-poster.jpg",
    preparedOn: "2026-11-05",
    blocks: PREPARED_TRAIN_BLOCKS,
    speech: PREPARED_TRAIN_SPEECH,
    art: PREPARED_TRAIN_ART,
    // block 1 (two trains, which is faster) -> the two-trains scene; blocks 5 and 6 (which answer, 9 h against 8 h) -> the check; block 7 (the bus) -> the equation
    videoAt: { 1: 8.8, 5: 56.8, 6: 56.8, 7: 33.8 },
    audio: (i) => `/prepared/audio/train-360-km/b${i}.m4a`,
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
