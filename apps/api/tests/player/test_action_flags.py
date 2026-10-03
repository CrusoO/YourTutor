from app.orchestrator.types import Action, SessionState
from app.player.action_flags import hint_solution_flags


def _state(session_type: str = "practice", hint_level_shown: int = 0) -> SessionState:
    return SessionState(
        session_type=session_type,
        now=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        catalog=(),
        overlay_skill_ids=(),
        bkt_params={},
        hint_level_shown=hint_level_shown,
    )


def test_no_hints_in_diagnostic() -> None:
    state = _state("diagnostic")
    action = Action(type="show_item", item_id="ITEM.1")
    assert hint_solution_flags(state, action, assessment=True) == (False, False)


def test_request_hint_on_practice_item() -> None:
    state = _state("practice", 0)
    action = Action(type="show_item", item_id="ITEM.1")
    assert hint_solution_flags(state, action, assessment=False) == (True, False)


def test_show_solution_after_two_hints() -> None:
    state = _state("practice", 2)
    action = Action(type="hint", item_id="ITEM.1")
    assert hint_solution_flags(state, action, assessment=False) == (False, True)
