"""CONFIDENCE_RULES: a right answer the learner called a guess is neither evidence nor a miss.

The rule reaches the ladder only when the deployment turns it on, in the live runtime, in the
offline sync replay and in the log rebuild, so all three agree.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.config import settings
from app.db.models import EventRow
from app.offline.sync import SyncEventIn, _event_for
from app.orchestrator.types import CatalogItem
from app.player.ladder_log import ladder_events_from_rows

ITEM = CatalogItem(
    id="i1", skill_ids=("s1",), difficulty=0.4, pool="practice", status="approved", role="procedure"
)


def _row(confidence: str | None) -> EventRow:
    payload: dict[str, Any] = {"response": "4"}
    if confidence is not None:
        payload["confidence"] = confidence
    return EventRow(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        item_id="i1",
        event_type="answer",
        payload=payload,
        correct=True,
        created_at=datetime(2026, 11, 1, tzinfo=UTC),
        state_before="practice",
    )


def _rebuilt(confidence: str | None) -> str:
    events = ladder_events_from_rows([(_row(confidence), "practice")], {ITEM.id: ITEM})
    assert len(events) == 1
    return events[0].confidence


@pytest.mark.parametrize("flag", [False, True])
def test_the_log_rebuild_passes_confidence_only_when_the_rule_is_on(
    monkeypatch: pytest.MonkeyPatch, flag: bool
) -> None:
    monkeypatch.setattr(settings, "confidence_rules", flag)
    assert _rebuilt("unsure") == ("unsure" if flag else "")
    assert _rebuilt("sure") == ("sure" if flag else "")


def test_nothing_or_nonsense_is_never_passed_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "confidence_rules", True)
    assert _rebuilt(None) == ""
    assert _rebuilt("maybe") == ""


@pytest.mark.parametrize("flag", [False, True])
def test_the_sync_replay_reads_confidence_only_when_the_rule_is_on(
    monkeypatch: pytest.MonkeyPatch, flag: bool
) -> None:
    monkeypatch.setattr(settings, "confidence_rules", flag)
    body = SyncEventIn(
        client_event_id=uuid.uuid4(),
        event_type="answer",
        item_id="i1",
        at=datetime(2026, 11, 1, tzinfo=UTC),
        payload={"response": "4", "confidence": "unsure"},
    )
    assert _event_for(body).confidence == ("unsure" if flag else None)
