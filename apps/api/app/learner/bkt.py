from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BktParams:
    p_init: float
    p_learn: float
    p_slip: float
    p_guess: float


def clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


def posterior(p_known: float, *, correct: bool, params: BktParams) -> float:
    p_l = clamp01(p_known)
    if correct:
        numer = p_l * (1.0 - params.p_slip)
        denom = numer + (1.0 - p_l) * params.p_guess
    else:
        numer = p_l * params.p_slip
        denom = numer + (1.0 - p_l) * (1.0 - params.p_guess)
    if denom <= 0.0:
        posterior_l = p_l
    else:
        posterior_l = numer / denom
    learned = posterior_l + (1.0 - posterior_l) * params.p_learn
    return clamp01(learned)


class BktModel:
    """MasteryModel: one BKT posterior + learn step."""

    def update(self, p_known: float, *, correct: bool, params: BktParams) -> float:
        return posterior(p_known, correct=correct, params=params)
