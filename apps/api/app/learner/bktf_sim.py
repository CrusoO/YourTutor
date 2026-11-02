"""Simulated learners for BKT-F.

The simulator draws learners from the *same* process the filter assumes, so a correct filter must
come out calibrated on its data. That checks internal consistency: the maths, the decay and the
update order agree with each other. It does not show that real learners behave like the model; only
a pilot can do that.

Generative process, per learner:

- start knowing the skill with probability `p_init`;
- before each attempt, with probability 1 - exp(-gap / tau) the state is forgotten and redrawn as
  Bernoulli(floor), which gives exactly P' = floor + (P - floor) * exp(-gap / tau) for the filter;
- a rapid guess is correct with probability `p_guess` whatever the state, and teaches nothing;
- any other attempt is correct with probability 1 - slip if known, else guess;
- an unknown skill is learned after a non-guess attempt with probability `p_learn`.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from app.learner.bktf import AttemptKind, BktFParams, decay, predict_correct, update


@dataclass(frozen=True)
class SimAttempt:
    gap_days: float
    kind: AttemptKind
    correct: bool


def simulate_learner(
    params: BktFParams,
    gaps_days: Sequence[float],
    kinds: Sequence[AttemptKind],
    rng: random.Random,
) -> list[SimAttempt]:
    if len(gaps_days) != len(kinds):
        raise ValueError("gaps_days and kinds must be the same length")
    known = rng.random() < params.p_init
    attempts: list[SimAttempt] = []
    for gap, kind in zip(gaps_days, kinds, strict=True):
        if rng.random() < 1.0 - math.exp(-max(0.0, gap) / params.tau_days):
            known = rng.random() < params.floor
        if kind is AttemptKind.RAPID_GUESS:
            correct = rng.random() < params.p_guess
        elif known:
            correct = rng.random() >= params.p_slip
        else:
            correct = rng.random() < params.p_guess
        if kind is not AttemptKind.RAPID_GUESS and not known:
            known = rng.random() < params.p_learn
        attempts.append(SimAttempt(gap_days=gap, kind=kind, correct=correct))
    return attempts


@dataclass(frozen=True)
class Score:
    n: int
    log_loss: float
    brier: float
    mean_predicted: float
    mean_observed: float


def _clip(p: float) -> float:
    return min(1.0 - 1e-9, max(1e-9, p))


def score(model: BktFParams, learners: Sequence[Sequence[SimAttempt]]) -> Score:
    """Replay the filter over every learner and score its next-answer predictions."""
    losses = briers = predicted = observed = 0.0
    n = 0
    for attempts in learners:
        p = model.p_init
        for attempt in attempts:
            # Predict from the decayed estimate, then update with what really happened.
            decayed = decay(p, attempt.gap_days, model)
            q = _clip(predict_correct(decayed, model, attempt.kind))
            y = 1.0 if attempt.correct else 0.0
            losses += -(y * math.log(q) + (1.0 - y) * math.log(1.0 - q))
            briers += (q - y) ** 2
            predicted += q
            observed += y
            n += 1
            p = update(
                p,
                correct=attempt.correct,
                kind=attempt.kind,
                gap_days=attempt.gap_days,
                params=model,
            )
    if n == 0:
        raise ValueError("no attempts to score")
    return Score(n, losses / n, briers / n, predicted / n, observed / n)


def baseline_log_loss(learners: Sequence[Sequence[SimAttempt]]) -> float:
    """Log-loss of always predicting the overall correct rate: the bar a useful model must clear."""
    ys = [1.0 if a.correct else 0.0 for attempts in learners for a in attempts]
    rate = _clip(sum(ys) / len(ys))
    return -sum(y * math.log(rate) + (1.0 - y) * math.log(1.0 - rate) for y in ys) / len(ys)
