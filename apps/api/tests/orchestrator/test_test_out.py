"""Skip ahead (ARCHITECTURE §9.7): item selection and the ladder evidence are pure."""

from __future__ import annotations

from datetime import UTC, datetime

from app.learner.ladder import (
    KIND_TEST_OUT,
    LadderEvent,
    SkillLadder,
    apply_ladder_event,
    compute,
)
from app.orchestrator.test_out import TEST_OUT_ITEMS, passed, select_items
from app.orchestrator.types import CatalogItem

AT = datetime(2026, 10, 7, tzinfo=UTC)


def _item(
    item_id: str,
    *,
    difficulty: float = 0.9,
    role: str = "procedure",
    pool: str = "practice",
    status: str = "approved",
    skill: str = "S",
) -> CatalogItem:
    return CatalogItem(
        id=item_id,
        skill_ids=(skill,),
        difficulty=difficulty,
        pool=pool,
        status=status,
        role=role,
        structure=item_id,
    )


def test_picks_one_apply_or_transfer_and_one_more_hard_item() -> None:
    catalog = (
        _item("P1"),
        _item("P2"),
        _item("T1", role="transfer"),
        _item("EASY", difficulty=0.2),
        _item("OTHER", skill="X"),
    )
    chosen = select_items(catalog, "S", allow_draft=False)
    assert chosen is not None
    assert len(chosen) == TEST_OUT_ITEMS == 2
    roles = [item.role for item in chosen]
    assert any(role in {"apply", "transfer"} for role in roles)
    assert all(item.difficulty > 0.8 and item.primary_skill == "S" for item in chosen)
    assert chosen[0].id != chosen[1].id


def test_selection_is_deterministic() -> None:
    catalog = (_item("P2"), _item("P1"), _item("T1", role="transfer"), _item("A1", role="apply"))
    assert select_items(catalog, "S", allow_draft=False) == select_items(
        tuple(reversed(catalog)), "S", allow_draft=False
    )


def test_unavailable_without_a_hard_apply_or_transfer_item() -> None:
    assert select_items((_item("P1"), _item("P2")), "S", allow_draft=False) is None


def test_unavailable_with_fewer_than_two_hard_items() -> None:
    assert select_items((_item("T1", role="transfer"),), "S", allow_draft=False) is None


def test_only_practice_pool_and_servable_status() -> None:
    catalog = (
        _item("P1", status="draft"),
        _item("T1", role="transfer", pool="diagnostic"),
        _item("T2", role="transfer", status="retired"),
        _item("P2"),
    )
    assert select_items(catalog, "S", allow_draft=False) is None
    draft_ok = (_item("P1", status="draft"), _item("T1", role="transfer", status="draft"))
    assert select_items(draft_ok, "S", allow_draft=False) is None
    assert select_items(draft_ok, "S", allow_draft=True) is not None


def test_pass_needs_every_answer_correct_and_both_answered() -> None:
    assert passed([True, True])
    assert not passed([True, False])
    assert not passed([False, True])
    assert not passed([True])
    assert not passed([])


def _event(skill: str = "S", event_id: str = "E1") -> LadderEvent:
    return LadderEvent(event_id=event_id, skill_id=skill, kind=KIND_TEST_OUT, at=AT)


def test_test_out_event_earns_level_4_with_test_out_evidence() -> None:
    ladders: dict[str, SkillLadder] = {}
    ladder = apply_ladder_event(ladders, _event(), p_known=0.2)
    assert ladder is not None
    assert ladder.level == 4
    assert ladder.evidence[4] == ["E1"]
    assert ladder.flags["evidence"] == "test_out"


def test_test_out_does_not_earn_the_levels_around_it() -> None:
    ladders: dict[str, SkillLadder] = {}
    apply_ladder_event(ladders, _event(), p_known=0.2)
    assert sorted(ladders["S"].achieved) == [4]


def test_test_out_twice_changes_nothing() -> None:
    ladders: dict[str, SkillLadder] = {}
    apply_ladder_event(ladders, _event(event_id="E1"), p_known=0.2)
    apply_ladder_event(ladders, _event(event_id="E2"), p_known=0.2)
    assert ladders["S"].evidence[4] == ["E1"]


def test_recompute_from_the_log_matches_the_incremental_ladder() -> None:
    live: dict[str, SkillLadder] = {}
    apply_ladder_event(live, _event(), p_known=0.2)
    folded = compute([_event()], AT)
    assert folded["S"].summary() == live["S"].summary()


def test_later_practice_still_chains_apply_and_transfer_after_a_test_out() -> None:
    ladders: dict[str, SkillLadder] = {}
    apply_ladder_event(ladders, _event(), p_known=0.2)
    apply_ladder_event(
        ladders,
        LadderEvent(
            event_id="A1",
            skill_id="S",
            kind="answer",
            at=AT,
            item_id="ITEM.A",
            correct=True,
            role="apply",
            structure="x",
        ),
        p_known=0.5,
    )
    assert 5 in ladders["S"].achieved
