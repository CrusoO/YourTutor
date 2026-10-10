"""First run and the warm-up offer (G5). Pure rules; the router stores the result.

First run: a student with no sessions is offered "Quick warm-up to find where to start" or "Start
from the beginning". Nothing starts automatically and no session exists until the student acts.
Re-offer: a student who started from the beginning is offered the warm-up once more after the
second finished practice session; "not now" is final.
"""

from __future__ import annotations

from typing import Any

FIRST_RUN = "first_run"
REOFFER = "warmup_reoffer"
REOFFER_AFTER_SESSIONS = 2
CHOICES = ("warmup", "start_beginning", "not_now")
_ALLOWED = {FIRST_RUN: ("warmup", "start_beginning"), REOFFER: ("warmup", "not_now")}


class InvalidChoice(ValueError):
    pass


def offer_for(
    state: dict[str, Any] | None, *, total_sessions: int, ended_practice: int
) -> str | None:
    """What to offer now: first_run, warmup_reoffer, or nothing."""
    state = state or {}
    if "first_run" not in state:
        return FIRST_RUN if total_sessions == 0 else None
    if (
        state["first_run"] == "start_beginning"
        and "reoffer" not in state
        and ended_practice >= REOFFER_AFTER_SESSIONS
    ):
        return REOFFER
    return None


def apply_choice(state: dict[str, Any] | None, offer: str | None, choice: str) -> dict[str, Any]:
    """The new onboarding state after a choice, or InvalidChoice if it does not match the offer."""
    if offer is None or choice not in _ALLOWED[offer]:
        raise InvalidChoice(choice)
    key = "first_run" if offer == FIRST_RUN else "reoffer"
    return {**(state or {}), key: choice}


def next_session_type(choice: str) -> str:
    return "diagnostic" if choice == "warmup" else "practice"
