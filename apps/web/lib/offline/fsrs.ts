/**
 * FSRS review scheduling for the offline player (ts-fsrs, fuzz off), with the same rating rules as
 * apps/api/app/learner/scheduler_fsrs.py. ts-fsrs rounds stability to 8 decimals where the Python
 * library does not, so offline cards are close to, not identical with, the server's; the server
 * recomputes them on sync and its cards replace the local ones.
 */

import { type Card, createEmptyCard, fsrs, generatorParameters, Rating } from "ts-fsrs";

export type { Card };

const scheduler = fsrs(generatorParameters({ enable_fuzz: false }));

export function rateWarmup(correct: boolean, hinted: boolean, latencyMs: number | null): Rating {
  if (!correct) return Rating.Again;
  if (hinted) return Rating.Hard;
  if (latencyMs !== null && latencyMs > 60_000) return Rating.Good;
  return Rating.Easy;
}

export function rateSession(unhintedRate: number): Rating {
  if (unhintedRate <= 0.0) return Rating.Again;
  if (unhintedRate <= 0.5) return Rating.Hard;
  if (unhintedRate < 0.85) return Rating.Good;
  return Rating.Easy;
}

export function reviewCard(card: Card | undefined, rating: Rating, atMs: number): Card {
  const now = new Date(atMs);
  const base: Card = card === undefined ? createEmptyCard(now) : card;
  // `next` accepts only the four review ratings
  return scheduler.next(base, now, rating as Exclude<Rating, Rating.Manual>).card;
}
