"""G2a session fields survive being stored in the plan and loaded for the next event."""

from __future__ import annotations

from app.orchestrator.types import default_params
from app.player.runtime import dump_state, load_state
from tests.orchestrator.conftest import NOW, catalog_item, make_session


def test_g2a_state_fields_round_trip_through_the_plan() -> None:
    state = make_session(catalog_item(), introduced={"MATH.S1"})
    state.last_wrong_item_id = "ITEM.A"
    state.fast_streak = 2
    state.help_without_attempt = 1
    state.stuck_item_id = "ITEM.A"
    state.stretch_served = 1
    state.stretch_skills = {"MATH.S1", "MATH.S2"}
    state.phase = "stuck"
    plan = dump_state(state)
    loaded = load_state(
        plan,
        session_type="practice",
        now=NOW,
        catalog=state.catalog,
        overlay_skill_ids=("MATH.S1",),
        bkt_params={"MATH.S1": default_params()},
        prerequisites={},
    )
    assert loaded.last_wrong_item_id == "ITEM.A"
    assert loaded.fast_streak == 2 and loaded.help_without_attempt == 1
    assert loaded.stuck_item_id == "ITEM.A"
    assert loaded.stretch_served == 1 and loaded.stretch_skills == {"MATH.S1", "MATH.S2"}
    assert loaded.phase == "stuck"


def test_an_old_plan_without_the_new_fields_loads_with_defaults() -> None:
    plan = dump_state(make_session(catalog_item()))
    for key in (
        "last_wrong_item_id",
        "fast_streak",
        "help_without_attempt",
        "stuck_item_id",
        "stretch_served",
        "stretch_skills",
    ):
        plan.pop(key)
    loaded = load_state(
        plan,
        session_type="practice",
        now=NOW,
        catalog=(),
        overlay_skill_ids=(),
        bkt_params={},
        prerequisites={},
    )
    assert loaded.last_wrong_item_id is None and loaded.fast_streak == 0
    assert loaded.stuck_item_id is None and loaded.stretch_served == 0
    assert loaded.stretch_skills == set()
