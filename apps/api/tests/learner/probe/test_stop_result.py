from __future__ import annotations

import pytest
from probe_helpers import CFG, ans, fresh, typed_items

from app.learner.probe.result import summarise, to_mastery_seed
from app.learner.probe.select import marginals
from app.learner.probe.stop import item_cap, should_stop
from app.learner.probe.types import Answer
from app.learner.probe.update import update

ITEMS = {i.skill_id: i for i in typed_items(["a", "b", "c", "d", "e", "f"])}
ORDER = ["a", "b", "c", "d", "e", "f"]


def wrong(n: int) -> list[Answer]:
    return [Answer(f"i{k}", "a", False) for k in range(n)]


def test_keeps_going_when_nothing_holds() -> None:
    assert should_stop(fresh(), 3, 2.0, [], 0.5, CFG) is None


def test_stop_reasons_in_order() -> None:
    belief = fresh()
    assert should_stop(belief, 3, 2.0, [], 0.01, CFG) == "low_gain"
    assert should_stop(belief, 12, 2.0, [], 0.5, CFG) == "item_cap"
    assert should_stop(belief, 3, 10.0, [], 0.5, CFG) == "time_cap"
    assert should_stop(belief, 3, 2.0, wrong(3), 0.5, CFG) == "frustration"
    assert should_stop(belief, 3, 2.0, wrong(2), 0.5, CFG) is None
    mixed = wrong(2) + [Answer("ok", "a", True)]
    assert should_stop(belief, 3, 2.0, mixed, 0.5, CFG) is None
    idk = [Answer(f"i{k}", "a", False, dont_know=True) for k in range(3)]
    assert should_stop(belief, 3, 2.0, idk, 0.5, CFG) == "frustration"


def test_resolved_when_every_skill_is_clear() -> None:
    belief = fresh()
    for skill in ("d", "f"):
        for _ in range(3):
            belief = update(belief, ITEMS[skill], ans(ITEMS[skill]), CFG)
    for _ in range(4):
        belief = update(belief, ITEMS["e"], ans(ITEMS["e"]), CFG)
    marks = marginals(belief)
    assert all(m >= CFG.resolve_hi or m <= CFG.resolve_lo for m in marks.values()), marks
    assert should_stop(belief, 5, 1.0, [], 0.5, CFG) == "resolved"


def test_cap_is_wider_only_for_wide_graphs() -> None:
    assert item_cap(12, CFG) == 12
    assert item_cap(13, CFG) == 14


def test_summarise_labels_and_outer_fringe() -> None:
    belief = fresh()
    for _ in range(3):
        belief = update(belief, ITEMS["b"], ans(ITEMS["b"]), CFG)  # b known, so a known
    for _ in range(3):
        belief = update(belief, ITEMS["e"], ans(ITEMS["e"], dont_know=True), CFG)
    result = summarise(belief, 6, "low_gain", CFG, ORDER)
    assert result.labels["b"] == "known" and result.labels["a"] == "known"
    assert result.labels["e"] == "not_known"
    assert result.asked == 6 and result.stop_reason == "low_gain"
    marks = result.marginals
    assert marks["c"] >= 0.5  # b known and the island unknown: c leans known, d is next
    assert result.ready_skills == ("e", "d")  # lowest depth first
    assert "f" not in result.ready_skills  # its prerequisite e is not known
    assert result.start_skill == "e"
    assert result.mixture == belief.mixture and not result.belief_reset


def test_start_skill_ties_use_chapter_order() -> None:
    belief = fresh(["x", "y"], {})
    for skill in ("x", "y"):
        item = typed_items([skill])[0]
        belief = update(belief, item, ans(item, dont_know=True), CFG)
    result = summarise(belief, 0, "item_cap", CFG, ["y", "x"])
    marks = result.marginals
    assert marks["x"] == pytest.approx(marks["y"])
    assert result.start_skill == "y"
    assert summarise(belief, 0, "item_cap", CFG, []).start_skill == "x"  # then by id


def test_everything_known_has_no_start_skill() -> None:
    belief = fresh(["a"], {})
    for _ in range(4):
        belief = update(belief, ITEMS["a"], ans(ITEMS["a"]), CFG)
    result = summarise(belief, 4, "resolved", CFG, ["a"])
    assert result.start_skill is None and result.ready_skills == ()


def test_mastery_seed_clamps() -> None:
    belief = fresh()
    for _ in range(5):
        belief = update(belief, ITEMS["d"], ans(ITEMS["d"]), CFG)
        belief = update(belief, ITEMS["e"], ans(ITEMS["e"], dont_know=True), CFG)
    result = summarise(belief, 10, "item_cap", CFG, ORDER)
    seed = to_mastery_seed(result, CFG)
    assert set(seed) == set(ORDER)
    assert seed["d"] == CFG.seed_cap  # known, but a placement is never proof
    assert seed["e"] == CFG.seed_floor
    assert all(CFG.seed_floor <= v <= CFG.seed_cap for v in seed.values())
    unclear = fresh()
    mid = summarise(unclear, 0, "item_cap", CFG, ORDER)
    assert all(
        CFG.unclear_lo <= v <= CFG.unclear_hi
        for s, v in to_mastery_seed(mid, CFG).items()
        if mid.labels[s] == "unclear"
    )
