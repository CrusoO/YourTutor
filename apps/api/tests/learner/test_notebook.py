"""Mistake notebook scheduling: pure table tests on a frozen clock."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.learner import notebook as nb

CFG = nb.NotebookConfig((2, 6, 15), 5)
MISS = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)


def day(n: int) -> datetime:
    return MISS + timedelta(days=n)


def test_shipped_config_is_two_six_fifteen() -> None:
    cfg = nb.load_config()
    assert cfg.return_days == (2, 6, 15)
    assert cfg.due_limit >= 1


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {"return_days": [], "due_limit": 5},
        {"return_days": [6, 2], "due_limit": 5},
        {"return_days": [2, 2], "due_limit": 5},
        {"return_days": [0, 2], "due_limit": 5},
        {"return_days": [True], "due_limit": 5},
        {"return_days": [2], "due_limit": 0},
    ],
)
def test_bad_config_refused(raw: object) -> None:
    with pytest.raises(ValueError):
        nb.parse_config(raw)


def test_new_entry_is_due_after_two_days() -> None:
    e = nb.new_entry(MISS, CFG)
    assert (e.stage, e.state, e.due_at) == (0, nb.OPEN, day(2))
    assert not nb.is_due(e, day(2) - timedelta(seconds=1))
    assert nb.is_due(e, day(2))


@pytest.mark.parametrize(
    ("stage", "outcome", "now_day", "want_stage", "want_state", "want_due"),
    [
        (0, "right", 2, 1, nb.OPEN, 6),
        (1, "right", 6, 2, nb.OPEN, 15),
        (2, "right", 15, 2, nb.SETTLED, None),
        (0, "wrong", 2, 0, nb.OPEN, 4),
        (1, "wrong", 6, 0, nb.OPEN, 8),
        (2, "wrong", 15, 1, nb.OPEN, 21),
        (0, "right", 9, 1, nb.OPEN, 9),  # late: counted from the miss, never in the past
    ],
)
def test_returns(
    stage: int,
    outcome: str,
    now_day: int,
    want_stage: int,
    want_state: str,
    want_due: int | None,
) -> None:
    start = nb.EntryState(stage, nb.OPEN, MISS, nb.due_at_for(MISS, stage, CFG))
    out = nb.apply_return(start, outcome, day(now_day), CFG)
    assert (out.stage, out.state) == (want_stage, want_state)
    assert out.due_at == (None if want_due is None else day(want_due))


def test_wrong_is_never_back_before_day_two_again() -> None:
    out = nb.apply_return(nb.new_entry(MISS, CFG), "wrong", day(2), CFG)
    assert out.due_at is not None and out.due_at - day(2) >= timedelta(days=2)


def test_full_path_to_settled() -> None:
    e = nb.new_entry(MISS, CFG)
    for d in (2, 6, 15):
        assert nb.is_due(e, day(d))
        e = nb.apply_return(e, "right", day(d), CFG)
    assert e.state == nb.SETTLED and not nb.is_due(e, day(100))


def test_settled_entry_does_not_change() -> None:
    done = nb.EntryState(2, nb.SETTLED, MISS, None)
    assert nb.apply_return(done, "wrong", day(30), CFG) == done


def test_bad_outcome_refused() -> None:
    with pytest.raises(ValueError):
        nb.apply_return(nb.new_entry(MISS, CFG), "skipped", day(2), CFG)


def test_stage_counts() -> None:
    entries = [
        nb.EntryState(0, nb.OPEN, MISS, day(2)),
        nb.EntryState(0, nb.OPEN, MISS, day(2)),
        nb.EntryState(2, nb.OPEN, MISS, day(15)),
        nb.EntryState(2, nb.SETTLED, MISS, None),
    ]
    assert nb.stage_counts(entries, CFG) == {"1": 2, "2": 0, "3": 1, "settled": 1}


def test_new_form_is_never_the_same_item_or_stem() -> None:
    cands = [
        ("a", "Solve x", 0.5),
        ("b", "Solve x", 0.5),
        ("c", "Solve y", 0.9),
        ("d", "Solve z", 0.55),
    ]
    assert nb.pick_new_form("a", "Solve x", cands, 0.5) == "d"
    assert nb.pick_new_form("a", "Solve x", cands, 0.5) == nb.pick_new_form(
        "a", "Solve x", cands, 0.5
    )
    same = [("a", "Solve x", 0.5), ("b", "Solve x", 0.5)]
    assert nb.pick_new_form("a", "Solve x", same, 0.5) is None


def test_config_loads_from_a_given_folder(tmp_path: Path) -> None:
    (tmp_path / "notebook.yaml").write_text("return_days: [1, 3]\ndue_limit: 2\n", encoding="utf-8")
    assert nb.load_config(tmp_path) == nb.NotebookConfig((1, 3), 2)
