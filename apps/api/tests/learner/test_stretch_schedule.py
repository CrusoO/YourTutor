"""G2a: the ladder schedules stretch items; incremental updates and recompute agree."""

from __future__ import annotations

from datetime import UTC, datetime

from app.learner.ladder import LadderEvent, SkillLadder, apply_ladder_event, compute

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def _answer(n: int, role: str, structure: str, at: datetime) -> LadderEvent:
    return LadderEvent(
        event_id=f"e{n}",
        skill_id="S1",
        kind="answer",
        at=at,
        item_id=f"i{n}",
        correct=True,
        pool="practice",
        role=role,
        structure=structure,
    )


def test_level_4_schedules_an_apply_stretch_one_day_later() -> None:
    ladders: dict[str, SkillLadder] = {}
    for n, structure in enumerate(("a", "b", "c"), start=1):
        at = T0.replace(minute=n)
        apply_ladder_event(ladders, _answer(n, "procedure", structure, at), p_known=0.97)
    flags = ladders["S1"].flags
    assert ladders["S1"].level == 4
    assert flags["stretch_after_4"] == "2026-01-02T09:03:00+00:00"
    assert "stretch_after_5" not in flags


def test_level_5_schedules_a_transfer_stretch_and_level_6_nothing() -> None:
    ladders: dict[str, SkillLadder] = {}
    for n, structure in enumerate(("a", "b", "c"), start=1):
        apply_ladder_event(ladders, _answer(n, "procedure", structure, T0.replace(minute=n)), 0.97)
    apply_ladder_event(ladders, _answer(4, "apply", "w", T0.replace(day=3, hour=10)), 0.97)
    assert ladders["S1"].flags["stretch_after_5"] == "2026-01-04T10:00:00+00:00"
    apply_ladder_event(ladders, _answer(5, "transfer", "t", T0.replace(day=5, hour=11)), 0.97)
    assert ladders["S1"].level == 6
    assert not any(key.startswith("stretch_after_6") for key in ladders["S1"].flags)


def test_the_schedule_is_set_once_and_never_moved() -> None:
    ladders: dict[str, SkillLadder] = {}
    for n, structure in enumerate(("a", "b", "c", "d", "e"), start=1):
        apply_ladder_event(ladders, _answer(n, "procedure", structure, T0.replace(minute=n)), 0.97)
    assert ladders["S1"].flags["stretch_after_4"] == "2026-01-02T09:03:00+00:00"


def test_recompute_from_the_log_gives_the_same_flags() -> None:
    events = [
        _answer(n, "procedure", s, T0.replace(minute=n)) for n, s in enumerate(("a", "b", "c"), 1)
    ]
    live: dict[str, SkillLadder] = {}
    for event in events:
        apply_ladder_event(live, event, p_known=0.97)
    folded = compute(events, datetime(2027, 1, 1, tzinfo=UTC))
    assert folded["S1"].level == live["S1"].level
    assert folded["S1"].flags["stretch_after_4"] == live["S1"].flags["stretch_after_4"]


def test_a_test_out_pass_also_schedules_the_stretch() -> None:
    ladders: dict[str, SkillLadder] = {}
    apply_ladder_event(
        ladders,
        LadderEvent(event_id="t1", skill_id="S1", kind="test_out", at=T0.replace(hour=12)),
        p_known=0.95,
    )
    assert ladders["S1"].flags["stretch_after_4"] == "2026-01-02T12:00:00+00:00"
    assert ladders["S1"].flags["evidence"] == "test_out"
