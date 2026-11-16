import { detectMath } from "@/lib/doubt/detect";
import { solve } from "@/lib/doubt/solve";
import type { MathCandidate, Solution } from "@/lib/doubt/types";

/** Small seeded generator (mulberry32) so every random test is repeatable. */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export function int(r: () => number, lo: number, hi: number): number {
  return lo + Math.floor(r() * (hi - lo + 1));
}

export function cand(text: string): MathCandidate {
  const d = detectMath(text);
  if (d.kind !== "candidate") throw new Error(`not a candidate: ${text} -> ${JSON.stringify(d)}`);
  return d.candidate;
}
export function solved(text: string): { c: MathCandidate; s: Solution } {
  const c = cand(text);
  return { c, s: solve(c) };
}
/** vitest runs from apps/web. */
export const FIXTURE_DIR = `${process.cwd().replace(/\\/g, "/")}/../../packages/shared/fixtures/doubt/`;
