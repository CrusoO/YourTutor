"""UI capability flags for session actions (orchestrator-owned, not client-inferred)."""

from __future__ import annotations

from app.orchestrator.types import Action, SessionState

_ITEM_HINT_TYPES = frozenset(
    {"show_item", "warmup_item", "similar_item", "hint", "check_your_work"}
)


def hint_solution_flags(
    state: SessionState,
    action: Action,
    *,
    assessment: bool,
) -> tuple[bool, bool]:
    """Return (can_request_help, can_show_solution) for the current action.

    The first value is sent as both `can_request_help` and the deprecated `can_request_hint`.
    """
    practice = state.session_type == "practice" and not assessment
    if not practice or action.type not in _ITEM_HINT_TYPES:
        return False, False
    can_show = state.hint_level_shown >= 2
    can_request = state.hint_level_shown < 2 and action.type in {
        "show_item",
        "warmup_item",
        "similar_item",
        "check_your_work",
    }
    return can_request, can_show
