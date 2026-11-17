"""Pure decay and merge: half-life, dropping, one write at a time."""

from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.learner.profile.counts import (
    Counts,
    add_event,
    decay_factor,
    decayed,
    from_payload,
    to_payload,
    week_index,
)


def test_week_index_has_no_day_and_never_goes_negative() -> None:
    assert week_index(date(2026, 1, 1)) == 0
    assert week_index(date(2026, 1, 5)) == 1
    assert week_index(date(2020, 1, 1)) == 0


def test_half_life_is_sixty_days() -> None:
    assert decay_factor(0) == 1.0
    assert decay_factor(-3) == 1.0
    # 60 days is 8.57 weeks: 9 weeks (63 days) is a little more than one half-life
    assert 0.47 < decay_factor(9) < 0.5
    assert decay_factor(4) > decay_factor(8)


def test_add_decays_then_adds_and_drops_weak_entries() -> None:
    c = add_event(Counts(), kind="method", key="factorise", increment=1, week=0)
    c = add_event(c, kind="error", key="slip", increment=2, week=0)
    assert c.methods == {"factorise": 1.0} and c.errors == {"slip": 2.0} and c.n_events == 2.0
    later = add_event(c, kind="method", key="complete_square", increment=1, week=9)
    assert "factorise" not in later.methods  # 0.48 is below 0.5, so it is forgotten
    assert later.errors["slip"] == pytest.approx(2 * decay_factor(9))
    assert later.methods["complete_square"] == 1.0


def test_read_decay_does_not_change_the_stored_value() -> None:
    c = Counts({"a": 4.0}, {}, 4.0, 0)
    assert decayed(c, 10).methods["a"] < 4.0 and c.methods["a"] == 4.0


def test_bad_kind_and_schema_are_refused() -> None:
    with pytest.raises(ValueError):
        add_event(Counts(), kind="free_text", key="x", increment=1, week=0)
    with pytest.raises(ValueError):
        from_payload({"v": 99, "m": {}, "e": {}, "n": 0, "w": 0})


@given(st.lists(st.tuples(st.sampled_from(["a", "b"]), st.integers(1, 5)), max_size=20))
def test_payload_round_trip_and_no_weak_entries(events: list[tuple[str, int]]) -> None:
    c, week = Counts(), 0
    for key, inc in events:
        c = add_event(c, kind="method", key=key, increment=inc, week=week)
        week += 1
    assert from_payload(to_payload(c)) == c
    assert all(v >= 0.5 for v in c.methods.values())
