from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.learner.traits import (
    TraitPrior,
    TraitState,
    decay_factor,
    decayed,
    estimate,
    observe,
)

PRIOR = TraitPrior(mu0=0.0, sigma0_sq=1.0, sigma_obs_sq=1.0, half_life_days=10.0)
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


def days(n: float) -> datetime:
    return T0 + timedelta(days=n)


# --- numbers worked by hand ---------------------------------------------------------------------


def test_with_no_evidence_the_estimate_is_the_prior() -> None:
    got = estimate(TraitState(), PRIOR)
    assert (got.mean, got.variance, got.n) == (0.0, 1.0, 0.0)


def test_one_observation_pulls_the_mean_part_of_the_way() -> None:
    # precision = 1 + 1 = 2; mean = (0 + 3) / 2 = 1.5; variance = 0.5
    got = estimate(observe(TraitState(), PRIOR, 3.0, T0), PRIOR)
    assert got.mean == pytest.approx(1.5)
    assert got.variance == pytest.approx(0.5)


def test_a_session_never_overwrites_the_mean() -> None:
    got = estimate(observe(TraitState(), PRIOR, 100.0, T0), PRIOR)
    assert got.mean < 100.0
    assert got.mean == pytest.approx(50.0)


def test_half_life_halves_the_evidence() -> None:
    state = observe(TraitState(), PRIOR, 2.0, T0)
    later = decayed(state, PRIOR, days(10))
    assert later.n == pytest.approx(0.5)
    assert later.sum_x == pytest.approx(1.0)


def test_decay_factor_matches_the_definition() -> None:
    gamma = 0.5 ** (1 / 10.0)
    assert decay_factor(10.0, 7.0) == pytest.approx(gamma**7.0)


def test_negative_gap_counts_as_zero_and_nan_is_rejected() -> None:
    assert decay_factor(10.0, -5.0) == 1.0
    with pytest.raises(ValueError):
        decay_factor(10.0, float("nan"))


def test_a_skewed_clock_does_not_age_the_state() -> None:
    state = observe(TraitState(), PRIOR, 2.0, days(5))
    assert decayed(state, PRIOR, days(1)).n == pytest.approx(state.n)


def test_after_a_long_break_the_estimate_returns_toward_the_prior() -> None:
    state = observe(TraitState(), PRIOR, 4.0, T0)
    fresh = estimate(state, PRIOR)
    stale = estimate(state, PRIOR, at=days(200))
    assert abs(stale.mean - PRIOR.mu0) < abs(fresh.mean - PRIOR.mu0)
    assert stale.variance > fresh.variance


def test_reading_without_a_time_does_not_decay() -> None:
    state = observe(TraitState(), PRIOR, 2.0, T0)
    assert estimate(state, PRIOR) == estimate(state, PRIOR, at=None)


# --- validation ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"sigma0_sq": 0.0},
        {"sigma_obs_sq": -1.0},
        {"half_life_days": 0.0},
        {"half_life_days": float("inf")},
        {"mu0": float("nan")},
    ],
)
def test_invalid_priors_are_rejected(overrides: dict[str, float]) -> None:
    base = {"mu0": 0.0, "sigma0_sq": 1.0, "sigma_obs_sq": 1.0, "half_life_days": 10.0}
    with pytest.raises(ValueError):
        TraitPrior(**{**base, **overrides})


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_non_finite_observations_are_rejected(bad: float) -> None:
    with pytest.raises(ValueError):
        observe(TraitState(), PRIOR, bad, T0)


# --- properties ---------------------------------------------------------------------------------

priors = st.builds(
    TraitPrior,
    mu0=st.floats(-5, 5),
    sigma0_sq=st.floats(0.01, 10),
    sigma_obs_sq=st.floats(0.01, 10),
    half_life_days=st.floats(0.5, 365),
)
xs = st.floats(-10, 10)
gaps = st.floats(0, 400)


@settings(max_examples=200, deadline=None)
@given(priors, st.lists(st.tuples(xs, gaps), max_size=25))
def test_evidence_only_ever_sharpens_the_belief_at_the_moment_it_arrives(
    prior: TraitPrior, observations: list[tuple[float, float]]
) -> None:
    state, at = TraitState(), T0
    for x, gap in observations:
        at = at + timedelta(days=gap)
        state = observe(state, prior, x, at)
        got = estimate(state, prior)
        assert got.variance <= prior.sigma0_sq + 1e-12
        assert got.n >= 1.0 - 1e-12


@settings(max_examples=200, deadline=None)
@given(priors, st.lists(xs, min_size=1, max_size=25))
def test_the_mean_stays_between_the_prior_and_the_data(
    prior: TraitPrior, observations: list[float]
) -> None:
    state = TraitState()
    for x in observations:
        state = observe(state, prior, x, T0)
    got = estimate(state, prior)
    low = min(prior.mu0, min(observations))
    high = max(prior.mu0, max(observations))
    assert low - 1e-9 <= got.mean <= high + 1e-9


@settings(max_examples=200, deadline=None)
@given(priors, st.lists(xs, min_size=2, max_size=12), st.randoms(use_true_random=False))
def test_order_does_not_matter_when_observations_arrive_together(
    prior: TraitPrior, observations: list[float], rng
) -> None:
    shuffled = observations[:]
    rng.shuffle(shuffled)

    def run(values: list[float]):
        state = TraitState()
        for x in values:
            state = observe(state, prior, x, T0)
        return estimate(state, prior)

    a, b = run(observations), run(shuffled)
    assert math.isclose(a.mean, b.mean, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(a.variance, b.variance, rel_tol=1e-9, abs_tol=1e-12)


@settings(max_examples=200, deadline=None)
@given(priors, xs, st.floats(0, 5000))
def test_evidence_fades_to_nothing_given_enough_time(
    prior: TraitPrior, x: float, gap: float
) -> None:
    state = observe(TraitState(), prior, x, T0)
    far = estimate(state, prior, at=T0 + timedelta(days=gap + 40 * prior.half_life_days))
    assert far.n < 1e-6
    assert math.isclose(far.mean, prior.mu0, rel_tol=1e-3, abs_tol=1e-3 * (1 + abs(x)))
