from __future__ import annotations

import random

import pytest

from app.learner.bktf import AttemptKind, BktFParams
from app.learner.bktf_sim import SimAttempt, baseline_log_loss, score, simulate_learner

TRUE = BktFParams(p_init=0.25, p_learn=0.12, p_slip=0.08, p_guess=0.2, tau_days=4.0)


def population(params: BktFParams, *, seed: int, learners: int = 600) -> list[list[SimAttempt]]:
    """Spaced practice: gaps from zero to two weeks, with a few rapid guesses mixed in."""
    rng = random.Random(seed)
    out = []
    for _ in range(learners):
        gaps = [0.0] + [rng.choice([0.0, 0.5, 2.0, 7.0, 14.0]) for _ in range(11)]
        kinds = [AttemptKind.RAPID_GUESS if rng.random() < 0.1 else AttemptKind.VALID for _ in gaps]
        out.append(simulate_learner(params, gaps, kinds, rng))
    return out


def test_simulation_is_reproducible() -> None:
    assert population(TRUE, seed=7, learners=20) == population(TRUE, seed=7, learners=20)
    assert population(TRUE, seed=7, learners=20) != population(TRUE, seed=8, learners=20)


def test_simulator_rejects_mismatched_inputs() -> None:
    with pytest.raises(ValueError):
        simulate_learner(TRUE, [0.0, 1.0], [AttemptKind.VALID], random.Random(0))


def test_filter_is_calibrated_on_data_from_its_own_process() -> None:
    result = score(TRUE, population(TRUE, seed=1))
    assert result.n == 600 * 12
    assert result.mean_predicted == pytest.approx(result.mean_observed, abs=0.02)


def test_filter_beats_the_constant_baseline() -> None:
    data = population(TRUE, seed=2)
    assert score(TRUE, data).log_loss < baseline_log_loss(data) - 0.02


def test_modelling_forgetting_beats_ignoring_it_when_gaps_are_long() -> None:
    data = population(TRUE, seed=3)
    no_forgetting = BktFParams(0.25, 0.12, 0.08, 0.2, tau_days=1e9)
    assert score(TRUE, data).log_loss < score(no_forgetting, data).log_loss


def test_hint_weight_does_not_matter_when_no_attempt_is_hinted() -> None:
    data = population(TRUE, seed=4, learners=100)
    other = BktFParams(0.25, 0.12, 0.08, 0.2, 4.0, hint_weight=0.1)
    assert score(TRUE, data) == score(other, data)
