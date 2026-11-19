"""The reason model weighs every cause of a wrong answer instead of picking the first match."""

from __future__ import annotations

import dataclasses

import pytest

from app.learner.reason import (
    DEFAULT_CONFIG,
    OTHER,
    Posterior,
    ReasonConfig,
    apply_correction,
    assess,
    cause_id,
    cause_kind,
    likelihoods,
    update,
    view,
)
from tests.orchestrator.conftest import catalog_item, make_learner, make_session

SIGN = cause_id("misconception", "MC.SIGN")
ADD = cause_id("misconception", "MC.ADD")
SLIP = cause_id("slip", "sign_flip")


def _item(**fields):  # type: ignore[no-untyped-def]
    return catalog_item(
        answer="12",
        rules=(("MC.ADD", ("18",)), ("MC.SIGN", ("-12", "18"))),
        slip_patterns=({"kind": "sign_flip"},),
        intermediate_values=("15",),
        **fields,
    )


def _assess(response: str, *, skilled: bool = True, **kw):  # type: ignore[no-untyped-def]
    item = _item()
    learner = make_learner(p_known={item.primary_skill: 0.96 if skilled else 0.1})
    return assess(item, response, learner, make_session(item), **kw)


def test_one_clear_misconception_is_named_with_confidence() -> None:
    result = _assess("-12", skilled=False)  # only MC.SIGN matches; no slip for a beginner
    assert result.view.band == "likely"
    assert result.view.cause == SIGN
    assert not result.view.needs_followup


def test_two_misconceptions_with_the_same_answer_are_not_forced_apart() -> None:
    result = _assess("18")  # both MC.ADD and MC.SIGN produce 18
    assert result.view.band == "maybe"
    assert result.view.needs_followup
    assert set(result.view.rivals) <= {ADD, SIGN}
    assert abs(result.posterior.get(ADD) - result.posterior.get(SIGN)) < 1e-9


def test_an_answer_nobody_wrote_down_is_never_given_a_false_label() -> None:
    result = _assess("7")
    assert result.view.cause is None
    assert result.view.band == "unclear"
    assert result.posterior.top()[0] == OTHER


def test_a_confident_wrong_answer_points_at_a_belief_more_than_an_unsure_one() -> None:
    sure = _assess("-12", confidence="sure").posterior.get(SIGN)
    plain = _assess("-12").posterior.get(SIGN)
    unsure = _assess("-12", confidence="unsure").posterior.get(SIGN)
    assert sure > plain > unsure


def test_a_slip_competes_with_the_misconception_for_a_skilled_learner_only() -> None:
    skilled = _assess("-12", skilled=True).posterior
    beginner = _assess("-12", skilled=False).posterior
    assert skilled.get(SLIP) > 0
    assert beginner.get(SLIP) == 0


def test_repeating_the_same_cause_raises_belief_and_a_different_answer_lowers_it() -> None:
    first = _assess("-12", skilled=False)
    again = _assess("-12", skilled=False, prior=first.posterior)
    assert again.posterior.get(SIGN) > first.posterior.get(SIGN)
    different = _assess("7", skilled=False, prior=first.posterior)
    assert different.posterior.get(SIGN) < first.posterior.get(SIGN)


def test_that_is_not_why_lowers_the_named_cause_and_the_lead_is_given_up() -> None:
    first = _assess("-12", skilled=False)
    corrected = apply_correction(first.posterior, SIGN)
    assert corrected.get(SIGN) < first.posterior.get(SIGN)
    assert view(corrected).band != "likely"


def test_correcting_the_only_cause_falls_back_to_other() -> None:
    only = Posterior.from_mapping({SIGN: 1.0})
    corrected = apply_correction(only, SIGN)
    assert corrected.top()[0] == OTHER


def test_correcting_a_cause_that_is_not_in_play_changes_nothing() -> None:
    first = _assess("-12", skilled=False)
    assert apply_correction(first.posterior, "misconception:MC.NONE") == first.posterior


@pytest.mark.parametrize("response", ["-12", "18", "7", "15", "12", ""])
@pytest.mark.parametrize("confidence", [None, "sure", "unsure"])
def test_weights_always_add_to_one_and_are_ordered(response: str, confidence) -> None:  # type: ignore[no-untyped-def]
    result = _assess(response, confidence=confidence)
    weights = [w for _, w in result.posterior.weights]
    assert sum(weights) == pytest.approx(1.0)
    assert weights == sorted(weights, reverse=True)
    assert all(w > 0 for w in weights)


def test_the_result_is_deterministic_and_immutable() -> None:
    a = _assess("18")
    b = _assess("18")
    assert a.posterior == b.posterior
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.posterior.weights = ()  # type: ignore[misc]


def test_likelihoods_always_include_other() -> None:
    assert OTHER in likelihoods(())
    assert OTHER in likelihoods((SIGN,), confidence="sure")


def test_update_with_no_prior_is_just_the_likelihoods_normalised() -> None:
    post = update(None, {SIGN: 0.9, OTHER: 0.1})
    assert post.get(SIGN) == pytest.approx(0.9)


def test_cause_ids_round_trip() -> None:
    assert cause_kind(cause_id("slip", "off_by")) == "slip"
    assert cause_id("other") == "other"


@pytest.mark.parametrize(
    "bad",
    [{"lik_slip": 0.0}, {"lik_slip": 1.0}, {"band_maybe": 0.9}, {"sure_boost": {"slip": 1.0}}],
)
def test_the_config_rejects_numbers_that_break_the_maths(bad: dict) -> None:  # type: ignore[type-arg]
    with pytest.raises(ValueError):
        ReasonConfig(**bad)


def test_the_default_config_is_valid() -> None:
    assert DEFAULT_CONFIG.band_likely > DEFAULT_CONFIG.band_maybe
