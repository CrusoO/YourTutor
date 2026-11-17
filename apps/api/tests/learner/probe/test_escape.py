"""Escape hatches: too easy, too hard, jump here (spec section 6)."""

from __future__ import annotations

from typing import Any, cast

import pytest

from app.learner.probe.escape import (
    JUMP_MAX_SKILLS,
    STUDENT_STOP,
    ancestors_space,
    apply_claim,
    jump_advice,
    jump_belief,
    stop_on_request,
)
from app.learner.probe.result import NOT_KNOWN, UNCLEAR, summarise, to_mastery_seed
from app.learner.probe.select import marginals
from app.learner.probe.types import ProbeResult, Space
from app.learner.probe.update import update
from tests.learner.probe.probe_helpers import CFG, SKILLS, ans, fresh, typed_items

ITEMS = {i.skill_id: i for i in typed_items(SKILLS)}
CHAIN = {f"s{i}": [f"s{i - 1}"] for i in range(1, 10)}


def test_too_easy_shifts_mixture_toward_the_high_base() -> None:
    before = fresh()
    after = apply_claim(before, "too_easy", CFG)
    assert after.mixture[2] > before.mixture[2]
    assert after.mixture[0] < before.mixture[0]
    assert sum(after.mixture) == pytest.approx(1.0)
    assert sum(after.weights) == pytest.approx(1.0)
    assert min(after.mixture) >= CFG.mixture_floor - 1e-9
    # raises belief in harder skills, but a claim alone never resolves anything
    assert marginals(after)["d"] > marginals(before)["d"]
    assert all(0.1 < m < 0.99 for m in marginals(after).values())


def test_too_easy_multiplies_the_high_component_by_three_when_unclamped() -> None:
    before = fresh()
    after = apply_claim(before, "too_easy", CFG)
    ratio = (after.mixture[2] / after.mixture[1]) / (before.mixture[2] / before.mixture[1])
    assert ratio == pytest.approx(3.0)


def test_repeated_too_easy_keeps_the_floor() -> None:
    belief = fresh()
    for _ in range(10):
        belief = apply_claim(belief, "too_easy", CFG)
    assert min(belief.mixture) >= CFG.mixture_floor - 1e-9
    assert sum(belief.mixture) == pytest.approx(1.0)


def test_claim_is_checked_by_evidence() -> None:
    claimed = apply_claim(fresh(), "too_easy", CFG)
    wrong = update(claimed, ITEMS["a"], ans(ITEMS["a"], False), CFG)
    assert marginals(wrong)["a"] < marginals(claimed)["a"]


def test_too_hard_changes_no_belief_and_unknown_claim_is_rejected() -> None:
    belief = fresh()
    assert apply_claim(belief, "too_hard", CFG) == belief
    with pytest.raises(ValueError):
        apply_claim(belief, cast(Any, "bogus"), CFG)


def test_stop_on_request_is_unknown_not_failed() -> None:
    belief = fresh()
    belief = update(belief, ITEMS["a"], ans(ITEMS["a"], False, dont_know=True), CFG)
    result = stop_on_request(belief, 1, CFG, SKILLS)
    assert result.stop_reason == STUDENT_STOP
    assert result.asked == 1
    assert result.start_skill is not None
    # everything still unresolved is "unclear", never invented as failed
    unresolved = [s for s, m in result.marginals.items() if 0.1 < m < 0.9]
    assert unresolved and all(result.labels[s] == UNCLEAR for s in unresolved)
    seeds = to_mastery_seed(result, CFG)
    assert all(CFG.seed_floor <= v <= CFG.seed_cap for v in seeds.values())


def test_stop_matches_summarise_with_the_stop_reason() -> None:
    belief = fresh()
    assert stop_on_request(belief, 0, CFG, SKILLS) == summarise(
        belief, 0, STUDENT_STOP, CFG, SKILLS
    )


def test_ancestors_space_is_target_plus_two_levels() -> None:
    space = ancestors_space("s9", CHAIN, CFG)
    assert set(space.skills) == {"s9", "s8", "s7"}
    assert len(space.states) == 4


def test_ancestors_space_caps_at_eight_skills() -> None:
    wide = {"t": [f"p{i}" for i in range(12)]}
    space = ancestors_space("t", wide, CFG)
    assert len(space.skills) == JUMP_MAX_SKILLS
    assert space.skills[0] == "t"


def test_ancestors_space_root_is_a_single_skill() -> None:
    assert ancestors_space("s0", CHAIN, CFG).skills == ("s0",)


def test_jump_belief_carries_the_mixture_posterior() -> None:
    old = apply_claim(fresh(), "too_easy", CFG)
    new = jump_belief("s9", CHAIN, CFG, previous=old)
    assert new.mixture == pytest.approx(old.mixture)
    assert jump_belief("s9", CHAIN, CFG).mixture == pytest.approx(fresh().mixture)


def _mini_result(answers: dict[str, bool]) -> tuple[Space, ProbeResult]:
    belief = jump_belief("s9", CHAIN, CFG)
    space = belief.space
    for skill, ok in answers.items():
        item = typed_items([skill], 2)
        for it in item:
            belief = update(belief, it, ans(it, ok), CFG)
    return space, summarise(belief, len(answers), "x", CFG, space.skills)


def test_jump_advice_starts_at_target_when_prerequisites_hold() -> None:
    space, result = _mini_result({"s8": True, "s7": True})
    advice = jump_advice(result, "s9", space)
    assert advice.start_at_target and advice.first_gap is None


def test_jump_advice_offers_the_first_gap() -> None:
    space, result = _mini_result({"s8": False, "s7": False})
    assert result.labels["s7"] == NOT_KNOWN
    advice = jump_advice(result, "s9", space)
    assert not advice.start_at_target
    assert advice.first_gap == "s7"  # shallowest unknown ancestor


def test_jump_advice_with_unclear_prerequisites_still_starts_at_target() -> None:
    belief = jump_belief("s9", CHAIN, CFG)
    result = summarise(belief, 0, "x", CFG, belief.space.skills)
    assert jump_advice(result, "s9", belief.space).start_at_target
