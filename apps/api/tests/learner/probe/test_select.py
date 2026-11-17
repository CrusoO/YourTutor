from __future__ import annotations

import pytest
from probe_helpers import CFG, ans, fresh, typed_items

from app.learner.probe.select import choose_item, expected_gain, marginals
from app.learner.probe.types import Belief
from app.learner.probe.update import item_params, update

SK = ["a", "b", "c", "d", "e", "f"]


def pick(belief: Belief, items, used=frozenset(), counts=None, last_mcq=False):
    return choose_item(belief, items, used, counts or {}, last_mcq, CFG)


def test_expected_gain_is_nonnegative_and_at_most_one_bit() -> None:
    belief = fresh()
    for item in typed_items(SK):
        assert 0.0 <= expected_gain(belief, item) <= 1.0 + 1e-9


def test_gain_is_zero_when_the_skill_is_certain() -> None:
    belief = fresh()
    space = belief.space
    bit = 1 << space.index("a")
    for known in (True, False):
        w = [1.0 if bool(s & bit) == known else 0.0 for s in space.states]
        total = sum(w)
        w = [x / total for x in w]
        certain = Belief(space, tuple(w), belief.mixture, belief.joint)
        assert marginals(certain)["a"] == pytest.approx(1.0 if known else 0.0)
        assert expected_gain(certain, typed_items(["a"])[0]) == pytest.approx(0.0, abs=1e-9)


def test_typed_item_is_worth_more_than_a_guessable_mcq_of_the_same_skill() -> None:
    belief = fresh()
    typed = item_params("t", "b", CFG)
    mcq = item_params("m", "b", CFG, options=2)
    assert expected_gain(belief, typed) > expected_gain(belief, mcq)
    assert pick(belief, [mcq, typed]) is typed


def test_first_pick_is_deterministic_and_ties_break_by_id() -> None:
    items = typed_items(["e"], per_skill=3)
    belief = fresh()
    first = pick(belief, items)
    assert first is not None and first.item_id == "e0"
    assert pick(belief, list(reversed(items))) == first


def test_used_items_and_per_skill_cap_are_respected() -> None:
    items = typed_items(["a"], per_skill=4)
    belief = fresh()
    assert pick(belief, items, used=frozenset({"a0"})).item_id == "a1"
    assert pick(belief, items, counts={"a": CFG.max_per_skill}) is None
    assert pick(belief, items, used=frozenset(i.item_id for i in items)) is None
    assert pick(belief, []) is None


def test_no_second_mcq_in_a_row() -> None:
    mcq = item_params("m", "a", CFG, options=4)
    typed = item_params("t", "e", CFG)
    belief = fresh()
    assert pick(belief, [mcq], last_mcq=True) is None
    assert pick(belief, [mcq, typed], last_mcq=True) is typed


def test_items_outside_the_space_are_ignored() -> None:
    stranger = item_params("s", "zzz", CFG)
    assert pick(fresh(), [stranger]) is None


def test_opener_prefers_winnable_items_when_one_exists() -> None:
    belief = fresh()
    easy = item_params("easy", "a", CFG, options=2)  # guessable, so P(correct) is high
    # make "a" very likely known: the opener must then pick it over a more informative skill
    for _ in range(2):
        belief = update(belief, typed_items(["a"])[0], ans(typed_items(["a"])[0]), CFG)
    assert marginals(belief)["a"] > 0.9
    hard = item_params("hard", "d", CFG)
    chosen = choose_item(belief, [hard, easy], frozenset(), {}, False, CFG)
    assert chosen is easy
    # after the opener items, plain information gain decides
    later = choose_item(belief, [hard, easy], frozenset({"x", "y"}), {}, False, CFG)
    assert later is hard


def test_opener_falls_back_when_nothing_is_winnable() -> None:
    belief = fresh()
    assert marginals(belief)["d"] < 0.7
    only = item_params("only", "d", CFG)
    assert pick(belief, [only]) is only
