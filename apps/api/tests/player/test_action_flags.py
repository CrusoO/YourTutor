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


def test_help_is_offered_on_a_hint_screen_until_two_hints_have_been_shown() -> None:
    action = Action(type="hint", item_id="ITEM.1")
    # a restated question or a step hint uses no ladder level: more help can still be asked for
    assert hint_solution_flags(_state(hint_level_shown=0), action, assessment=False) == (
        True,
        False,
    )
    assert hint_solution_flags(_state(hint_level_shown=1), action, assessment=False) == (
        True,
        False,
    )
    assert hint_solution_flags(_state(hint_level_shown=2), action, assessment=False) == (
        False,
        True,
    )


def test_help_is_offered_after_check_your_work() -> None:
    action = Action(type="check_your_work", item_id="ITEM.1")
    assert hint_solution_flags(_state(), action, assessment=False) == (True, False)


def test_no_help_flags_on_the_picker_screens() -> None:
    for kind in ("ask_stuck_point", "ask_stuck_step"):
        action = Action(type=kind, item_id="ITEM.1")
        assert hint_solution_flags(_state(), action, assessment=False) == (False, False)
