"""Skip ahead sessions (ARCHITECTURE §9.7): server-checked answers, no hints, no BKT or FSRS.

A skip-ahead is its own session type. Answers are verified here against the authored key (the
client flag is ignored), recorded in `events`, and only a pass writes to the ladder: one
`test_out_passed` event moves the skill to level 4 with `evidence=test_out`. A miss writes nothing
beyond the log and never shows penalty wording.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.config import settings
from app.db.models import EventRow, ItemRow, SessionRow, StudentRow
from app.learner.ladder import KIND_TEST_OUT, MASTERY_P, LadderEvent, apply_ladder_event
from app.learner.types import Mastery
from app.orchestrator.test_out import TEST_OUT_ITEMS, passed, select_items
from app.orchestrator.types import CatalogItem
from app.verifier.check import verify_response

NO_HINTS = "no_hint_in_assessment"


def new_plan(skill_id: str, overlay_id: str, items: list[CatalogItem]) -> dict[str, Any]:
    return {
        "overlay_id": overlay_id,
        "test_out": {
            "skill_id": skill_id,
            "item_ids": [item.id for item in items],
            "answers": [],
            "result": None,
        },
    }


def pick_items(catalog: tuple[CatalogItem, ...], skill_id: str) -> list[CatalogItem] | None:
    return select_items(catalog, skill_id, allow_draft=settings.allow_draft_content)


def _state(row: SessionRow) -> dict[str, Any]:
    return dict((row.plan or {}).get("test_out") or {})


def _action(
    session: Session,
    row: SessionRow,
    locale: str,
    *,
    rejected: bool = False,
    flag: str | None = None,
) -> dict[str, Any]:
    from app.player.runtime import _item_payload

    state = _state(row)
    skill_id = state["skill_id"]
    base: dict[str, Any] = {
        "skill_id": skill_id,
        "session_type": "test_out",
        "phase": "test_out",
        "hint_level": None,
        "hint_level_shown": 0,
        "misconception_id": None,
        "text": None,
        "source": None,
        "correct": None,
        "grade": None,
        "resumable": False,
        "rejected": rejected,
        "guardrail_flag": flag,
        "allow_hint": False,
        "can_request_hint": False,
        "can_show_solution": False,
        "dont_know_option": False,
    }
    result = state.get("result")
    if result is not None:
        return {
            **base,
            "type": "test_out_result",
            "item_id": None,
            "item": None,
            "ended_reason": "test_out_complete",
            "reason": "test_out_complete",
            "extras": result,
        }
    index = len(state["answers"])
    item_id = state["item_ids"][index]
    return {
        **base,
        "type": "show_item",
        "item_id": item_id,
        "item": _item_payload(session.get(ItemRow, item_id), locale, reveal=False, steps=False),
        "ended_reason": None,
        "reason": None,
        "extras": {
            "assessment": True,
            "test_out": {"index": index + 1, "of": TEST_OUT_ITEMS},
        },
    }


def _envelope(
    row: SessionRow, action: dict[str, Any], *, duplicate: bool = False
) -> dict[str, Any]:
    state = _state(row)
    return {
        "session_id": str(row.id),
        "duplicate": duplicate,
        "action": action,
        "progress": {
            "items_completed": len(state.get("answers") or []),
            "active_ms": row.active_ms,
            "resumable": False,
            "ended_reason": row.ended_reason,
        },
        "llm_called": False,
    }


def view(session: Session, student: StudentRow, row: SessionRow) -> dict[str, Any]:
    action = _action(session, row, student.home_language or "en")
    return {
        "id": str(row.id),
        "type": row.type,
        "student_id": str(row.student_id),
        "action": action,
        "progress": _envelope(row, action)["progress"],
        "llm_called": False,
    }


def _log(
    session: Session,
    row: SessionRow,
    client_event_id: uuid.UUID,
    event_type: str,
    item_id: str | None,
    payload: dict[str, Any],
    correct: bool | None,
) -> None:
    session.add(
        EventRow(
            id=uuid.uuid4(),
            client_event_id=client_event_id,
            session_id=row.id,
            item_id=item_id,
            event_type=event_type,
            payload=payload,
            correct=correct,
            hint_level=None,
            latency_ms=payload.get("latency_ms"),
            created_at=now_utc(),
            state_before="test_out",
            state_after="test_out",
            rule_id=None,
        )
    )


def _earn_level_4(session: Session, row: SessionRow, student: StudentRow, skill_id: str) -> str:
    """Write the ladder evidence for a pass. Returns the id of the evidence event."""
    from app.learner.bkt import BktParams
    from app.player.runtime import _bkt_and_prereqs, load_learner, persist_learner

    evidence_id = uuid.uuid4()
    learner = load_learner(session, student.id)
    if skill_id not in learner.mastery:
        params, _ = _bkt_and_prereqs(session, (skill_id,))
        start: BktParams = params[skill_id]
        learner.mastery[skill_id] = Mastery(skill_id=skill_id, p_known=start.p_init)
    # Level 4 means p_known >= MASTERY_P; without this the policy would still see the skill as a
    # weak prerequisite and send the student back to it. No attempt counts change.
    learner.mastery[skill_id].p_known = max(learner.mastery[skill_id].p_known, MASTERY_P)
    apply_ladder_event(
        learner.ladders,
        LadderEvent(event_id=str(evidence_id), skill_id=skill_id, kind=KIND_TEST_OUT, at=now_utc()),
        p_known=learner.mastery[skill_id].p_known,
    )
    persist_learner(session, student.id, learner)
    _log(
        session,
        row,
        evidence_id,
        "test_out_passed",
        None,
        {"skill_id": skill_id, "item_ids": _state(row)["item_ids"]},
        True,
    )
    return str(evidence_id)


def apply_event(
    session: Session,
    row: SessionRow,
    student: StudentRow,
    catalog: tuple[CatalogItem, ...],
    client_event_id: uuid.UUID,
    event_type: str,
    item_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    locale = student.home_language or "en"
    state = _state(row)
    if state.get("result") is not None:
        return _envelope(row, _action(session, row, locale))
    if event_type != "answer":
        flag = NO_HINTS if event_type in {"request_hint", "show_solution", "explain_back"} else None
        return _envelope(row, _action(session, row, locale, rejected=True, flag=flag or "ignored"))
    index = len(state["answers"])
    expected = state["item_ids"][index]
    item = next((entry for entry in catalog if entry.id == expected), None)
    if item is None or (item_id and item_id != expected):
        return _envelope(row, _action(session, row, locale, rejected=True, flag="wrong_item"))
    correct = verify_response(
        str(payload.get("response") or ""),
        answer_sympy=item.answer_sympy,
        accept=list(item.accept),
        item_type=item.type,
        verify=item.verify,
        options=list(item.options),
    )
    _log(session, row, client_event_id, "answer", expected, payload, correct)
    answers = [*state["answers"], correct]
    plan = dict(row.plan or {})
    state["answers"] = answers
    if len(answers) >= TEST_OUT_ITEMS:
        ok = passed(answers)
        level = 0
        if ok:
            _earn_level_4(session, row, student, state["skill_id"])
            level = 4
        state["result"] = {"passed": ok, "level": level, "skill_id": state["skill_id"]}
        row.ended_at = now_utc()
        row.ended_reason = "test_out_complete"
        row.resumable = False
    plan["test_out"] = state
    row.plan = plan
    return _envelope(row, _action(session, row, locale))
