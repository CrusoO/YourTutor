/** Bayesian knowledge tracing, a line-for-line mirror of apps/api/app/learner/bkt.py. */

export type BktParams = { p_init: number; p_learn: number; p_slip: number; p_guess: number };

export const DEFAULT_BKT: BktParams = { p_init: 0.2, p_learn: 0.15, p_slip: 0.1, p_guess: 0.2 };

export function clamp01(value: number): number {
  return Math.min(1.0, Math.max(0.0, value));
}

export function posterior(pKnown: number, correct: boolean, params: BktParams): number {
  const pl = clamp01(pKnown);
  let numer: number;
  let denom: number;
  if (correct) {
    numer = pl * (1.0 - params.p_slip);
    denom = numer + (1.0 - pl) * params.p_guess;
  } else {
    numer = pl * params.p_slip;
    denom = numer + (1.0 - pl) * (1.0 - params.p_guess);
  }
  const posteriorL = denom <= 0.0 ? pl : numer / denom;
  const learned = posteriorL + (1.0 - posteriorL) * params.p_learn;
  return clamp01(learned);
}
