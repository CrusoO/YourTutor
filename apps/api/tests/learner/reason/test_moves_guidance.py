"""Help follows the cause, "another way" is really another way, and help fades with success."""

from __future__ import annotations

import pytest

from app.learner.reason.moves import (
    FAMILIES,
    LEVEL_MAX,
    LEVEL_MIN,
    PREFERENCE,
    Guidance,
    advance,
    offer,
)


def test_every_cause_prefers_every_family_exactly_once() -> None:
    for kind, order in PREFERENCE.items():
        assert sorted(order) == sorted(FAMILIES), kind


def test_a_misconception_starts_with_a_picture_and_a_slip_with_steps() -> None:
    assert offer("misconception")[0] == "picture"
    assert offer("slip")[0] == "steps"


def test_the_family_just_used_moves_to_the_end() -> None:
    first = offer("misconception")
    again = offer("misconception", recent=[first[0]], count=4)
    assert again[-1] == first[0]
    assert again[0] != first[0]


def test_only_available_families_are_offered_and_the_count_is_respected() -> None:
    assert set(offer("slip", available={"steps", "worked"})) == {"steps", "worked"}
    assert len(offer("slip", count=2)) == 2


def test_an_unknown_cause_gets_the_general_order() -> None:
    assert offer("something_new") == offer("other")


def test_one_remaining_family_is_kept_even_if_it_was_just_used() -> None:
    assert offer("slip", recent=["steps"], available={"steps"}) == ("steps",)


def test_two_confident_unaided_wins_take_help_away_one_step() -> None:
    g = Guidance()
    g = advance(g, correct=True, hinted=False, confident=True)
    assert g.level == Guidance().level and g.wins == 1
    g = advance(g, correct=True, hinted=False, confident=None)
    assert g.level == Guidance().level - 1 and g.wins == 0


def test_an_unsure_or_helped_correct_answer_does_not_fade_help() -> None:
    g = Guidance(level=2, wins=1)
    assert advance(g, correct=True, hinted=False, confident=False).wins == 0
    assert advance(g, correct=True, hinted=True, confident=True).level == 2


def test_two_misses_give_help_back_and_one_miss_resets_wins() -> None:
    g = advance(Guidance(level=1, wins=1), correct=False, hinted=False, confident=None)
    assert g.wins == 0 and g.misses == 1 and g.level == 1
    g = advance(g, correct=False, hinted=True, confident=None)
    assert g.level == 2 and g.misses == 0


@pytest.mark.parametrize("start", [LEVEL_MIN, LEVEL_MAX])
def test_the_level_never_leaves_its_range(start: int) -> None:
    g = Guidance(level=start)
    for _ in range(10):
        g = advance(g, correct=True, hinted=False, confident=True)
    assert LEVEL_MIN <= g.level <= LEVEL_MAX
    for _ in range(10):
        g = advance(g, correct=False, hinted=False, confident=None)
    assert LEVEL_MIN <= g.level <= LEVEL_MAX


def test_payload_round_trips_and_bad_input_falls_back() -> None:
    g = Guidance(level=1, wins=1, misses=0)
    assert Guidance.from_payload(g.as_payload()) == g
    assert Guidance.from_payload(None) == Guidance()
    assert Guidance.from_payload({"level": 99, "wins": -4}) == Guidance(LEVEL_MAX, 0, 0)
    assert Guidance.from_payload({"level": True}) == Guidance()
