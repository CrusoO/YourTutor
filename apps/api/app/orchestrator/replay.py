"""Replay-verification: the same event log must reproduce the same actions."""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from app.learner.types import LearnerState
from app.orchestrator.policy import policy
from app.orchestrator.types import Action, Event, SessionState


def replay_actions(
    learner: LearnerState, session: SessionState, events: list[Event]
) -> list[Action]:
    actions = [policy(learner, session, None)]
    for event in events:
        actions.append(policy(learner, session, event))
    return actions


def verify_replay(
    learner: LearnerState,
    session: SessionState,
    events: list[Event],
    expected: list[Action],
) -> bool:
    clone_learner = deepcopy(learner)
    clone_session = deepcopy(session)
    got = replay_actions(clone_learner, clone_session, events)
    if len(got) != len(expected):
        return False
    for left, right in zip(got, expected, strict=True):
        if (left.type, left.item_id, left.rule_id) != (right.type, right.item_id, right.rule_id):
            return False
    return True


def pseudonymous_session_id(session_id: UUID) -> str:
    return f"sess_{session_id.hex[:8]}"
