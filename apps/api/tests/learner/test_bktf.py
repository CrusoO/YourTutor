from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.learner.bkt import BktParams, posterior
from app.learner.bktf import AttemptKind, BktFParams, decay, predict_correct, update

PARAMS = BktFParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2, tau_days=10.0)
VALID, GUESS, HINTED = AttemptKind.VALID, AttemptKind.RAPID_GUESS, AttemptKind.HINTED


def params_strategy() -> st.SearchStrategy[BktFParams]:
    return st.builds(
        BktFParams,
        p_init=st.floats(0.01, 0.6),
        p_learn=st.floats(0.01, 0.9),
        p_slip=st.floats(0.01, 0.45),
        p_guess=st.floats(0.01, 0.45),
        tau_days=st.floats(0.5, 365.0),
        p_floor=st.floats(0.0, 0.5),
        hint_weight=st.floats(0.0, 1.0),
    )


# --- numbers worked by hand ---------------------------------------------------------------------


def test_first_valid_correct_matches_hand_calculation() -> None:
    # posterior = 0.2*0.9 / (0.2*0.9 + 0.8*0.2) = 0.18/0.34; then 0.5294 + 0.4706*0.15 = 0.6
    got = update(0.2, correct=True, kind=VALID, gap_days=0.0, params=PARAMS)
    assert got == pytest.approx(0.6)


def test_decay_matches_formula() -> None:
    # floor = max(0.2, 0) = 0.2; 0.2 + (0.9 - 0.2) * exp(-10/10)
    assert decay(0.9, 10.0, PARAMS) == pytest.approx(0.2 + 0.7 * math.exp(-1.0))


def test_decay_with_no_gap_changes_nothing() -> None:
    assert decay(0.7, 0.0, PARAMS) == pytest.approx(0.7)


def test_negative_gap_counts_as_zero() -> None:
    assert decay(0.7, -3.0, PARAMS) == decay(0.7, 0.0, PARAMS)


def test_nan_gap_is_rejected() -> None:
    with pytest.raises(ValueError):
        decay(0.7, float("nan"), PARAMS)


def test_predict_correct() -> None:
    assert predict_correct(0.5, PARAMS) == pytest.approx(0.5 * 0.9 + 0.5 * 0.2)


def test_a_rapid_guess_is_predicted_at_the_guess_rate_whatever_is_known() -> None:
    assert predict_correct(0.95, PARAMS, GUESS) == PARAMS.p_guess


# --- the attempt kinds --------------------------------------------------------------------------


def test_rapid_guess_changes_nothing_beyond_decay() -> None:
    for correct in (True, False):
        got = update(0.6, correct=correct, kind=GUESS, gap_days=5.0, params=PARAMS)
        assert got == decay(0.6, 5.0, PARAMS)


def test_rapid_guess_wrong_never_collapses_to_one() -> None:
    # The mistake this model avoids: a guess treated as G=1 makes the "incorrect" posterior 1.
    assert update(0.3, correct=False, kind=GUESS, gap_days=0.0, params=PARAMS) == pytest.approx(0.3)


def test_hinted_correct_with_zero_weight_only_learns() -> None:
    p = BktFParams(0.2, 0.15, 0.1, 0.2, 10.0, hint_weight=0.0)
    got = update(0.4, correct=True, kind=HINTED, gap_days=0.0, params=p)
    assert got == pytest.approx(0.4 + 0.6 * 0.15)


def test_hinted_correct_with_full_weight_equals_valid() -> None:
    p = BktFParams(0.2, 0.15, 0.1, 0.2, 10.0, hint_weight=1.0)
    hinted = update(0.4, correct=True, kind=HINTED, gap_days=2.0, params=p)
    valid = update(0.4, correct=True, kind=VALID, gap_days=2.0, params=p)
    assert hinted == pytest.approx(valid)


def test_hinted_correct_counts_for_less_than_valid_correct() -> None:
    hinted = update(0.4, correct=True, kind=HINTED, gap_days=0.0, params=PARAMS)
    valid = update(0.4, correct=True, kind=VALID, gap_days=0.0, params=PARAMS)
    assert hinted < valid


def test_hinted_incorrect_is_a_normal_incorrect() -> None:
    hinted = update(0.4, correct=False, kind=HINTED, gap_days=1.0, params=PARAMS)
    valid = update(0.4, correct=False, kind=VALID, gap_days=1.0, params=PARAMS)
    assert hinted == pytest.approx(valid)


