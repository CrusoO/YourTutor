"""Sync guardrails: re-verify from stored response, ignore client correct."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.learner.types import LearnerState
from app.orchestrator.policy import policy
from app.orchestrator.types import Action, Event, SessionState
from app.verifier.check import verify_response


def apply_sync_event(learner: LearnerState, session: SessionState, event: Event) -> Action:
    """Server-side apply. Client `correct` is never trusted."""
    if event.type == "answer":
        event.client_correct = None
    return policy(learner, session, event)


def verified_correct(session: SessionState, event: Event) -> bool | None:
    if event.type != "answer" or not event.response:
        return None
    item = session.item(event.item_id) or session.item()
    if item is None:
        return None
    return verify_response(
        event.response,
        answer_sympy=item.answer_sympy,
        accept=list(item.accept),
        item_type=item.type,
        verify=item.verify,
        options=list(item.options),
    )


def load_fixture(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def fixture_dir() -> Path:
    root = Path(__file__).resolve().parents[4]
    return root / "packages" / "shared" / "fixtures" / "sync_guardrails"
