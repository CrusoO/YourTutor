"""A stand-in for the browser: plays a practice session with the teaching policy, offline.

The TypeScript policy is held to the Python one by the shared fixtures, so a Python run of the
policy over the pack's own catalog is what the browser does. It records the events the browser
would send and the learner state it ends with.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ItemRow, MisconceptionRow, OverlayRow, SessionRow, SkillRow, StudentRow
from app.offline.pack import learner_json, pack_catalog
from app.orchestrator.policy import policy
from app.orchestrator.types import Action, Event
from app.player.runtime import _build_state, _overlay_skills

NS = uuid.UUID("12345678-1234-5678-1234-567812345678")
T0 = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)  # always in the past
BKT = {"p_init": 0.2, "p_learn": 0.3, "p_slip": 0.1, "p_guess": 0.2}


def seed_content(db: Session, chapter_id: str = "bhutan_class9") -> None:
    """Two skills (the second needs the first), numeric items in several shapes, one chapter."""
    for skill, prereqs in (("OFF.S1", []), ("OFF.S2", ["OFF.S1"])):
        db.add(
            SkillRow(
                id=skill,
                title={"en": skill},
                grade_band=[9],
                subject="math",
                prerequisites=prereqs,
                related=[],
                misconceptions=[],
                bkt=BKT,
                status="approved",
            )
        )
    roles = ["procedure"] * 16 + ["recall", "explain", "apply", "transfer"]
    for skill in ("OFF.S1", "OFF.S2"):
        for index, role in enumerate(roles):
            answer = 4 + index
            a = 2 + index % 4
            stem = [
                f"Solve x + {a} = {a + answer}",
                f"Solve {a}x = {a * answer}",
                f"Solve x - {a} = {answer - a}",
            ][index % 3]
            db.add(
                ItemRow(
                    id=f"{skill}.{index:02d}",
                    skill_ids=[skill],
                    primary_skill=skill,
                    difficulty=[0.2, 0.3, 0.5, 0.55, 0.9][index % 5]
                    if role == "procedure"
                    else 0.5,
                    type="expression",
                    pool="practice",
                    role=role,
                    stem={"en": stem},
                    answer={"sympy": str(answer), "accept": [str(answer)]},
                    solution_steps=[{"en": f"Work out {stem}."}, {"en": f"x = {answer}"}],
                    hints=[
                        {"level": 1, "en": f"Hint one for {skill} {index}. What undoes it?"},
                        {"level": 2, "en": f"Hint two for {skill} {index}. Do it to both sides."},
                        {"level": 3, "en": f"Hint three for {skill} {index}. Then read x."},
                    ],
                    prediction_prompt={"en": f"What is the first step for {skill}?"},
                    misconception_rules=[{"id": "MC.OFF.1", "when_answer_equals": ["77"]}],
                    status="approved",
                    content_hash="x",
                )
            )
    db.add(
        MisconceptionRow(
            id="MC.OFF.1",
            title={"en": "Wrong side"},
            explanation={"en": "You may have changed only one side."},
            remedial_skill="OFF.S1",
            status="approved",
        )
    )
    db.add(
        OverlayRow(
            id=chapter_id,
            curriculum_id="bhutan",
            grade=9,
            chapter="linear_equations",
            skill_ids=["OFF.S1", "OFF.S2"],
            live=True,
            section_map={},
        )
    )
    db.commit()


def _event(kind: str, at: datetime, **payload: Any) -> dict[str, Any]:
    return {"event_type": kind, "at": at.isoformat(), "payload": payload}


def play(
    db: Session,
    student: StudentRow,
    steps: int = 40,
    wrong_every: int = 4,
    *,
    t0: datetime = T0,
    wrong_response: str = "999",
    help_at: int | None = 5,
) -> dict[str, Any]:
    """Run the policy as the browser would; returns the events sent and the state reached."""
    row = SessionRow(
        id=uuid.uuid4(),
        student_id=student.id,
        started_at=t0,
        type="practice",
        last_active_at=t0,
        plan={},
        active_ms=0,
    )
    state, learner = _build_state(db, row, student)
    skills = _overlay_skills(db, student)
    state.catalog = pack_catalog(db, skills)
    answers = {item.id: item.answer_sympy for item in state.catalog}
    state.now = t0
    state.last_active_at = t0
    action: Action = policy(learner, state, None)
    events: list[dict[str, Any]] = []
    clock, answered = t0, 0
    for index in range(steps):
        clock = clock + timedelta(seconds=10)
        kind: str
        payload: dict[str, Any] = {}
        item_id: str | None = action.item_id
        if action.type == "end_session":
            break
        if action.type in {"show_item", "similar_item", "warmup_item", "hint", "check_your_work"}:
            answered += 1
            wrong = answered % wrong_every == 0
            item = action.item_id or ""
            payload = {
                "response": wrong_response if wrong else answers.get(item, "0"),
                "latency_ms": 8000,
            }
            kind = "answer"
        elif action.type == "predict":
            kind, payload = "predict_response", {"response": "subtract"}
        elif action.type in {"worked_example", "reveal_solution", "explain_back_result"}:
            kind = "continue"
        elif action.type == "ask_stuck_point":
            kind, payload = "stuck_choice", {"choice": "start"}
        elif action.type == "ask_stuck_step":
            kind, payload = "stuck_step", {"index": 0}
        elif action.type == "explain_back_prompt":
            kind, payload = "explain_back", {"text": "I did the same to both sides."}
        elif action.type == "break_or_switch":
            kind, payload = "break_choice", {"choice": "continue"}
        else:
            break
        if help_at is not None and index == help_at:
            kind, payload = "request_help", {}
        state.now = clock
        action = policy(
            learner,
            state,
            Event(
                type=kind,
                response=payload.get("response") or payload.get("choice"),
                latency_ms=payload.get("latency_ms"),
                item_id=item_id,
                text=payload.get("text"),
                event_id=str(uuid.uuid5(NS, f"{t0.isoformat()}:e{index}")),
            )
            if kind not in {"stuck_step"}
            else Event(
                type=kind,
                response=str(payload["index"]),
                item_id=item_id,
                event_id=str(uuid.uuid5(NS, f"{t0.isoformat()}:e{index}")),
            ),  # fmt: skip
        )
        record = _event(kind, clock, **payload)
        record["client_event_id"] = str(uuid.uuid5(NS, f"{t0.isoformat()}:e{index}"))
        record["item_id"] = item_id
        record["client_action"] = {"type": action.type, "item_id": action.item_id}
        events.append(record)
    return {
        "started_at": t0.isoformat(),
        "events": events,
        "learner": learner_json(learner),
        "last_action": action.type,
    }
