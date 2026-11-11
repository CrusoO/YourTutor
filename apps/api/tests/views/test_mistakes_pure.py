"""The mistake list and warm-up choice: pure functions, no database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.views.mistakes import (
    K_FLOOR,
    Hit,
    WarmItem,
    aggregate,
    enough_students,
    pick_warmup,
)

NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)


def hit(
    student: int, mid: str = "MC.A", days_ago: float = 1, item: str = "I1", skill: str = "S1"
) -> Hit:
    return Hit(f"s{student}", mid, skill, item, NOW - timedelta(days=days_ago))


def test_counts_students_and_occurrences_separately() -> None:
    hits = [hit(i) for i in range(5)] + [hit(0), hit(0)]
    (row,) = aggregate(hits, NOW)
    assert (row.students, row.occurrences) == (5, 7)


def test_a_row_below_the_floor_is_dropped() -> None:
    hits = [hit(i) for i in range(K_FLOOR - 1)] + [hit(0, days_ago=2)] * 20
    assert aggregate(hits, NOW) == []  # many hits from four people is still four people


def test_floor_is_exactly_five() -> None:
    assert K_FLOOR == 5
    assert aggregate([hit(i) for i in range(5)], NOW)
    assert not aggregate([hit(i) for i in range(4)], NOW)


def test_window_is_respected_and_configurable() -> None:
    old = [hit(i, days_ago=20) for i in range(5)]
    assert aggregate(old, NOW) == []
    assert aggregate(old, NOW, days=30)[0].students == 5
    future = [hit(i, days_ago=-1) for i in range(5)]
    assert aggregate(future, NOW) == []


def test_students_outside_the_window_do_not_count_toward_the_floor() -> None:
    hits = [hit(i) for i in range(4)] + [hit(9, days_ago=30)]
    assert aggregate(hits, NOW) == []


def test_order_is_students_then_occurrences_then_id_and_input_order_is_irrelevant() -> None:
    hits = (
        [hit(i, "MC.B") for i in range(6)]
        + [hit(i, "MC.A") for i in range(5)]
        + [hit(0, "MC.A")] * 3
        + [hit(i, "MC.C") for i in range(5)]
    )
    forward = [r.misconception_id for r in aggregate(hits, NOW)]
    backward = [r.misconception_id for r in aggregate(hits[::-1], NOW)]
    assert forward == backward == ["MC.B", "MC.A", "MC.C"]


def test_skill_and_example_item_are_the_most_common_with_stable_ties() -> None:
    hits = [hit(i, item="I2", skill="S2") for i in range(3)]
    hits += [hit(i, item="I1", skill="S1") for i in range(3, 6)]
    (row,) = aggregate(hits, NOW)
    assert (row.skill_id, row.example_item_id) == ("S1", "I1")


def test_output_carries_no_student_identifier() -> None:
    (row,) = aggregate([hit(i) for i in range(5)], NOW)
    assert not any("s0" in str(v) for v in vars(row).values())


def test_class_gate() -> None:
    assert not enough_students(4)
    assert enough_students(5)


# warm-up


def items(n: int, mids: set[str], prefix: str = "I") -> list[WarmItem]:
    return [WarmItem(f"{prefix}{i:02d}", "S1", frozenset(mids)) for i in range(n)]


def test_warmup_is_five_items_and_each_has_a_target() -> None:
    pool = items(8, {"MC.A"}) + items(8, {"MC.B"}, "J")
    picked = pick_warmup(pool, ["MC.A", "MC.B"], "1")
    assert len(picked) == 5
    assert len({i for i, _ in picked}) == 5
    assert {t for _, t in picked} == {"MC.A", "MC.B"}


def test_same_seed_same_warmup_other_seed_differs() -> None:
    pool = items(30, {"MC.A"})
    first = pick_warmup(pool, ["MC.A"], "7")
    assert first == pick_warmup(list(reversed(pool)), ["MC.A"], "7")
    assert any(first != pick_warmup(pool, ["MC.A"], str(s)) for s in range(2, 8))


def test_an_item_serving_two_targets_is_used_once() -> None:
    pool = items(6, {"MC.A", "MC.B"})
    picked = pick_warmup(pool, ["MC.A", "MC.B"], "1")
    assert len(picked) == 5 and len({i for i, _ in picked}) == 5


def test_not_enough_items_is_not_padded() -> None:
    pool = items(2, {"MC.A"}) + items(1, {"MC.C"}, "K")
    picked = pick_warmup(pool, ["MC.A", "MC.B"], "1")
    assert len(picked) == 2  # nothing for MC.B, and the unrelated item is never used
    assert all(t == "MC.A" for _, t in picked)


def test_no_servable_items_gives_an_empty_warmup() -> None:
    assert pick_warmup([], ["MC.A"], "1") == []
    assert pick_warmup(items(3, {"MC.Z"}), ["MC.A"], "1") == []
