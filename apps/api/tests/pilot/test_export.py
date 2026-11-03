"""The pilot export: what counts as a delayed retest, and that nobody is named."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.db.models import EventRow
from app.orchestrator.types import CatalogItem
from app.pilot.export import (
    attempts_for_student,
    bucket,
    pseudonym,
    retests,
    summarise,
)

T0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
SESSION_A, SESSION_B, SESSION_C = (uuid.uuid4() for _ in range(3))
ITEM = CatalogItem(
    id="i1", skill_ids=("s1",), difficulty=0.4, pool="practice", status="approved", role="procedure"
)
ITEM_2 = CatalogItem(
    id="i2", skill_ids=("s1",), difficulty=0.6, pool="practice", status="approved", role="apply"
)
CATALOG = {ITEM.id: ITEM, ITEM_2.id: ITEM_2}


def ev(
    session: uuid.UUID,
    item: str,
    kind: str,
    days: float,
    *,
    correct: bool | None = None,
    state_before: str = "practice",
    **payload: Any,
) -> EventRow:
    return EventRow(
        id=uuid.uuid4(),
        session_id=session,
        item_id=item,
        event_type=kind,
        payload=payload,
        correct=correct,
        hint_level=None,
        latency_ms=4000,
        created_at=T0 + timedelta(days=days),
        state_before=state_before,
        rule_id="R07",
    )


def run(*events: EventRow, types: dict[uuid.UUID, str] | None = None) -> list[dict[str, Any]]:
    kinds = types or {}
    return attempts_for_student([(e, kinds.get(e.session_id, "practice")) for e in events], CATALOG)


def test_an_answer_row_carries_what_the_log_knows() -> None:
    rows = run(
        ev(
            SESSION_A,
            "i1",
            "answer",
            0,
            correct=False,
            confidence="sure",
            diagnosis={"class": "slip"},
        )
    )
    assert len(rows) == 1
    row = rows[0]
    assert (row["skill_id"], row["role"], row["correct"], row["first_try"]) == (
        "s1",
        "procedure",
        False,
        True,
    )
    assert row["confidence"] == "sure" and row["diagnosis"] == "slip" and row["rule_id"] == "R07"
    assert row["days_since_skill_practice"] is None and row["attempt_on_skill"] == 1


def test_help_before_an_answer_marks_it_hinted_and_a_second_answer_is_not_a_first_try() -> None:
    rows = run(
        ev(SESSION_A, "i1", "request_help", 0),
        ev(SESSION_A, "i1", "answer", 0.001, correct=True),
        ev(SESSION_A, "i1", "answer", 0.002, correct=True),
    )
    assert [r["hinted"] for r in rows] == [True, True]
    assert [r["first_try"] for r in rows] == [True, False]


def test_days_since_the_skill_was_last_practised_counts_help_and_answers_per_skill() -> None:
    rows = run(
        ev(SESSION_A, "i1", "answer", 0, correct=True),
        ev(SESSION_B, "i2", "answer", 8, correct=True, state_before="warmup"),
    )
    assert rows[1]["days_since_skill_practice"] == 8.0 and rows[1]["pool"] == "warmup"


def test_a_review_after_a_week_is_a_7_day_retest_and_after_three_weeks_a_21_day_one() -> None:
    rows = run(
        ev(SESSION_A, "i1", "answer", 0, correct=True),
        ev(SESSION_B, "i1", "answer", 8, correct=True, state_before="warmup"),
        ev(SESSION_C, "i2", "answer", 30, correct=False, state_before="warmup"),
    )
    found = retests([{"pseudonym": "x", **r} for r in rows])
    assert [(r["bucket"], r["correct"]) for r in found] == [("7d", True), ("21d", False)]


def test_a_review_that_is_too_soon_hinted_or_a_second_try_is_not_a_retest() -> None:
    rows = run(
        ev(SESSION_A, "i1", "answer", 0, correct=True),
        ev(SESSION_B, "i1", "answer", 3, correct=True, state_before="warmup"),  # too soon
        ev(SESSION_C, "i2", "request_help", 20, state_before="warmup"),
        ev(SESSION_C, "i2", "answer", 20.001, correct=True, state_before="warmup"),  # hinted
    )
    assert retests([{"pseudonym": "x", **r} for r in rows]) == []


def test_buckets() -> None:
    assert [bucket(d) for d in (None, 0, 6.99, 7, 20.9, 21, 90)] == [
        "",
        "",
        "",
        "7d",
        "7d",
        "21d",
        "21d",
    ]


def test_the_summary_compares_a_normal_day_with_the_delayed_retests() -> None:
    rows = [
        {"pseudonym": "a", **r}
        for r in run(
            ev(SESSION_A, "i1", "answer", 0, correct=True, confidence="sure"),
            ev(SESSION_A, "i2", "answer", 0.001, correct=False, confidence="sure"),
            ev(SESSION_B, "i1", "answer", 9, correct=True, state_before="warmup"),
        )
    ]
    summary = summarise(rows)
    assert summary["answers"] == 3 and summary["learners"] == 1
    assert summary["unhinted_first_try_practice"] == {"n": 2, "right": 1, "rate": 0.5}
    assert summary["retests"]["7d"] == {"n": 1, "right": 1, "rate": 1.0}
    assert summary["retests"]["21d"] == {"n": 0, "right": 0, "rate": None}
    assert summary["sure_but_wrong"] == {"of_sure_answers": 2, "wrong": 1}


def test_a_pseudonym_is_stable_keyed_and_short() -> None:
    student = uuid.uuid4()
    a = pseudonym("a-secret-of-sufficient-length", student)
    assert a == pseudonym("a-secret-of-sufficient-length", student)
    assert a != pseudonym("another-secret-of-enough-length", student)
    assert len(a) == 16 and str(student)[:8] not in a


def test_a_weak_or_missing_salt_is_refused() -> None:
    for salt in ("", "short"):
        with pytest.raises(ValueError):
            pseudonym(salt, uuid.uuid4())
