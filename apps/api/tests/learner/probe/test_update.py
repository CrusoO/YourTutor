from __future__ import annotations

import pytest
from probe_helpers import CFG, ans, fresh, typed_items

from app.learner.probe.select import marginals
from app.learner.probe.types import Answer, ProbeItem
from app.learner.probe.update import item_params, likelihood, update

ITEMS = {i.skill_id: i for i in typed_items(["a", "b", "c", "d", "e", "f"])}


def test_item_params() -> None:
    assert item_params("x", "a", CFG).guess == CFG.guess_typed
    assert item_params("x", "a", CFG, multistep=True).slip == CFG.slip_multistep
    mcq4 = item_params("x", "a", CFG, options=4)
    assert (mcq4.guess, mcq4.is_mcq) == (0.25, True)
    assert item_params("x", "a", CFG, options=2).guess == CFG.guess_mcq_cap
    assert item_params("x", "a", CFG, options=20).guess == CFG.guess_mcq_floor
    with pytest.raises(ValueError):
        item_params("x", "a", CFG, options=1)


def test_likelihood_table() -> None:
    item = ITEMS["a"]
    right = Answer(item.item_id, "a", True)
    wrong = Answer(item.item_id, "a", False)
    assert likelihood(item, right, CFG) == (pytest.approx(0.90), pytest.approx(0.05))
    assert likelihood(item, wrong, CFG) == (pytest.approx(0.10), pytest.approx(0.95))
    idk = Answer(item.item_id, "a", False, dont_know=True)
    assert likelihood(item, idk, CFG) == (CFG.idk_known, CFG.idk_unknown)


def test_rapid_and_unsure_correct_answers_are_weaker_evidence() -> None:
    item = ITEMS["a"]
    normal = likelihood(item, Answer(item.item_id, "a", True), CFG)
    for flag in ({"rapid": True}, {"unsure": True}):
        weak = likelihood(item, Answer(item.item_id, "a", True, **flag), CFG)
        assert weak[1] == CFG.guess_uncertain > normal[1]
        assert weak[0] / weak[1] < normal[0] / normal[1]
    # a fast wrong answer uses the normal wrong likelihood
    fast_wrong = Answer(item.item_id, "a", False, rapid=True)
    assert likelihood(item, fast_wrong, CFG) == likelihood(
        item, Answer(item.item_id, "a", False), CFG
    )


def test_dont_know_cannot_be_correct() -> None:
    with pytest.raises(ValueError):
        Answer("x", "a", True, dont_know=True)


def test_probe_item_validation() -> None:
    with pytest.raises(ValueError):
        ProbeItem("x", "a", guess=0.6, slip=0.5, is_mcq=False)
    with pytest.raises(ValueError):
        ProbeItem("", "a", guess=0.1, slip=0.1, is_mcq=False)


def test_correct_answer_raises_skill_and_ancestors_not_unrelated() -> None:
    before = fresh()
    after = update(before, ITEMS["d"], ans(ITEMS["d"]), CFG)
    m0, m1 = marginals(before), marginals(after)
    for skill in ("d", "b", "c", "a"):
        assert m1[skill] > m0[skill]
    assert m1["d"] > 0.5
    # the island moves only through the shared starting-level mixture, never a direct update
    assert m0["e"] < m1["e"] < m1["a"]


def test_wrong_answer_lowers_skill_and_dependents() -> None:
    before = fresh()
    after = update(before, ITEMS["b"], ans(ITEMS["b"], False), CFG)
    m0, m1 = marginals(before), marginals(after)
    assert m1["b"] < m0["b"] and m1["d"] < m0["d"]
    assert m1["a"] < m0["a"] or m1["a"] == pytest.approx(m0["a"], abs=1e-9)


def test_dont_know_is_stronger_than_wrong() -> None:
    before = fresh()
    wrong = marginals(update(before, ITEMS["b"], ans(ITEMS["b"], False), CFG))["b"]
    idk = marginals(update(before, ITEMS["b"], ans(ITEMS["b"], dont_know=True), CFG))["b"]
    assert idk < wrong


def test_update_is_pure_and_normalised() -> None:
    before = fresh()
    snapshot = before.weights
    after = update(before, ITEMS["a"], ans(ITEMS["a"]), CFG)
    assert before.weights == snapshot and after is not before
    assert sum(after.weights) == pytest.approx(1.0) and sum(after.mixture) == pytest.approx(1.0)


def test_mixture_moves_toward_the_matching_level() -> None:
    belief = fresh()
    for skill in ("d", "b", "c"):
        belief = update(belief, ITEMS[skill], ans(ITEMS[skill]), CFG)
    assert belief.mixture[2] > belief.mixture[1] > belief.mixture[0]
    low = fresh()
    for skill in ("a", "e"):
        low = update(low, ITEMS[skill], ans(ITEMS[skill], dont_know=True), CFG)
    assert low.mixture[0] > low.mixture[2]


def test_mismatched_or_unknown_item_is_rejected() -> None:
    belief = fresh()
    with pytest.raises(ValueError):
        update(belief, ITEMS["a"], ans(ITEMS["b"]), CFG)
    stranger = ProbeItem("q", "zzz", 0.05, 0.1, False)
    with pytest.raises(ValueError):
        update(belief, stranger, Answer("q", "zzz", True), CFG)


def test_thirty_wrong_answers_and_all_idk_never_break_the_belief() -> None:
    belief = fresh()
    for n in range(30):
        item = ITEMS["abcdef"[n % 6]]
        belief = update(belief, item, ans(item, False), CFG)
        assert all(w > 0 for w in belief.weights)
    assert sum(belief.weights) == pytest.approx(1.0)
    idk = fresh()
    for n in range(60):
        item = ITEMS["abcdef"[n % 6]]
        idk = update(idk, item, ans(item, dont_know=True), CFG)
    assert sum(idk.weights) == pytest.approx(1.0)
    assert marginals(idk)["a"] < 0.01
    assert not idk.reset


def test_underflow_restores_the_prior_and_flags_it() -> None:
    from dataclasses import replace

    belief = fresh()
    tiny = tuple(tuple(1e-310 for _ in row) for row in belief.joint)
    broken = replace(belief, joint=tiny)
    result = update(broken, ITEMS["a"], ans(ITEMS["a"]), CFG)
    assert result.reset
    assert result.weights == fresh().weights