def test_matches_the_legacy_model_when_nothing_is_forgotten() -> None:
    legacy = BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)
    p_new = p_old = 0.2
    for correct in (True, True, False, True, False, False, True):
        p_new = update(p_new, correct=correct, kind=VALID, gap_days=0.0, params=PARAMS)
        p_old = posterior(p_old, correct=correct, params=legacy)
        assert p_new == pytest.approx(p_old)


# --- parameter validation -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"p_init": 0.0},
        {"p_init": 1.0},
        {"p_learn": 0.0},
        {"p_slip": 0.0},
        {"p_guess": 1.0},
        {"p_slip": 0.6, "p_guess": 0.5},
        {"tau_days": 0.0},
        {"tau_days": float("inf")},
        {"p_floor": 1.0},
        {"hint_weight": 1.5},
        {"p_learn": float("nan")},
    ],
)
def test_invalid_params_are_rejected(overrides: dict[str, float]) -> None:
    base = {"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2, "tau_days": 10.0}
    with pytest.raises(ValueError):
        BktFParams(**{**base, **overrides})


def test_floor_is_the_larger_of_prior_and_configured_floor() -> None:
    assert BktFParams(0.2, 0.1, 0.1, 0.2, 10.0, p_floor=0.35).floor == 0.35
    assert BktFParams(0.4, 0.1, 0.1, 0.2, 10.0, p_floor=0.35).floor == 0.4


# --- properties ---------------------------------------------------------------------------------

probability = st.floats(0.0, 1.0)
gap = st.floats(0.0, 1000.0)
kind = st.sampled_from(list(AttemptKind))


@settings(max_examples=200, deadline=None)
@given(params_strategy(), st.lists(st.tuples(st.booleans(), kind, gap), max_size=40))
def test_estimate_always_stays_in_unit_interval(
    params: BktFParams, attempts: list[tuple[bool, AttemptKind, float]]
) -> None:
    p = params.p_init
    for correct, k, g in attempts:
        p = update(p, correct=correct, kind=k, gap_days=g, params=params)
        assert 0.0 <= p <= 1.0


@settings(max_examples=200, deadline=None)
@given(params_strategy(), probability, gap)
def test_decay_moves_toward_the_floor_and_never_past_it(
    params: BktFParams, p: float, g: float
) -> None:
    out = decay(p, g, params)
    low, high = sorted((p, params.floor))
    assert low - 1e-12 <= out <= high + 1e-12
    if p >= params.floor:
        assert out >= params.floor - 1e-12


@settings(max_examples=200, deadline=None)
@given(params_strategy(), probability, gap, gap)
def test_longer_gap_means_more_forgetting(
    params: BktFParams, p: float, g1: float, g2: float
) -> None:
    short, long = sorted((g1, g2))
    assert (
        abs(decay(p, long, params) - params.floor)
        <= abs(decay(p, short, params) - params.floor) + 1e-12
    )


@settings(max_examples=200, deadline=None)
@given(params_strategy(), probability, st.booleans(), gap)
def test_rapid_guess_never_raises_a_known_estimate(
    params: BktFParams, p: float, correct: bool, g: float
) -> None:
    out = update(p, correct=correct, kind=GUESS, gap_days=g, params=params)
    assert out == decay(p, g, params)
    if p >= params.floor:
        assert out <= p + 1e-12


@settings(max_examples=200, deadline=None)
@given(params_strategy(), st.floats(0.0, 0.999), gap, kind)
def test_wrong_answer_never_reaches_certainty(
    params: BktFParams, p: float, g: float, k: AttemptKind
) -> None:
    assert update(p, correct=False, kind=k, gap_days=g, params=params) < 1.0


@settings(max_examples=200, deadline=None)
@given(params_strategy(), probability)
def test_a_correct_answer_never_lowers_the_estimate_at_zero_gap(
    params: BktFParams, p: float
) -> None:
    for k in (VALID, HINTED):
        assert update(p, correct=True, kind=k, gap_days=0.0, params=params) >= p - 1e-12


@settings(max_examples=200, deadline=None)
@given(params_strategy(), probability, gap, st.booleans(), kind)
def test_update_is_deterministic(
    params: BktFParams, p: float, g: float, correct: bool, k: AttemptKind
) -> None:
    first = update(p, correct=correct, kind=k, gap_days=g, params=params)
    assert update(p, correct=correct, kind=k, gap_days=g, params=params) == first
